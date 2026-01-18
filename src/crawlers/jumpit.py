"""
점핏 크롤러 (개발자 특화)

점핏은 API 기반으로 데이터를 제공합니다.
"""
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from loguru import logger

from .base import BaseCrawler
from src.models import JobPosting, JobSource, ExperienceLevel


class JumpitCrawler(BaseCrawler):
    """점핏 크롤러 (개발자 특화)"""

    source = JobSource.JUMPIT
    BASE_URL = "https://www.jumpit.co.kr"
    API_URL = "https://jumpit-api.saramin.co.kr"  # 2026-01 도메인 변경

    # 페이지네이션 설정
    MAX_PAGES = 3
    ITEMS_PER_PAGE = 16

    # 직군별 카테고리 ID
    CATEGORY_IDS = {
        "backend": 1,       # 서버/백엔드
        "frontend": 2,      # 프론트엔드
        "fullstack": 3,     # 풀스택
        "data": 4,          # 데이터 엔지니어
        "ml": 14,           # 머신러닝/AI
    }

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 목록 크롤링"""
        all_jobs = []

        # 각 카테고리별로 크롤링
        for category_name, category_id in self.CATEGORY_IDS.items():
            jobs = await self._fetch_jobs_by_category(category_id, category_name)
            all_jobs.extend(jobs)
            logger.info(f"[점핏] '{category_name}' 카테고리: {len(jobs)}건")

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

        logger.info(f"[점핏] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _fetch_jobs_by_category(
        self,
        category_id: int,
        category_name: str
    ) -> List[JobPosting]:
        """카테고리별 채용 공고 수집"""
        all_jobs = []

        for page in range(1, self.MAX_PAGES + 1):
            jobs = await self._fetch_jobs_page(category_id, page)
            all_jobs.extend(jobs)

            if len(jobs) < self.ITEMS_PER_PAGE:
                break

            logger.debug(f"[점핏] '{category_name}' 페이지 {page}: {len(jobs)}건")

        return all_jobs

    async def _fetch_jobs_page(
        self,
        category_id: int,
        page: int
    ) -> List[JobPosting]:
        """API에서 채용 공고 목록 가져오기"""
        # URL에 파라미터 직접 포함 (API 호환성 보장)
        # career=0: 신입 (career 파라미터는 Integer 타입이어야 함)
        url = (
            f"{self.API_URL}/api/positions"
            f"?jobCategory={category_id}"
            f"&page={page}"
            f"&sort=rsp_rate"
            f"&career=0"
        )

        try:
            data = await self.fetch_json(url)
            if not data or "result" not in data:
                # API가 안 되면 HTML 크롤링 시도
                return await self._fetch_jobs_html(category_id, page)

            return self._parse_api_response(data)

        except Exception as e:
            logger.debug(f"[점핏] API 오류, HTML 크롤링 시도: {e}")
            return await self._fetch_jobs_html(category_id, page)

    async def _fetch_jobs_html(
        self,
        category_id: int,
        page: int
    ) -> List[JobPosting]:
        """HTML 페이지에서 채용 공고 목록 파싱"""
        url = f"{self.BASE_URL}/positions?jobCategory={category_id}&page={page}&career=0"
        html = await self.fetch(url)

        if not html:
            return []

        return self._parse_html_list(html)

    def _parse_api_response(self, data: Dict[str, Any]) -> List[JobPosting]:
        """API 응답 파싱"""
        jobs = []
        positions = data.get("result", {}).get("positions", [])

        for item in positions:
            try:
                job = self._parse_api_item(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[점핏] API 파싱 오류: {e}")
                continue

        return jobs

    def _parse_api_item(self, item: Dict[str, Any]) -> Optional[JobPosting]:
        """API 응답 항목 파싱"""
        position_id = str(item.get("id", ""))
        if not position_id:
            return None

        title = item.get("title", "")
        company_name = item.get("companyName", "")

        if not title or not company_name:
            return None

        # 경력 조건
        min_career = item.get("minCareer", 0)
        max_career = item.get("maxCareer", 0)
        experience_level = self._determine_experience_level_from_career(min_career, max_career)
        experience_text = self._format_career_text(min_career, max_career)

        # 기술 스택 (문자열 리스트)
        tech_stacks = item.get("techStacks", [])
        tech_stack = [t for t in tech_stacks if isinstance(t, str) and t]

        # 마감일
        close_date = item.get("closedAt")
        deadline = None
        deadline_text = ""
        if close_date:
            try:
                deadline = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
                deadline_text = deadline.strftime("%Y-%m-%d")
            except:
                deadline_text = close_date

        # 위치
        locations = item.get("locations", [])
        location = ", ".join(locations) if locations else ""

        return JobPosting(
            id=self.generate_id(self.source.value, position_id),
            title=title,
            company_name=company_name,
            company_logo=item.get("logo"),
            experience_level=experience_level,
            experience_text=experience_text,
            deadline=deadline,
            deadline_text=deadline_text,
            location=location,
            tech_stack=tech_stack[:10],
            source=self.source,
            source_url=f"{self.BASE_URL}/position/{position_id}",
            source_id=position_id,
            crawled_at=datetime.now(),
        )

    def _parse_html_list(self, html: str) -> List[JobPosting]:
        """HTML에서 채용 공고 목록 파싱"""
        soup = self.parse_html(html)
        jobs = []

        # 채용 공고 카드 찾기
        job_cards = soup.select("[class*='position-card'], [class*='JobCard'], a[href*='/position/']")

        for card in job_cards:
            try:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[점핏] HTML 파싱 오류: {e}")
                continue

        return jobs

    def _parse_html_card(self, card) -> Optional[JobPosting]:
        """HTML 카드에서 채용 공고 파싱"""
        # 링크에서 position ID 추출
        link = card.get("href", "")
        if not link:
            link_elem = card.select_one("a[href*='/position/']")
            if link_elem:
                link = link_elem.get("href", "")

        if not link or "/position/" not in link:
            return None

        if link.startswith("/"):
            link = f"{self.BASE_URL}{link}"

        source_id = self._extract_source_id(link)

        # 회사명
        company_elem = card.select_one("[class*='company'], [class*='Company']")
        company_name = company_elem.get_text(strip=True) if company_elem else ""

        # 포지션명
        title_elem = card.select_one("[class*='title'], [class*='Title'], h2, h3")
        title = title_elem.get_text(strip=True) if title_elem else ""

        if not title or not company_name:
            return None

        # 기술 스택
        tech_elems = card.select("[class*='tech'], [class*='skill'], [class*='stack'] span")
        tech_stack = [t.get_text(strip=True) for t in tech_elems][:10]

        # 경력
        career_elem = card.select_one("[class*='career'], [class*='Career']")
        experience_text = career_elem.get_text(strip=True) if career_elem else ""
        experience_level = self._determine_experience_level(experience_text)

        return JobPosting(
            id=self.generate_id(self.source.value, source_id),
            title=title,
            company_name=company_name,
            experience_level=experience_level,
            experience_text=experience_text,
            tech_stack=tech_stack,
            source=self.source,
            source_url=link,
            source_id=source_id,
            crawled_at=datetime.now(),
        )

    def _extract_source_id(self, url: str) -> str:
        """URL에서 공고 ID 추출"""
        match = re.search(r"/position/(\d+)", url)
        if match:
            return match.group(1)
        return url.rstrip('/').split('/')[-1][:20]

    def _determine_experience_level_from_career(
        self,
        min_career: int,
        max_career: int
    ) -> ExperienceLevel:
        """경력 연차로 경력 레벨 결정"""
        if min_career == 0 and max_career == 0:
            return ExperienceLevel.ANY
        if min_career == 0:
            return ExperienceLevel.ENTRY
        if min_career <= 2:
            return ExperienceLevel.JUNIOR
        return ExperienceLevel.EXPERIENCED

    def _determine_experience_level(self, text: str) -> ExperienceLevel:
        """텍스트에서 경력 레벨 결정"""
        if not text:
            return ExperienceLevel.ANY
        text = text.lower()
        if "신입" in text or "0년" in text:
            return ExperienceLevel.ENTRY
        if "경력무관" in text or "경력 무관" in text:
            return ExperienceLevel.ANY
        if "주니어" in text or "1년" in text or "2년" in text:
            return ExperienceLevel.JUNIOR
        return ExperienceLevel.EXPERIENCED

    def _format_career_text(self, min_career: int, max_career: int) -> str:
        """경력 텍스트 포맷팅"""
        if min_career == 0 and max_career == 0:
            return "경력무관"
        if min_career == 0:
            return f"신입~{max_career}년"
        if max_career == 0 or max_career >= 99:
            return f"{min_career}년 이상"
        return f"{min_career}~{max_career}년"

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기"""
        if not job.source_id:
            return job

        # API로 상세 정보 조회 시도
        url = f"{self.API_URL}/api/position/{job.source_id}"

        try:
            data = await self.fetch_json(url)
            if data and "result" in data:
                result = data["result"]

                # 상세 설명
                if result.get("jobDescription"):
                    job.description = result["jobDescription"][:500]

                # 자격 요건
                if result.get("qualifications"):
                    job.requirements = result["qualifications"][:10]

                # 우대 사항
                if result.get("preferredQualifications"):
                    job.preferred = result["preferredQualifications"][:10]

                # 급여
                if result.get("minSalary") and result.get("maxSalary"):
                    job.salary = f"{result['minSalary']:,}~{result['maxSalary']:,}만원"

                job.updated_at = datetime.now()

        except Exception as e:
            logger.debug(f"[점핏] 상세 정보 조회 실패: {e}")

        return job
