"""
JobFilter 단위 테스트
"""
import pytest
from datetime import datetime, timedelta

from src.core.config import FilterConfig
from src.models import ExperienceLevel, JobPosting, JobSource
from src.services.job_filter import JobFilter


class TestJobFilter:
    """JobFilter 테스트"""

    @pytest.fixture
    def filter(self) -> JobFilter:
        """기본 필터 인스턴스"""
        return JobFilter()

    @pytest.fixture
    def custom_filter(self) -> JobFilter:
        """커스텀 필터 인스턴스"""
        config = FilterConfig(
            job_keywords=["백엔드", "Backend"],
            exclude_keywords=["시니어"],
            entry_level_keywords=["신입", "경력무관"],
        )
        return JobFilter(config)

    def _create_job(
        self,
        title: str = "데이터 분석가",
        experience_text: str = "신입",
        description: str = None,
    ) -> JobPosting:
        """테스트용 JobPosting 생성"""
        return JobPosting(
            id="test1",
            title=title,
            company_name="테스트 회사",
            experience_level=ExperienceLevel.ENTRY,
            experience_text=experience_text,
            deadline=datetime.now() + timedelta(days=7),
            deadline_text="D-7",
            location="서울",
            source=JobSource.SARAMIN,
            source_url="https://example.com/job/1",
            source_id="1",
            crawled_at=datetime.now(),
            description=description,
        )

    # === 기본 매칭 테스트 ===

    def test_matches_with_job_keyword_in_title(self, filter: JobFilter):
        """타이틀에 직무 키워드가 있으면 매칭"""
        job = self._create_job(title="데이터 분석가 신입")
        assert filter.matches(job) is True

    def test_matches_with_job_keyword_in_description(self, filter: JobFilter):
        """설명에 직무 키워드가 있으면 매칭"""
        job = self._create_job(
            title="분석 전문가",
            description="데이터 분석 업무를 담당합니다",
        )
        assert filter.matches(job) is True

    def test_not_matches_without_job_keyword(self, filter: JobFilter):
        """직무 키워드가 없으면 매칭 안 됨"""
        job = self._create_job(title="백엔드 개발자")
        assert filter.matches(job) is False

    # === 제외 키워드 테스트 ===

    def test_excludes_senior_in_title(self, filter: JobFilter):
        """타이틀에 '시니어'가 있으면 제외"""
        job = self._create_job(title="시니어 데이터 분석가")
        assert filter.matches(job) is False

    def test_excludes_lead_in_title(self, filter: JobFilter):
        """타이틀에 'Lead'가 있으면 제외"""
        job = self._create_job(title="Data Analyst Lead")
        assert filter.matches(job) is False

    def test_excludes_team_leader(self, filter: JobFilter):
        """타이틀에 '팀장'이 있으면 제외"""
        job = self._create_job(title="데이터 분석 팀장")
        assert filter.matches(job) is False

    # === 경력 조건 테스트 ===

    def test_entry_level_keywords(self, filter: JobFilter):
        """신입 키워드가 있으면 포함"""
        test_cases = [
            "신입",
            "경력무관",
            "경력 무관",
            "인턴",
            "신입/경력",
        ]
        for exp_text in test_cases:
            job = self._create_job(experience_text=exp_text)
            assert filter.matches(job) is True, f"'{exp_text}' should match"

    def test_excludes_experienced_only(self, filter: JobFilter):
        """경력만 요구하면 제외"""
        test_cases = [
            "경력 3년 이상",
            "경력3년↑",
            "1~3년",
            "2-5년",
            "3년 이상",
        ]
        for exp_text in test_cases:
            job = self._create_job(experience_text=exp_text)
            assert filter.matches(job) is False, f"'{exp_text}' should not match"

    def test_excludes_career_only(self, filter: JobFilter):
        """'경력'만 있고 신입 키워드 없으면 제외"""
        job = self._create_job(experience_text="경력")
        assert filter.matches(job) is False

    def test_includes_no_experience_requirement(self, filter: JobFilter):
        """경력 조건이 없으면 포함"""
        job = self._create_job(experience_text=None)
        assert filter.matches(job) is True

    # === 커스텀 필터 테스트 ===

    def test_custom_job_keywords(self, custom_filter: JobFilter):
        """커스텀 직무 키워드 매칭"""
        job = self._create_job(title="백엔드 개발자")
        assert custom_filter.matches(job) is True

        job2 = self._create_job(title="데이터 분석가")
        assert custom_filter.matches(job2) is False

    # === filter_jobs 테스트 ===

    def test_filter_jobs_list(self, filter: JobFilter, sample_jobs):
        """채용 공고 리스트 필터링"""
        filtered = filter.filter_jobs(sample_jobs)

        # 시니어/경력 공고는 제외되어야 함
        titles = [job.title for job in filtered]
        assert "데이터 분석가" in titles
        assert "데이터 사이언티스트" in titles

    def test_filter_jobs_empty_list(self, filter: JobFilter):
        """빈 리스트 필터링"""
        filtered = filter.filter_jobs([])
        assert filtered == []


class TestExperienceLevelParsing:
    """경력 조건 파싱 테스트"""

    @pytest.fixture
    def filter(self) -> JobFilter:
        return JobFilter()

    @pytest.mark.parametrize(
        "exp_text,expected",
        [
            # 신입 가능
            ("신입", True),
            ("경력무관", True),
            ("경력 무관", True),
            ("인턴", True),
            ("신입/경력", True),
            ("Junior", True),
            ("Entry Level", True),
            # 빈 값
            ("", True),
            (None, True),
            # 경력 요구
            ("경력 1년", False),
            ("경력1년", False),
            ("경력 2년↑", False),
            ("1년 이상", False),
            ("2년 이상", False),
            ("1~3년", False),
            ("2-5년", False),
            ("경력 1~3", False),
            ("경력", False),
        ],
    )
    def test_is_entry_level_friendly(
        self, filter: JobFilter, exp_text: str, expected: bool
    ):
        """경력 조건 파싱 테스트"""
        result = filter._is_entry_level_friendly(exp_text)
        assert result is expected, f"'{exp_text}' should be {expected}"
