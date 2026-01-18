"""
JSON 내보내기 서비스

단일 책임: 채용 공고를 JSON 파일로 저장
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.config import ExporterConfig, get_config
from src.core.interfaces import ExporterProtocol
from src.models import JobPosting, JobSource


class JSONExporter(ExporterProtocol):
    """JSON 파일 내보내기 서비스

    채용 공고를 JSON 파일로 저장합니다.
    기존 데이터와 병합하여 신규/기존 공고를 관리합니다.
    """

    def __init__(
        self,
        output_path: Optional[Path] = None,
        config: Optional[ExporterConfig] = None,
    ):
        """
        Args:
            output_path: 출력 파일 경로. None이면 기본 경로 사용.
            config: 내보내기 설정
        """
        app_config = get_config()
        self._output_path = output_path or app_config.jobs_json_path
        self._config = config or app_config.exporter

        # 출력 디렉토리 생성
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def new_threshold_hours(self) -> int:
        """새 공고 판정 시간 (시간)"""
        return self._config.new_threshold_hours

    def export(self, jobs: List[JobPosting]) -> Path:
        """채용 공고를 JSON 파일로 내보내기

        Args:
            jobs: 내보낼 채용 공고 리스트

        Returns:
            저장된 파일 경로
        """
        # 기존 데이터 로드
        existing_jobs = self._load_existing_jobs()

        # 새 데이터 병합
        merged_jobs, new_count = self._merge_jobs(jobs, existing_jobs)

        # 마감된 공고 필터링
        active_jobs = self._filter_expired(merged_jobs)

        # 정렬
        sorted_jobs = self._sort_jobs(active_jobs)

        # 통계 계산
        stats = self._calculate_stats(sorted_jobs)

        # 저장
        output_data = {
            "updated_at": datetime.now().isoformat(),
            "stats": stats,
            "jobs": sorted_jobs,
        }

        self._save_json(output_data)

        logger.info(
            f"JSON 저장 완료: {self._output_path} "
            f"({len(sorted_jobs)}건, 신규 {new_count}건)"
        )

        return self._output_path

    def _load_existing_jobs(self) -> Dict[str, Dict[str, Any]]:
        """기존 JSON 파일에서 데이터 로드"""
        if not self._output_path.exists():
            return {}

        try:
            with open(self._output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {job["id"]: job for job in data.get("jobs", [])}
        except Exception as e:
            logger.warning(f"기존 데이터 로드 실패: {e}")
            return {}

    def _merge_jobs(
        self,
        new_jobs: List[JobPosting],
        existing_jobs: Dict[str, Dict[str, Any]],
    ) -> tuple[Dict[str, Dict[str, Any]], int]:
        """새 공고와 기존 공고 병합

        Returns:
            (병합된 공고 딕셔너리, 신규 공고 수)
        """
        now = datetime.now()
        new_count = 0

        for job in new_jobs:
            job_dict = self._job_to_dict(job)

            if job.id not in existing_jobs:
                # 신규 공고
                job_dict["first_seen_at"] = now.isoformat()
                job_dict["is_new"] = True
                new_count += 1
            else:
                # 기존 공고 - first_seen_at 유지
                existing = existing_jobs[job.id]
                job_dict["first_seen_at"] = existing.get(
                    "first_seen_at", now.isoformat()
                )

                # is_new 판정 (시간 기반)
                job_dict["is_new"] = self._is_new_job(job_dict["first_seen_at"])
                if job_dict["is_new"]:
                    new_count += 1

            existing_jobs[job.id] = job_dict

        return existing_jobs, new_count

    def _is_new_job(self, first_seen_at: str) -> bool:
        """공고가 '새 공고'인지 판정"""
        try:
            first_seen = datetime.fromisoformat(first_seen_at)
            hours_since = (datetime.now() - first_seen).total_seconds() / 3600
            return hours_since <= self.new_threshold_hours
        except Exception:
            return False

    def _filter_expired(self, jobs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """마감된 공고 필터링"""
        now = datetime.now()
        active = []

        for job in jobs.values():
            deadline = job.get("deadline")
            if deadline:
                try:
                    deadline_dt = datetime.fromisoformat(deadline)
                    if deadline_dt < now:
                        continue  # 마감된 공고 제외
                except Exception:
                    pass
            active.append(job)

        return active

    def _sort_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """마감일 기준 정렬"""
        return sorted(
            jobs,
            key=lambda x: (
                x.get("deadline") or "9999-99-99",
                x.get("crawled_at") or "",
            ),
        )

    def _calculate_stats(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """통계 계산"""
        now = datetime.now()

        total = len(jobs)
        new_count = sum(1 for j in jobs if j.get("is_new"))

        # 7일 내 마감
        expiring = 0
        for job in jobs:
            if job.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(job["deadline"])
                    days_left = (deadline - now).days
                    if 0 <= days_left <= 7:
                        expiring += 1
                except Exception:
                    pass

        # 소스별 통계
        by_source = {}
        for source in JobSource:
            count = sum(1 for j in jobs if j.get("source") == source.value)
            by_source[source.value] = count

        return {
            "total": total,
            "new": new_count,
            "expiring_7days": expiring,
            "by_source": by_source,
        }

    def _job_to_dict(self, job: JobPosting) -> Dict[str, Any]:
        """JobPosting을 dict로 변환"""
        return {
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "company_logo": job.company_logo,
            "experience_level": (
                job.experience_level.value
                if hasattr(job.experience_level, "value")
                else job.experience_level
            ),
            "experience_text": job.experience_text,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "deadline_text": job.deadline_text,
            "internship_period": job.internship_period,
            "location": job.location,
            "salary": job.salary,
            "employment_type": job.employment_type,
            "requirements": job.requirements or [],
            "preferred": job.preferred or [],
            "tech_stack": job.tech_stack or [],
            "description": job.description,
            "source": job.source.value if hasattr(job.source, "value") else job.source,
            "source_url": job.source_url,
            "crawled_at": job.crawled_at.isoformat() if job.crawled_at else None,
            "is_new": job.is_new,
            "category": job.category,
            "category_score": job.category_score,
        }

    def _save_json(self, data: Dict[str, Any]) -> None:
        """JSON 파일 저장"""
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
