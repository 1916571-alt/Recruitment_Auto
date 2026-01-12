"""
크롤러 기본 클래스

단일 책임: 크롤러 공통 기능 제공
의존성 주입: HTTP 클라이언트, 필터를 외부에서 주입 가능
"""
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from src.core.config import get_config
from src.core.interfaces import FilterProtocol, HttpClientProtocol
from src.models import JobPosting, JobSource
from src.services.job_filter import JobFilter

from .http_client import AioHttpClient


class BaseCrawler(ABC):
    """크롤러 기본 클래스

    모든 크롤러가 상속받아야 하는 추상 클래스.
    HTTP 클라이언트와 필터는 의존성 주입으로 제공받습니다.

    사용 예시:
        ```python
        async with SaraminCrawler() as crawler:
            jobs = await crawler.crawl()
        ```
    """

    source: JobSource  # 하위 클래스에서 정의

    def __init__(
        self,
        http_client: Optional[HttpClientProtocol] = None,
        job_filter: Optional[FilterProtocol] = None,
    ):
        """
        Args:
            http_client: HTTP 클라이언트. None이면 기본 클라이언트 사용.
            job_filter: 채용 공고 필터. None이면 기본 필터 사용.
        """
        self._config = get_config().crawler
        self._http_client = http_client
        self._filter = job_filter or JobFilter()
        self._owns_client = http_client is None  # 클라이언트 소유 여부

    @property
    def source_name(self) -> str:
        """데이터 소스 이름"""
        return self.source.value

    async def __aenter__(self) -> "BaseCrawler":
        """컨텍스트 매니저 진입"""
        if self._http_client is None:
            self._http_client = AioHttpClient(self._config)
            await self._http_client.__aenter__()
            self._owns_client = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료"""
        if self._owns_client and self._http_client:
            await self._http_client.__aexit__(exc_type, exc_val, exc_tb)
            self._http_client = None

    @property
    def http_client(self) -> HttpClientProtocol:
        """HTTP 클라이언트"""
        if self._http_client is None:
            raise RuntimeError("HTTP client not initialized. Use async with statement.")
        return self._http_client

    async def fetch(self, url: str) -> Optional[str]:
        """URL에서 HTML 가져오기

        Args:
            url: 요청 URL

        Returns:
            HTML 문자열 또는 None
        """
        return await self.http_client.get(url)

    async def fetch_json(self, url: str, **kwargs) -> Optional[dict]:
        """URL에서 JSON 가져오기

        Args:
            url: 요청 URL
            **kwargs: 추가 옵션

        Returns:
            JSON 딕셔너리 또는 None
        """
        return await self.http_client.get_json(url, **kwargs)

    def parse_html(self, html: str) -> BeautifulSoup:
        """HTML 파싱

        Args:
            html: HTML 문자열

        Returns:
            BeautifulSoup 객체
        """
        return BeautifulSoup(html, "html.parser")

    def generate_id(self, source: str, source_id: str) -> str:
        """고유 ID 생성

        MD5 해시 기반으로 고유 ID를 생성합니다.

        Args:
            source: 데이터 소스 이름
            source_id: 원본 사이트의 공고 ID

        Returns:
            12자리 고유 ID
        """
        unique_str = f"{source}_{source_id}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]

    def matches_filter(self, job: JobPosting) -> bool:
        """필터 조건에 맞는지 확인

        Args:
            job: 확인할 채용 공고

        Returns:
            필터 조건 충족 여부
        """
        return self._filter.matches(job)

    @abstractmethod
    async def crawl(self) -> List[JobPosting]:
        """채용 공고 크롤링

        하위 클래스에서 반드시 구현해야 합니다.

        Returns:
            수집된 채용 공고 리스트
        """
        pass

    @abstractmethod
    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기

        하위 클래스에서 반드시 구현해야 합니다.

        Args:
            job: 기본 정보가 담긴 채용 공고

        Returns:
            상세 정보가 추가된 채용 공고
        """
        pass
