"""
크롤러 통합 테스트
"""
import pytest
from unittest.mock import AsyncMock

from src.crawlers import SaraminCrawler, InthisworkCrawler
from src.crawlers.http_client import AioHttpClient
from src.models import JobSource
from tests.conftest import MockHttpClient


class TestSaraminCrawler:
    """사람인 크롤러 테스트"""

    @pytest.fixture
    def crawler(self, mock_http_client: MockHttpClient) -> SaraminCrawler:
        """Mock HTTP 클라이언트를 사용하는 크롤러"""
        return SaraminCrawler(http_client=mock_http_client)

    def test_source_name(self, crawler: SaraminCrawler):
        """소스 이름 테스트"""
        assert crawler.source_name == "saramin"
        assert crawler.source == JobSource.SARAMIN

    @pytest.mark.asyncio
    async def test_crawl_parses_job_cards(
        self, crawler: SaraminCrawler, mock_http_client: MockHttpClient, saramin_html: str
    ):
        """채용 공고 카드 파싱 테스트"""
        # Mock 응답 설정
        mock_http_client.set_response(
            "https://www.saramin.co.kr/zf_user/search/recruit", saramin_html
        )

        # crawl 메서드는 여러 URL을 호출하므로, 모든 URL에 같은 응답 설정
        for keyword in SaraminCrawler.SEARCH_KEYWORDS:
            # URL 패턴에 상관없이 모든 GET 요청에 같은 응답
            pass

        # 실제 구현에서는 URL 매칭이 필요
        # 여기서는 파싱 로직만 테스트
        jobs = crawler._parse_job_list(saramin_html)

        assert len(jobs) >= 1
        job = jobs[0]
        assert job.company_name == "테스트 회사"
        assert "데이터 분석가" in job.title

    def test_parse_deadline_d_format(self, crawler: SaraminCrawler):
        """D-N 형식 마감일 파싱"""
        from datetime import datetime, timedelta

        deadline = crawler._parse_deadline("D-7")
        expected = datetime.now() + timedelta(days=7)

        assert deadline is not None
        assert deadline.date() == expected.date()

    def test_parse_deadline_date_format(self, crawler: SaraminCrawler):
        """MM/DD 형식 마감일 파싱"""
        from datetime import datetime

        deadline = crawler._parse_deadline("~01/20")

        assert deadline is not None
        assert deadline.month == 1
        assert deadline.day == 20

    def test_determine_experience_level(self, crawler: SaraminCrawler):
        """경력 레벨 판정"""
        from src.models import ExperienceLevel

        assert crawler._determine_experience_level("인턴") == ExperienceLevel.INTERN
        assert crawler._determine_experience_level("신입") == ExperienceLevel.ENTRY
        assert crawler._determine_experience_level("경력무관") == ExperienceLevel.ANY
        assert (
            crawler._determine_experience_level("경력 3년 이상")
            == ExperienceLevel.EXPERIENCED
        )

    def test_extract_source_id(self, crawler: SaraminCrawler):
        """소스 ID 추출"""
        url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345"
        source_id = crawler._extract_source_id(url)
        assert source_id == "12345"


class TestInthisworkCrawler:
    """인디스워크 크롤러 테스트"""

    @pytest.fixture
    def crawler(self, mock_http_client: MockHttpClient) -> InthisworkCrawler:
        """Mock HTTP 클라이언트를 사용하는 크롤러"""
        return InthisworkCrawler(http_client=mock_http_client)

    def test_source_name(self, crawler: InthisworkCrawler):
        """소스 이름 테스트"""
        assert crawler.source_name == "inthiswork"
        assert crawler.source == JobSource.INTHISWORK

    def test_parse_job_from_link(self, crawler: InthisworkCrawler):
        """링크에서 채용 공고 파싱"""
        url = "https://inthiswork.com/archives/12345"
        title_text = "네이버｜데이터 분석가"

        job = crawler._parse_job_from_link(url, title_text)

        assert job is not None
        assert job.company_name == "네이버"
        assert job.title == "데이터 분석가"
        assert job.source == JobSource.INTHISWORK

    def test_extract_source_id(self, crawler: InthisworkCrawler):
        """소스 ID 추출"""
        url = "https://inthiswork.com/archives/12345"
        source_id = crawler._extract_source_id(url)
        assert source_id == "12345"

    @pytest.mark.asyncio
    async def test_crawl_with_mock(
        self, crawler: InthisworkCrawler, mock_http_client: MockHttpClient
    ):
        """Mock을 사용한 크롤링 테스트"""
        html = '''
        <html>
        <body>
            <a href="/archives/123">테스트회사｜데이터 분석가</a>
            <a href="/archives/124">다른회사｜ML 엔지니어</a>
        </body>
        </html>
        '''
        mock_http_client.set_response("https://inthiswork.com/data", html)

        # 크롤러 실행 (컨텍스트 매니저 없이 직접 호출)
        jobs = crawler._parse_job_list(html)

        assert len(jobs) == 2
        assert jobs[0].company_name == "테스트회사"
        assert jobs[1].company_name == "다른회사"


class TestBaseCrawlerIntegration:
    """BaseCrawler 통합 테스트"""

    def test_generate_id_consistency(self, mock_http_client: MockHttpClient):
        """ID 생성 일관성 테스트"""
        crawler1 = SaraminCrawler(http_client=mock_http_client)
        crawler2 = SaraminCrawler(http_client=mock_http_client)

        id1 = crawler1.generate_id("saramin", "12345")
        id2 = crawler2.generate_id("saramin", "12345")

        assert id1 == id2
        assert len(id1) == 12

    def test_generate_id_uniqueness(self, mock_http_client: MockHttpClient):
        """ID 생성 유일성 테스트"""
        crawler = SaraminCrawler(http_client=mock_http_client)

        id1 = crawler.generate_id("saramin", "12345")
        id2 = crawler.generate_id("saramin", "12346")
        id3 = crawler.generate_id("inthiswork", "12345")

        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """컨텍스트 매니저 테스트"""
        async with SaraminCrawler() as crawler:
            assert crawler._http_client is not None
            assert crawler._owns_client is True

        # 컨텍스트 종료 후 클라이언트가 정리되어야 함
        assert crawler._http_client is None
