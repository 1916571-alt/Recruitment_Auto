"""
크롤러 기본 클래스
"""
import asyncio
import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from src.models import JobPosting, JobSource
from config import settings


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""

    source: JobSource

    def __init__(self):
        self.settings = settings.crawler
        self.filter_settings = settings.filter
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.settings.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        """URL에서 HTML 가져오기"""
        try:
            await asyncio.sleep(self.settings.request_delay_seconds)
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"Failed to fetch {url}: status {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    async def fetch_json(self, url: str, **kwargs) -> Optional[dict]:
        """URL에서 JSON 가져오기"""
        try:
            await asyncio.sleep(self.settings.request_delay_seconds)
            async with self.session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                logger.warning(f"Failed to fetch {url}: status {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """HTML 파싱"""
        return BeautifulSoup(html, "html.parser")

    def generate_id(self, source: str, source_id: str) -> str:
        """고유 ID 생성"""
        unique_str = f"{source}_{source_id}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]

    def matches_filter(self, job: JobPosting) -> bool:
        """필터 조건에 맞는지 확인"""
        # 제외 키워드 체크 (타이틀에서)
        title_lower = job.title.lower()
        for exclude in self.filter_settings.exclude_keywords:
            if exclude.lower() in title_lower:
                logger.debug(f"제외(타이틀): {job.title} - '{exclude}'")
                return False

        # 직무 키워드 체크 (OR 조건)
        job_match = False
        search_text = f"{job.title} {job.description or ''}".lower()
        for keyword in self.filter_settings.job_keywords:
            if keyword.lower() in search_text:
                job_match = True
                break

        if not job_match:
            return False

        # 경력 조건 체크 - 신입 가능한 공고만 포함
        return self._is_entry_level_friendly(job.experience_text)

    def _is_entry_level_friendly(self, exp_text: Optional[str]) -> bool:
        """신입이 지원 가능한 공고인지 확인"""
        if not exp_text:
            # 경력 조건이 없으면 포함
            return True

        exp_lower = exp_text.lower().strip()

        # 1. 신입 가능 키워드가 있으면 바로 포함
        entry_keywords = ["신입", "경력무관", "경력 무관", "인턴", "intern", "entry", "junior", "신입/경력", "경력/신입"]
        for keyword in entry_keywords:
            if keyword in exp_lower:
                return True

        # 2. "경력 N년" 패턴 체크 - 경력직만 요구하면 제외
        # 패턴: "경력 1년", "경력1년", "경력2년↑", "1년 이상", "1~3년", "경력 1-3년" 등
        career_patterns = [
            r'경력\s*(\d+)\s*년?\s*[↑이상]?',  # 경력 1년, 경력1년, 경력2년↑
            r'(\d+)\s*년\s*이상',               # 1년 이상
            r'(\d+)\s*~\s*(\d+)\s*년',          # 1~3년
            r'(\d+)\s*-\s*(\d+)\s*년',          # 1-3년
            r'(\d+)\s*년\s*[~↑]',               # 1년~, 1년↑
            r'경력\s*(\d+)\s*[~\-]\s*(\d+)',    # 경력 1~3, 경력 1-3
        ]

        for pattern in career_patterns:
            match = re.search(pattern, exp_lower)
            if match:
                # 숫자 추출
                years = [int(g) for g in match.groups() if g and g.isdigit()]
                if years:
                    min_years = min(years)
                    # 1년 이상 경력 요구하면 제외
                    if min_years >= 1:
                        logger.debug(f"제외(경력): '{exp_text}' - 최소 {min_years}년 요구")
                        return False

        # 3. 순수 "경력" 단어만 있고 신입 키워드 없으면 제외
        if "경력" in exp_lower and not any(k in exp_lower for k in ["신입", "무관"]):
            logger.debug(f"제외(경력만): '{exp_text}'")
            return False

        # 그 외의 경우 포함
        return True

    @abstractmethod
    async def crawl(self) -> List[JobPosting]:
        """채용 공고 크롤링 (구현 필요)"""
        pass

    @abstractmethod
    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기 (구현 필요)"""
        pass
