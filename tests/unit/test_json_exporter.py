"""
JSONExporter 단위 테스트
"""
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from src.exporters.json_exporter import JSONExporter
from src.models import ExperienceLevel, JobPosting, JobSource


class TestJSONExporter:
    """JSONExporter 테스트"""

    @pytest.fixture
    def exporter(self, tmp_data_dir: Path) -> JSONExporter:
        """테스트용 JSONExporter"""
        return JSONExporter(output_path=tmp_data_dir / "jobs.json")

    @pytest.fixture
    def sample_job(self) -> JobPosting:
        """샘플 채용 공고"""
        return JobPosting(
            id="test1",
            title="데이터 분석가",
            company_name="테스트 회사",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입",
            deadline=datetime.now() + timedelta(days=7),
            deadline_text="D-7",
            location="서울",
            source=JobSource.SARAMIN,
            source_url="https://example.com/job/1",
            source_id="1",
            crawled_at=datetime.now(),
            is_new=True,
        )

    def test_export_creates_file(
        self, exporter: JSONExporter, sample_job: JobPosting, tmp_data_dir: Path
    ):
        """export가 파일을 생성하는지 테스트"""
        output_path = exporter.export([sample_job])

        assert output_path.exists()
        assert output_path == tmp_data_dir / "jobs.json"

    def test_export_json_structure(
        self, exporter: JSONExporter, sample_job: JobPosting
    ):
        """export된 JSON 구조 테스트"""
        output_path = exporter.export([sample_job])

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "updated_at" in data
        assert "stats" in data
        assert "jobs" in data
        assert len(data["jobs"]) == 1

    def test_export_stats_calculation(
        self, exporter: JSONExporter, sample_jobs
    ):
        """통계 계산 테스트"""
        output_path = exporter.export(sample_jobs)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stats = data["stats"]
        assert stats["total"] > 0
        assert "new" in stats
        assert "expiring_7days" in stats
        assert "by_source" in stats

    def test_export_merges_existing_jobs(
        self, tmp_data_dir: Path, sample_job: JobPosting
    ):
        """기존 데이터와 병합 테스트"""
        output_path = tmp_data_dir / "jobs.json"

        # 기존 데이터 생성
        existing_data = {
            "updated_at": datetime.now().isoformat(),
            "stats": {},
            "jobs": [
                {
                    "id": "existing1",
                    "title": "기존 공고",
                    "company_name": "기존 회사",
                    "first_seen_at": (datetime.now() - timedelta(hours=24)).isoformat(),
                    "is_new": True,
                    "source": "saramin",
                    "source_url": "https://example.com/existing",
                    "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
                }
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # 새 데이터 내보내기
        exporter = JSONExporter(output_path=output_path)
        exporter.export([sample_job])

        # 검증
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 기존 공고 + 새 공고
        assert len(data["jobs"]) >= 1
        job_ids = [j["id"] for j in data["jobs"]]
        assert sample_job.id in job_ids

    def test_export_filters_expired_jobs(
        self, exporter: JSONExporter
    ):
        """마감된 공고 필터링 테스트"""
        expired_job = JobPosting(
            id="expired1",
            title="마감된 공고",
            company_name="회사",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입",
            deadline=datetime.now() - timedelta(days=1),  # 어제 마감
            deadline_text="마감",
            source=JobSource.SARAMIN,
            source_url="https://example.com/expired",
            source_id="expired1",
            crawled_at=datetime.now(),
        )

        active_job = JobPosting(
            id="active1",
            title="활성 공고",
            company_name="회사",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입",
            deadline=datetime.now() + timedelta(days=7),
            deadline_text="D-7",
            source=JobSource.SARAMIN,
            source_url="https://example.com/active",
            source_id="active1",
            crawled_at=datetime.now(),
        )

        output_path = exporter.export([expired_job, active_job])

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        job_ids = [j["id"] for j in data["jobs"]]
        assert "active1" in job_ids
        assert "expired1" not in job_ids

    def test_export_preserves_first_seen_at(
        self, tmp_data_dir: Path
    ):
        """first_seen_at 보존 테스트"""
        output_path = tmp_data_dir / "jobs.json"

        first_seen_time = datetime.now() - timedelta(hours=36)
        existing_data = {
            "updated_at": datetime.now().isoformat(),
            "stats": {},
            "jobs": [
                {
                    "id": "job1",
                    "title": "기존 공고",
                    "company_name": "회사",
                    "first_seen_at": first_seen_time.isoformat(),
                    "is_new": True,
                    "source": "saramin",
                    "source_url": "https://example.com/1",
                    "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
                }
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # 같은 공고 다시 내보내기
        updated_job = JobPosting(
            id="job1",
            title="기존 공고 (업데이트)",
            company_name="회사",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입",
            deadline=datetime.now() + timedelta(days=10),
            deadline_text="D-10",
            source=JobSource.SARAMIN,
            source_url="https://example.com/1",
            source_id="1",
            crawled_at=datetime.now(),
        )

        exporter = JSONExporter(output_path=output_path)
        exporter.export([updated_job])

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        job = next(j for j in data["jobs"] if j["id"] == "job1")
        # first_seen_at이 보존되어야 함
        saved_first_seen = datetime.fromisoformat(job["first_seen_at"])
        assert abs((saved_first_seen - first_seen_time).total_seconds()) < 1

    def test_is_new_based_on_threshold(
        self, tmp_data_dir: Path
    ):
        """is_new 판정 테스트 (48시간 기준)"""
        output_path = tmp_data_dir / "jobs.json"

        # 24시간 전에 발견된 공고 (still new)
        recent_time = datetime.now() - timedelta(hours=24)
        # 72시간 전에 발견된 공고 (not new)
        old_time = datetime.now() - timedelta(hours=72)

        existing_data = {
            "updated_at": datetime.now().isoformat(),
            "stats": {},
            "jobs": [
                {
                    "id": "recent",
                    "title": "최근 공고",
                    "company_name": "회사",
                    "first_seen_at": recent_time.isoformat(),
                    "is_new": True,
                    "source": "saramin",
                    "source_url": "https://example.com/recent",
                    "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
                },
                {
                    "id": "old",
                    "title": "오래된 공고",
                    "company_name": "회사",
                    "first_seen_at": old_time.isoformat(),
                    "is_new": True,
                    "source": "saramin",
                    "source_url": "https://example.com/old",
                    "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
                },
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # 기존 공고만 다시 내보내기 (업데이트 시뮬레이션)
        jobs = [
            JobPosting(
                id="recent",
                title="최근 공고",
                company_name="회사",
                experience_level=ExperienceLevel.ENTRY,
                source=JobSource.SARAMIN,
                source_url="https://example.com/recent",
                deadline=datetime.now() + timedelta(days=10),
            ),
            JobPosting(
                id="old",
                title="오래된 공고",
                company_name="회사",
                experience_level=ExperienceLevel.ENTRY,
                source=JobSource.SARAMIN,
                source_url="https://example.com/old",
                deadline=datetime.now() + timedelta(days=10),
            ),
        ]

        exporter = JSONExporter(output_path=output_path)
        exporter.export(jobs)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        recent_job = next(j for j in data["jobs"] if j["id"] == "recent")
        old_job = next(j for j in data["jobs"] if j["id"] == "old")

        assert recent_job["is_new"] is True  # 48시간 이내
        assert old_job["is_new"] is False  # 48시간 초과
