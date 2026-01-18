"""
로켓펀치 크롤러 (스타트업 특화)

로켓펀치는 Next.js SPA로 전환되어 sitemap 기반 크롤링을 사용합니다.
"""
import re
import gzip
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from io import BytesIO

from loguru import logger

from .base import BaseCrawler
from src.models import JobPosting, JobSource, ExperienceLevel


class RocketPunchCrawler(BaseCrawler):
    """로켓펀치 크롤러 (스타트업 특화)"""

    source = JobSource.ROCKETPUNCH
    BASE_URL = "https://www.rocketpunch.com"
    SITEMAP_URL = "https://image.rocketpunch.com/sitemap/jobs-0.xml.gz"

    # 최대 수집 개수
    MAX_JOBS = 50

    async def crawl(self) -> List[JobPosting]:
        """sitemap에서 최근 채용 공고 크롤링"""
        # 1. sitemap에서 최근 채용공고 URL 추출
        job_urls = await self._fetch_sitemap_urls()

        if not job_urls:
            logger.warning("[로켓펀치] sitemap에서 채용공고를 찾을 수 없습니다")
            return []

        logger.info(f"[로켓펀치] sitemap에서 {len(job_urls)}개 URL 발견, 최근 {self.MAX_JOBS}개 크롤링")

        # 2. 각 페이지에서 메타 태그로 정보 추출
        all_jobs = []
        for url in job_urls[:self.MAX_JOBS]:
            job = await self._fetch_job_from_url(url)
            if job:
                all_jobs.append(job)

        # 3. 필터링
        unique_jobs = []
        for job in all_jobs:
            passed, category, score = self._filter.matches_with_category(job)
            if passed:
                job.category = category
                job.category_score = score
                unique_jobs.append(job)

        logger.info(f"[로켓펀치] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _fetch_sitemap_urls(self) -> List[str]:
        """sitemap에서 최근 채용공고 URL 추출"""
        try:
            # gzip으로 압축된 sitemap 다운로드
            response = await self.http_client.get(self.SITEMAP_URL)
            if not response:
                return []

            # gzip 압축 해제
            try:
                xml_content = gzip.decompress(response.encode('latin-1')).decode('utf-8')
            except:
                xml_content = response

            # URL과 lastmod 추출
            url_pattern = r'<loc>(https://www\.rocketpunch\.com/jobs/\d+)</loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>'
            matches = re.findall(url_pattern, xml_content)

            # lastmod 기준 정렬 (최신순)
            sorted_urls = sorted(matches, key=lambda x: x[1], reverse=True)

            return [url for url, _ in sorted_urls]

        except Exception as e:
            logger.debug(f"[로켓펀치] sitemap 파싱 오류: {e}")
            return []

    async def _fetch_job_from_url(self, url: str) -> Optional[JobPosting]:
        """채용공고 페이지에서 메타 태그로 정보 추출"""
        try:
            html = await self.fetch(url)
            if not html:
                return None

            return self._parse_job_page(html, url)

        except Exception as e:
            logger.debug(f"[로켓펀치] 페이지 파싱 오류: {e}")
            return None

    def _parse_job_page(self, html: str, url: str) -> Optional[JobPosting]:
        """페이지에서 메타 태그로 채용 정보 추출"""
        soup = self.parse_html(html)

        # og:title에서 회사명과 포지션 추출 (형식: "회사명 - 포지션 채용")
        og_title = soup.find("meta", property="og:title")
        if not og_title:
            return None

        title_content = og_title.get("content", "")
        if " - " not in title_content:
            return None

        parts = title_content.split(" - ", 1)
        company_name = parts[0].strip()
        title = parts[1].replace(" 채용", "").strip() if len(parts) > 1 else ""

        if not title or not company_name:
            return None

        # source_id 추출
        source_id = url.rstrip('/').split('/')[-1]

        # og:description에서 추가 정보 추출
        og_desc = soup.find("meta", property="og:description")
        description = og_desc.get("content", "")[:500] if og_desc else ""

        # og:image
        og_image = soup.find("meta", property="og:image")
        company_logo = og_image.get("content", "") if og_image else None

        # 경력 레벨 추정 (title에서)
        experience_level = self._determine_experience_level(title)

        return JobPosting(
            id=self.generate_id(self.source.value, source_id),
            title=title,
            company_name=company_name,
            company_logo=company_logo,
            experience_level=experience_level,
            description=description,
            source=self.source,
            source_url=url,
            source_id=source_id,
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
