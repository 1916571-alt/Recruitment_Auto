"""
원티드 크롤러 (IT/스타트업 특화)

원티드는 GraphQL API를 사용하지만, 일반 API도 제공합니다.
"""
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger

from .base import BaseCrawler
from src.models import JobPosting, JobSource, ExperienceLevel


class WantedCrawler(BaseCrawler):
    """원티드 크롤러 (IT/스타트업 특화)"""

    source = JobSource.WANTED
    BASE_URL = "https://www.wanted.co.kr"
    API_URL = "https://www.wanted.co.kr/api/v4"

    # 페이지네이션 설정
    MAX_PAGES = 3
    ITEMS_PER_PAGE = 20

    # 직군별 태그 ID
    TAG_IDS = {
        "backend": [872, 669],       # 서버 개발자, 백엔드 개발자
        "frontend": [669, 873],      # 프론트엔드 개발자
        "data": [655, 1024, 1025],   # 데이터 분석가, 데이터 엔지니어, ML 엔지니어
        "pm": [876, 877],            # 서비스 기획자, PM
    }

    # 직군 검색 키워드
    SEARCH_KEYWORDS = [
        "백엔드 신입",
        "프론트엔드 신입",
        "데이터 분석 신입",
        "서비스 기획 신입",
        "서버 개발자",
    ]

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 목록 크롤링"""
        all_jobs = []

        # 키워드별로 검색
        for keyword in self.SEARCH_KEYWORDS:
            jobs = await self._search_jobs_with_pagination(keyword)
            all_jobs.extend(jobs)
            logger.info(f"[원티드] '{keyword}' 검색 결과: {len(jobs)}건")

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

        logger.info(f"[원티드] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _search_jobs_with_pagination(self, keyword: str) -> List[JobPosting]:
        """키워드로 채용 공고 검색 (페이지네이션)"""
        all_jobs = []
        offset = 0

        for page in range(1, self.MAX_PAGES + 1):
            jobs, has_more = await self._search_jobs(keyword, offset)
            all_jobs.extend(jobs)

            if not has_more or len(jobs) < self.ITEMS_PER_PAGE:
                break

            offset += self.ITEMS_PER_PAGE
            logger.debug(f"[원티드] '{keyword}' 페이지 {page}: {len(jobs)}건")

        return all_jobs

    async def _search_jobs(
        self,
        keyword: str,
        offset: int = 0
    ) -> tuple[List[JobPosting], bool]:
        """API로 채용 공고 검색"""
        url = f"{self.API_URL}/jobs"
        params = {
            "query": keyword,
            "limit": self.ITEMS_PER_PAGE,
            "offset": offset,
            "years": "0",  # 신입
            "country": "kr",
            "locations": "all",
            "job_sort": "-confirm_time",  # 최신순
        }

        try:
            data = await self.fetch_json(url, params=params)
            if data and "data" in data:
                jobs = self._parse_api_response(data)
                has_more = len(data.get("data", [])) >= self.ITEMS_PER_PAGE
                return jobs, has_more
        except Exception as e:
            logger.debug(f"[원티드] API 오류: {e}")

        # HTML 크롤링으로 대체
        jobs = await self._fetch_jobs_html(keyword, offset)
        return jobs, len(jobs) >= self.ITEMS_PER_PAGE

    async def _fetch_jobs_html(self, keyword: str, offset: int) -> List[JobPosting]:
        """HTML 페이지에서 채용 공고 목록 파싱"""
        page = (offset // self.ITEMS_PER_PAGE) + 1
        url = f"{self.BASE_URL}/search?query={keyword}&tab=position"
        html = await self.fetch(url)

        if not html:
            return []

        return self._parse_html_list(html)

    def _parse_api_response(self, data: Dict[str, Any]) -> List[JobPosting]:
        """API 응답 파싱"""
        jobs = []
        job_list = data.get("data", [])

        for item in job_list:
            try:
                job = self._parse_api_item(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[원티드] API 파싱 오류: {e}")
                continue

        return jobs

    def _parse_api_item(self, item: Dict[str, Any]) -> Optional[JobPosting]:
        """API 응답 항목 파싱"""
        job_id = str(item.get("id", ""))
        if not job_id:
            return None

        title = item.get("position", "")
        company = item.get("company", {})
        company_name = company.get("name", "")

        if not title or not company_name:
            return None

        # 경력 조건
        appeal = item.get("appeal", "")
        experience_text = ""
        experience_level = ExperienceLevel.ANY

        # 경력 정보 파싱
        if "years" in item:
            years = item["years"]
            if years == 0:
                experience_level = ExperienceLevel.ENTRY
                experience_text = "신입"
            elif years == -1:
                experience_level = ExperienceLevel.ANY
                experience_text = "경력무관"
            else:
                experience_level = ExperienceLevel.EXPERIENCED
                experience_text = f"{years}년 이상"

        # 기술 스택 (skill_tags에서 추출)
        skill_tags = item.get("skill_tags", [])
        tech_stack = []
        for tag in skill_tags:
            if isinstance(tag, dict):
                tech_stack.append(tag.get("title", ""))
            elif isinstance(tag, str):
                tech_stack.append(tag)
        tech_stack = [t for t in tech_stack if t][:10]

        # 위치
        location = ""
        address = item.get("address", {})
        if address:
            if isinstance(address, dict):
                location = address.get("full_location", "")
            elif isinstance(address, str):
                location = address

        # 회사 로고
        company_logo = company.get("logo_img", {})
        if isinstance(company_logo, dict):
            company_logo = company_logo.get("origin", "")

        # 급여 (reward 정보)
        salary = ""
        reward = item.get("reward", {})
        if reward and isinstance(reward, dict):
            formatted = reward.get("formatted_total", "")
            if formatted:
                salary = f"합격 보상금: {formatted}"

        return JobPosting(
            id=self.generate_id(self.source.value, job_id),
            title=title,
            company_name=company_name,
            company_logo=company_logo if isinstance(company_logo, str) else None,
            experience_level=experience_level,
            experience_text=experience_text,
            location=location,
            salary=salary,
            tech_stack=tech_stack,
            source=self.source,
            source_url=f"{self.BASE_URL}/wd/{job_id}",
            source_id=job_id,
            crawled_at=datetime.now(),
        )

    def _parse_html_list(self, html: str) -> List[JobPosting]:
        """HTML에서 채용 공고 목록 파싱"""
        soup = self.parse_html(html)
        jobs = []

        # 채용 공고 카드 찾기
        job_cards = soup.select("[class*='JobCard'], a[href*='/wd/'], [data-position-id]")

        for card in job_cards:
            try:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[원티드] HTML 파싱 오류: {e}")
                continue

        return jobs

    def _parse_html_card(self, card) -> Optional[JobPosting]:
        """HTML 카드에서 채용 공고 파싱"""
        # 링크에서 job ID 추출
        link = card.get("href", "")
        if not link:
            link_elem = card.select_one("a[href*='/wd/']")
            if link_elem:
                link = link_elem.get("href", "")

        if not link or "/wd/" not in link:
            return None

        if link.startswith("/"):
            link = f"{self.BASE_URL}{link}"

        source_id = self._extract_source_id(link)

        # 회사명
        company_elem = card.select_one("[class*='company'], [class*='Company']")
        company_name = company_elem.get_text(strip=True) if company_elem else ""

        # 포지션명
        title_elem = card.select_one("[class*='position'], [class*='title'], h3, h4")
        title = title_elem.get_text(strip=True) if title_elem else ""

        if not title or not company_name:
            return None

        # 위치
        loc_elem = card.select_one("[class*='location'], [class*='address']")
        location = loc_elem.get_text(strip=True) if loc_elem else ""

        return JobPosting(
            id=self.generate_id(self.source.value, source_id),
            title=title,
            company_name=company_name,
            experience_level=ExperienceLevel.ANY,
            location=location,
            source=self.source,
            source_url=link,
            source_id=source_id,
            crawled_at=datetime.now(),
        )

    def _extract_source_id(self, url: str) -> str:
        """URL에서 공고 ID 추출"""
        match = re.search(r"/wd/(\d+)", url)
        if match:
            return match.group(1)
        return url.rstrip('/').split('/')[-1][:20]

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기"""
        if not job.source_id:
            return job

        # API로 상세 정보 조회
        url = f"{self.API_URL}/jobs/{job.source_id}"

        try:
            data = await self.fetch_json(url)
            if data and "job" in data:
                result = data["job"]

                # 상세 설명
                detail = result.get("detail", {})
                if detail:
                    # 주요 업무
                    main_tasks = detail.get("main_tasks", "")
                    # 자격 요건
                    requirements_text = detail.get("requirements", "")
                    # 우대 사항
                    preferred_text = detail.get("preferred_points", "")
                    # 복지
                    benefits = detail.get("benefits", "")

                    # 상세 설명 조합
                    description_parts = []
                    if main_tasks:
                        description_parts.append(f"[주요 업무] {main_tasks}")
                    if requirements_text:
                        description_parts.append(f"[자격 요건] {requirements_text}")

                    job.description = "\n".join(description_parts)[:500]

                    # 자격 요건 파싱
                    if requirements_text:
                        job.requirements = self._parse_requirements(requirements_text)

                    # 우대 사항 파싱
                    if preferred_text:
                        job.preferred = self._parse_requirements(preferred_text)

                # 기술 스택
                skill_tags = result.get("skill_tags", [])
                if skill_tags:
                    tech_stack = []
                    for tag in skill_tags:
                        if isinstance(tag, dict):
                            tech_stack.append(tag.get("title", ""))
                        elif isinstance(tag, str):
                            tech_stack.append(tag)
                    job.tech_stack = [t for t in tech_stack if t][:10]

                job.updated_at = datetime.now()

        except Exception as e:
            logger.debug(f"[원티드] 상세 정보 조회 실패: {e}")
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
        desc_elem = soup.select_one("[class*='JobDescription'], [class*='description']")
        if desc_elem:
            job.description = desc_elem.get_text(strip=True)[:500]

        # 기술 스택
        tech_elems = soup.select("[class*='SkillTag'], [class*='skill'] span")
        if tech_elems:
            job.tech_stack = [t.get_text(strip=True) for t in tech_elems][:10]

        job.updated_at = datetime.now()
        return job

    def _parse_requirements(self, text: str) -> List[str]:
        """요구사항 텍스트를 리스트로 파싱"""
        if not text:
            return []

        # 줄바꿈, 불릿 등으로 분리
        lines = re.split(r'[\n\r•·\-]', text)
        requirements = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # 너무 짧은 것 제외
                requirements.append(line[:200])

        return requirements[:10]
