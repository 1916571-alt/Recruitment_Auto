"""
잡코리아 크롤러
"""
import re
from typing import List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

from loguru import logger

from .base import BaseCrawler
from src.models import JobPosting, JobSource, ExperienceLevel
from config.settings import settings


class JobKoreaCrawler(BaseCrawler):
    """잡코리아 크롤러"""

    source = JobSource.JOBKOREA
    BASE_URL = "https://www.jobkorea.co.kr"

    # 페이지네이션 설정
    MAX_PAGES = 3
    ITEMS_PER_PAGE = 40

    @property
    def search_keywords(self) -> list:
        return settings.filter.job_keywords

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 목록 크롤링"""
        all_jobs = []

        for keyword in self.search_keywords:
            jobs = await self._search_jobs_with_pagination(keyword)
            all_jobs.extend(jobs)
            logger.info(f"[잡코리아] '{keyword}' 검색 결과: {len(jobs)}건")

        # 중복 제거 + 필터링
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job.source_id not in seen_ids:
                seen_ids.add(job.source_id)
                passed, category, score = self._filter.matches_with_category(job)
                if passed:
                    job.category = category
                    job.category_score = score
                    unique_jobs.append(job)

        logger.info(f"[잡코리아] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _search_jobs_with_pagination(self, keyword: str) -> List[JobPosting]:
        """키워드로 채용 공고 검색 (페이지네이션)"""
        all_jobs = []

        for page in range(1, self.MAX_PAGES + 1):
            jobs = await self._search_jobs(keyword, page)
            all_jobs.extend(jobs)

            if len(jobs) < self.ITEMS_PER_PAGE:
                break

            logger.debug(f"[잡코리아] '{keyword}' 페이지 {page}: {len(jobs)}건")

        return all_jobs

    async def _search_jobs(self, keyword: str, page: int = 1) -> List[JobPosting]:
        """키워드로 채용 공고 검색 (단일 페이지)"""
        params = {
            "stext": keyword,
            "careerType": "1,8",  # 1: 신입, 8: 경력무관
            "tabType": "recruit",
            "Page_No": page,
        }

        url = f"{self.BASE_URL}/Search/?{urlencode(params, quote_via=quote)}"
        html = await self.fetch(url)

        if not html:
            return []

        return self._parse_job_list(html)

    def _parse_job_list(self, html: str) -> List[JobPosting]:
        """채용 공고 목록 파싱"""
        soup = self.parse_html(html)
        jobs = []

        # 채용 공고 항목 찾기
        job_items = soup.select(".list-default .list-post")
        if not job_items:
            job_items = soup.select(".recruit-info")
        if not job_items:
            job_items = soup.select(".list-item")

        for item in job_items:
            try:
                job = self._parse_job_item(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[잡코리아] 파싱 오류: {e}")
                continue

        return jobs

    def _parse_job_item(self, item) -> Optional[JobPosting]:
        """채용 공고 항목 파싱"""
        # 회사명
        company_elem = item.select_one(".corp-name a, .name a, .company-name")
        if not company_elem:
            return None
        company_name = company_elem.get_text(strip=True)

        # 포지션명
        title_elem = item.select_one(".information-title a, .title a, .job-title")
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # 링크
        link = title_elem.get("href", "")
        if link.startswith("/"):
            link = f"{self.BASE_URL}{link}"

        # 공고 ID 추출
        source_id = self._extract_source_id(link)

        # 경력 조건
        experience_text = ""
        exp_elem = item.select_one(".option .exp, .exp-text, .career")
        if exp_elem:
            experience_text = exp_elem.get_text(strip=True)

        experience_level = self._determine_experience_level(experience_text)

        # 마감일
        deadline_text = ""
        date_elem = item.select_one(".date, .deadline, .end-date")
        if date_elem:
            deadline_text = date_elem.get_text(strip=True)

        deadline = self._parse_deadline(deadline_text)

        # 위치
        location = ""
        loc_elem = item.select_one(".loc, .location, .work-place")
        if loc_elem:
            location = loc_elem.get_text(strip=True)

        return JobPosting(
            id=self.generate_id(self.source.value, source_id),
            title=title,
            company_name=company_name,
            experience_level=experience_level,
            experience_text=experience_text,
            deadline=deadline,
            deadline_text=deadline_text,
            location=location,
            source=self.source,
            source_url=link,
            source_id=source_id,
            crawled_at=datetime.now(),
        )

    def _extract_source_id(self, url: str) -> str:
        """URL에서 공고 ID 추출"""
        # /Recruit/GI_Read/xxxxx 형식
        match = re.search(r"GI_Read/(\d+)", url)
        if match:
            return match.group(1)
        # oZwork/xxxxx 형식
        match = re.search(r"oZwork/(\d+)", url)
        if match:
            return match.group(1)
        return url.rstrip('/').split('/')[-1][:20]

    def _determine_experience_level(self, text: str) -> ExperienceLevel:
        """경력 레벨 결정"""
        if not text:
            return ExperienceLevel.ANY
        text = text.lower()
        if "인턴" in text:
            return ExperienceLevel.INTERN
        if "경력무관" in text or "경력 무관" in text:
            return ExperienceLevel.ANY
        if "신입" in text:
            return ExperienceLevel.ENTRY
        if any(x in text for x in ["경력", "시니어", "senior"]):
            return ExperienceLevel.EXPERIENCED
        return ExperienceLevel.ANY

    def _parse_deadline(self, text: str) -> Optional[datetime]:
        """마감일 파싱"""
        if not text:
            return None

        today = datetime.now()

        # D-7 형식
        match = re.search(r"D-(\d+)", text, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            return today + timedelta(days=days)

        # YYYY.MM.DD 형식
        match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day)

        # MM/DD 또는 MM.DD 형식
        match = re.search(r"(\d{1,2})[/.](\d{1,2})", text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            year = today.year
            deadline = datetime(year, month, day)
            if deadline < today:
                deadline = datetime(year + 1, month, day)
            return deadline

        return None

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기"""
        if not job.source_url:
            return job

        html = await self.fetch(job.source_url)
        if not html:
            return job

        soup = self.parse_html(html)

        # 상세 설명
        desc_elem = soup.select_one(".view-detail-content, .recruit-view-detail, .job-detail")
        if desc_elem:
            job.description = desc_elem.get_text(strip=True)[:500]

        # 자격 요건
        requirements = []
        req_section = soup.select(".requirement-list li, .spec-list li")
        for li in req_section[:10]:
            requirements.append(li.get_text(strip=True))
        if requirements:
            job.requirements = requirements

        # 기술 스택
        tech_elems = soup.select(".skill-tag, .tech-stack span")
        if tech_elems:
            job.tech_stack = [t.get_text(strip=True) for t in tech_elems][:10]

        job.updated_at = datetime.now()
        return job
