"""
pytest fixtures

테스트에서 공통으로 사용하는 fixture를 정의합니다.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from src.core.config import FilterConfig, reset_config
from src.core.container import Container
from src.core.interfaces import HttpClientProtocol
from src.models import ExperienceLevel, JobPosting, JobSource


# === Fixtures 디렉토리 ===

@pytest.fixture
def fixtures_dir() -> Path:
    """테스트 fixture 디렉토리 경로"""
    return Path(__file__).parent / "fixtures"


# === Mock HTTP Client ===

class MockHttpClient(HttpClientProtocol):
    """테스트용 Mock HTTP 클라이언트

    미리 정의된 응답을 반환합니다.
    """

    def __init__(self):
        self.responses: Dict[str, str] = {}
        self.json_responses: Dict[str, Dict] = {}
        self.request_history: List[str] = []

    def set_response(self, url: str, html: str) -> None:
        """URL에 대한 HTML 응답 설정"""
        self.responses[url] = html

    def set_json_response(self, url: str, data: Dict) -> None:
        """URL에 대한 JSON 응답 설정"""
        self.json_responses[url] = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get(self, url: str, **kwargs) -> Optional[str]:
        """Mock GET 요청"""
        self.request_history.append(("GET", url))
        return self.responses.get(url)

    async def get_json(self, url: str, **kwargs) -> Optional[Dict]:
        """Mock GET JSON 요청"""
        self.request_history.append(("GET_JSON", url))
        return self.json_responses.get(url)

    async def post(self, url: str, data: Dict, **kwargs) -> Optional[Dict]:
        """Mock POST 요청"""
        self.request_history.append(("POST", url, data))
        return self.json_responses.get(url)


@pytest.fixture
def mock_http_client() -> MockHttpClient:
    """Mock HTTP 클라이언트 fixture"""
    return MockHttpClient()


# === Sample Data ===

@pytest.fixture
def sample_job() -> JobPosting:
    """샘플 채용 공고"""
    return JobPosting(
        id="test123",
        title="데이터 분석가 (신입/경력)",
        company_name="테스트 회사",
        company_logo=None,
        experience_level=ExperienceLevel.ENTRY,
        experience_text="신입 가능",
        deadline=datetime.now() + timedelta(days=7),
        deadline_text="D-7",
        location="서울",
        source=JobSource.SARAMIN,
        source_url="https://example.com/job/123",
        source_id="123",
        crawled_at=datetime.now(),
        is_new=True,
    )


@pytest.fixture
def sample_jobs() -> List[JobPosting]:
    """샘플 채용 공고 리스트"""
    now = datetime.now()
    return [
        JobPosting(
            id="job1",
            title="데이터 분석가",
            company_name="회사A",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입",
            deadline=now + timedelta(days=3),
            deadline_text="D-3",
            location="서울",
            source=JobSource.SARAMIN,
            source_url="https://saramin.co.kr/job/1",
            source_id="1",
            crawled_at=now,
            is_new=True,
        ),
        JobPosting(
            id="job2",
            title="데이터 사이언티스트",
            company_name="회사B",
            experience_level=ExperienceLevel.ANY,
            experience_text="경력무관",
            deadline=now + timedelta(days=14),
            deadline_text="D-14",
            location="판교",
            source=JobSource.SARAMIN,
            source_url="https://saramin.co.kr/job/2",
            source_id="2",
            crawled_at=now,
            is_new=False,
        ),
        JobPosting(
            id="job3",
            title="ML 엔지니어",
            company_name="회사C",
            experience_level=ExperienceLevel.EXPERIENCED,
            experience_text="경력 3년 이상",
            deadline=now + timedelta(days=5),
            deadline_text="D-5",
            location="서울",
            source=JobSource.INTHISWORK,
            source_url="https://inthiswork.com/job/3",
            source_id="3",
            crawled_at=now,
            is_new=True,
        ),
    ]


@pytest.fixture
def senior_job() -> JobPosting:
    """시니어 포지션 채용 공고 (필터링 되어야 함)"""
    return JobPosting(
        id="senior1",
        title="시니어 데이터 분석가",
        company_name="시니어 회사",
        experience_level=ExperienceLevel.EXPERIENCED,
        experience_text="경력 5년 이상",
        deadline=datetime.now() + timedelta(days=10),
        deadline_text="D-10",
        location="서울",
        source=JobSource.SARAMIN,
        source_url="https://example.com/job/senior",
        source_id="senior1",
        crawled_at=datetime.now(),
        is_new=True,
    )


# === Filter Config ===

@pytest.fixture
def default_filter_config() -> FilterConfig:
    """기본 필터 설정"""
    return FilterConfig()


@pytest.fixture
def custom_filter_config() -> FilterConfig:
    """커스텀 필터 설정"""
    return FilterConfig(
        job_keywords=["백엔드", "Backend", "서버 개발"],
        exclude_keywords=["시니어", "팀장"],
        entry_level_keywords=["신입", "경력무관"],
    )


# === Container ===

@pytest.fixture(autouse=True)
def reset_container():
    """각 테스트 전후로 컨테이너 리셋"""
    yield
    Container.reset_instance()
    reset_config()


# === HTML Fixtures ===

@pytest.fixture
def saramin_html() -> str:
    """사람인 검색 결과 페이지 샘플 HTML"""
    return '''
    <html>
    <body>
        <div class="item_recruit">
            <div class="corp_name">
                <a href="/company/123">테스트 회사</a>
            </div>
            <div class="job_tit">
                <a href="/job/456?rec_idx=789">데이터 분석가 (신입)</a>
            </div>
            <div class="job_condition">
                <span>서울</span>
                <span>신입</span>
            </div>
            <div class="job_date">
                <span class="date">D-7</span>
            </div>
        </div>
        <div class="item_recruit">
            <div class="corp_name">
                <a href="/company/124">다른 회사</a>
            </div>
            <div class="job_tit">
                <a href="/job/457?rec_idx=790">시니어 데이터 엔지니어</a>
            </div>
            <div class="job_condition">
                <span>판교</span>
                <span>경력 5년 이상</span>
            </div>
            <div class="job_date">
                <span class="date">D-14</span>
            </div>
        </div>
    </body>
    </html>
    '''


# === Temporary Files ===

@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """임시 데이터 디렉토리"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def tmp_docs_dir(tmp_path: Path) -> Path:
    """임시 문서 디렉토리"""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    return docs_dir


@pytest.fixture
def existing_jobs_json(tmp_data_dir: Path) -> Path:
    """기존 jobs.json 파일"""
    jobs_file = tmp_data_dir / "jobs.json"
    data = {
        "updated_at": datetime.now().isoformat(),
        "stats": {"total": 1, "new": 1, "expiring_7days": 0, "by_source": {}},
        "jobs": [
            {
                "id": "existing1",
                "title": "기존 공고",
                "company_name": "기존 회사",
                "first_seen_at": (datetime.now() - timedelta(hours=24)).isoformat(),
                "is_new": True,
                "source": "saramin",
                "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
            }
        ],
    }
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return jobs_file
