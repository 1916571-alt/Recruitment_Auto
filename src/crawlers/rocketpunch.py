"""
로켓펀치 크롤러 (스타트업 특화)

로켓펀치는 API와 HTML 모두 지원합니다.
"""
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from loguru import logger

from .base import BaseCrawler
from src.models import JobPosting, JobSource, ExperienceLevel


class RocketPunchCrawler(BaseCrawler):
    """로켓펀치 크롤러 (스타트업 특화)"""

    source = JobSource.ROCKETPUNCH
    BASE_URL = "https://www.rocketpunch.com"
    API_URL = "https://www.rocketpunch.com/api"

    # 페이지네이션 설정
    MAX_PAGES = 3
    ITEMS_PER_PAGE = 20

    # 직군별 태그
    JOB_TAGS = {
        "backend": ["서버", "백엔드", "Backend", "Server"],
        "frontend": ["프론트엔드", "Frontend", "웹개발"],
        "data": ["데이터", "Data", "AI", "ML", "머신러닝"],
        "pm": ["PM", "기획", "프로덕트"],
    }

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 목록 크롤링"""
        all_jobs = []

        # 각 직군별로 크롤링
        for job_type, keywords in self.JOB_TAGS.items():
            for keyword in keywords[:2]:  # 직군당 2개 키워드만
                jobs = await self._search_jobs_with_pagination(keyword)
                all_jobs.extend(jobs)
                logger.info(f"[로켓펀치] '{keyword}' 검색 결과: {len(jobs)}건")

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

        logger.info(f"[로켓펀치] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _search_jobs_with_pagination(self, keyword: str) -> List[JobPosting]:
        """키워드로 채용 공고 검색 (페이지네이션)"""
        all_jobs = []

        for page in range(1, self.MAX_PAGES + 1):
            jobs = await self._search_jobs(keyword, page)
            all_jobs.extend(jobs)

            if len(jobs) < self.ITEMS_PER_PAGE:
                break

            logger.debug(f"[로켓펀치] '{keyword}' 페이지 {page}: {len(jobs)}건")

        return all_jobs

    async def _search_jobs(self, keyword: str, page: int = 1) -> List[JobPosting]:
        """키워드로 채용 공고 검색"""
        # API 먼저 시도
        api_url = f"{self.API_URL}/jobs/template"
        params = {
            "keywords": keyword,
            "page": page,
            "hiring_type": "0",  # 0: 신입, 1: 경력
        }

        try:
            data = await self.fetch_json(api_url, params=params)
            if data and "data" in data:
                return self._parse_api_response(data)
        except Exception as e:
            logger.debug(f"[로켓펀치] API 오류: {e}")

        # HTML 크롤링 시도
        return await self._fetch_jobs_html(keyword, page)

    async def _fetch_jobs_html(self, keyword: str, page: int) -> List[JobPosting]:
        """HTML 페이지에서 채용 공고 목록 파싱"""
        url = f"{self.BASE_URL}/jobs?keywords={keyword}&page={page}&hiring_type=0"
        html = await self.fetch(url)

        if not html:
            return []

        return self._parse_html_list(html)

    def _parse_api_response(self, data: Dict[str, Any]) -> List[JobPosting]:
        """API 응답 파싱"""
        jobs = []
        job_list = data.get("data", {}).get("jobs", [])

        for item in job_list:
            try:
                job = self._parse_api_item(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[로켓펀치] API 파싱 오류: {e}")
                continue

        return jobs

    def _parse_api_item(self, item: Dict[str, Any]) -> Optional[JobPosting]:
        """API 응답 항목 파싱"""
        job_id = str(item.get("id", ""))
        if not job_id:
            return None

        title = item.get("title", "")
        company = item.get("company", {})
        company_name = company.get("name", "")

        if not title or not company_name:
            return None

        # 경력 조건
        career_type = item.get("career_type", "")
        experience_level = self._determine_experience_level(career_type)
        experience_text = career_type

        # 기술 스택
        tech_stacks = item.get("primary_tags", [])
        tech_stack = [t.get("name", "") for t in tech_stacks if t.get("name")]

        # 마감일
        deadline = None
        deadline_text = ""
        if item.get("deadline"):
            try:
                deadline = datetime.fromisoformat(item["deadline"].replace("Z", "+00:00"))
                deadline_text = deadline.strftime("%Y-%m-%d")
            except:
                deadline_text = item.get("deadline", "")

        # 위치
        location = item.get("location", "")

        # 급여
        salary = ""
        if item.get("min_salary") and item.get("max_salary"):
            salary = f"{item['min_salary']:,}~{item['max_salary']:,}만원"

        return JobPosting(
            id=self.generate_id(self.source.value, job_id),
            title=title,
            company_name=company_name,
            company_logo=company.get("logo"),
            experience_level=experience_level,
            experience_text=experience_text,
            deadline=deadline,
            deadline_text=deadline_text,
            location=location,
            salary=salary,
            tech_stack=tech_stack[:10],
            source=self.source,
            source_url=f"{self.BASE_URL}/jobs/{job_id}",
            source_id=job_id,
            crawled_at=datetime.now(),
        )

    def _parse_html_list(self, html: str) -> List[JobPosting]:
        """HTML에서 채용 공고 목록 파싱"""
        soup = self.parse_html(html)
        jobs = []

        # 채용 공고 카드 찾기
        job_cards = soup.select(".job-item, .company-jobs-item, div[data-job-id]")

        for card in job_cards:
            try:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[로켓펀치] HTML 파싱 오류: {e}")
                continue

        return jobs

    def _parse_html_card(self, card) -> Optional[JobPosting]:
        """HTML 카드에서 채용 공고 파싱"""
        # 공고 ID
        job_id = card.get("data-job-id", "")
        if not job_id:
            link_elem = card.select_one("a[href*='/jobs/']")
            if link_elem:
                href = link_elem.get("href", "")
                match = re.search(r"/jobs/(\d+)", href)
                if match:
                    job_id = match.group(1)

        if not job_id:
            return None

        # 회사명
        company_elem = card.select_one(".company-name, .name a, h4 a")
        company_name = company_elem.get_text(strip=True) if company_elem else ""

        # 포지션명
        title_elem = card.select_one(".job-title, .position a, h5 a")
        title = title_elem.get_text(strip=True) if title_elem else ""

        if not title or not company_name:
            return None

        # 기술 스택
        tech_elems = card.select(".job-tag, .tag, .skill-tag")
        tech_stack = [t.get_text(strip=True) for t in tech_elems][:10]

        # 경력
        career_elem = card.select_one(".career, .experience")
        experience_text = career_elem.get_text(strip=True) if career_elem else ""
        experience_level = self._determine_experience_level(experience_text)

        # 위치
        loc_elem = card.select_one(".location, .address")
        location = loc_elem.get_text(strip=True) if loc_elem else ""

        return JobPosting(
            id=self.generate_id(self.source.value, job_id),
            title=title,
            company_name=company_name,
            experience_level=experience_level,
            experience_text=experience_text,
            location=location,
            tech_stack=tech_stack,
            source=self.source,
            source_url=f"{self.BASE_URL}/jobs/{job_id}",
            source_id=job_id,
            crawled_at=datetime.now(),
        )

    def _determine_experience_level(self, text: str) -> ExperienceLevel:
        """경력 레벨 결정"""
        if not text:
            return ExperienceLevel.ANY
        text = text.lower()
        if "신입" in text or "entry" in text:
            return ExperienceLevel.ENTRY
        if "경력무관" in text or "경력 무관" in text or "무관" in text:
            return ExperienceLevel.ANY
        if "인턴" in text or "intern" in text:
            return ExperienceLevel.INTERN
        if any(x in text for x in ["경력", "시니어", "senior"]):
            return ExperienceLevel.EXPERIENCED
        return ExperienceLevel.ANY

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기"""
        if not job.source_id:
            return job

        # API로 상세 정보 조회 시도
        api_url = f"{self.API_URL}/jobs/{job.source_id}"

        try:
            data = await self.fetch_json(api_url)
            if data and "data" in data:
                result = data["data"]

                # 상세 설명
                if result.get("description"):
                    job.description = result["description"][:500]

                # 자격 요건
                if result.get("requirements"):
                    job.requirements = result["requirements"][:10] if isinstance(result["requirements"], list) else [result["requirements"][:200]]

                # 우대 사항
                if result.get("preferred"):
                    job.preferred = result["preferred"][:10] if isinstance(result["preferred"], list) else [result["preferred"][:200]]

                # 회사 정보
                company = result.get("company", {})
                if company.get("logo"):
                    job.company_logo = company["logo"]

                job.updated_at = datetime.now()

        except Exception as e:
            logger.debug(f"[로켓펀치] 상세 정보 조회 실패: {e}")
            # HTML 크롤링으로 대체
            await self._get_job_detail_html(job)

        return job

    async def _get_job_detail_html(self, job: JobPosting) -> JobPosting:
        """HTML에서 채용 공고 상세 정보 가져오기"""
        html = await self.fetch(job.source_url)
        if not html:
            return job

        soup = self.parse_html(html)

        # 상세 설명
        desc_elem = soup.select_one(".job-description, .description, .content")
        if desc_elem:
            job.description = desc_elem.get_text(strip=True)[:500]

        # 자격 요건
        req_elem = soup.select_one(".requirements, .qualifications")
        if req_elem:
            requirements = []
            for li in req_elem.select("li")[:10]:
                requirements.append(li.get_text(strip=True))
            if requirements:
                job.requirements = requirements

        # 기술 스택
        tech_elems = soup.select(".tech-stack .tag, .skill-tags .tag")
        if tech_elems:
            job.tech_stack = [t.get_text(strip=True) for t in tech_elems][:10]

        job.updated_at = datetime.now()
        return job
