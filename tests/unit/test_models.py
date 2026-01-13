"""
데이터 모델 단위 테스트
"""
import pytest
from datetime import datetime, timedelta

from src.models import ExperienceLevel, JobPosting, JobSource, JobSummary


class TestJobPosting:
    """JobPosting 모델 테스트"""

    def test_create_job_posting_minimal(self):
        """최소 필수 필드로 생성"""
        job = JobPosting(
            title="데이터 분석가",
            company_name="테스트 회사",
            experience_level=ExperienceLevel.ENTRY,
            source=JobSource.SARAMIN,
            source_url="https://example.com/job/1",
        )

        assert job.title == "데이터 분석가"
        assert job.company_name == "테스트 회사"
        assert job.experience_level == ExperienceLevel.ENTRY
        assert job.source == JobSource.SARAMIN
        assert job.source_url == "https://example.com/job/1"
        assert job.is_new is True
        assert job.is_active is True

    def test_create_job_posting_full(self):
        """모든 필드로 생성"""
        deadline = datetime.now() + timedelta(days=7)
        crawled_at = datetime.now()

        job = JobPosting(
            id="test123",
            title="데이터 분석가",
            company_name="테스트 회사",
            company_logo="https://example.com/logo.png",
            experience_level=ExperienceLevel.ENTRY,
            experience_text="신입 가능",
            deadline=deadline,
            deadline_text="D-7",
            internship_period="3개월",
            location="서울",
            salary="3,500만원 이상",
            employment_type="정규직",
            requirements=["Python", "SQL"],
            preferred=["Tableau", "AWS"],
            tech_stack=["Python", "Pandas", "SQL"],
            description="데이터 분석 업무",
            source=JobSource.SARAMIN,
            source_url="https://example.com/job/1",
            source_id="1",
            crawled_at=crawled_at,
            is_active=True,
            is_new=True,
        )

        assert job.id == "test123"
        assert job.company_logo == "https://example.com/logo.png"
        assert job.deadline == deadline
        assert job.location == "서울"
        assert job.requirements == ["Python", "SQL"]
        assert job.tech_stack == ["Python", "Pandas", "SQL"]

    def test_experience_level_enum_values(self):
        """ExperienceLevel enum 값 테스트"""
        assert ExperienceLevel.INTERN.value == "인턴"
        assert ExperienceLevel.ENTRY.value == "신입"
        assert ExperienceLevel.ANY.value == "경력무관"
        assert ExperienceLevel.JUNIOR.value == "주니어"
        assert ExperienceLevel.EXPERIENCED.value == "경력"

    def test_job_source_enum_values(self):
        """JobSource enum 값 테스트"""
        assert JobSource.SARAMIN.value == "saramin"
        assert JobSource.INTHISWORK.value == "inthiswork"

    def test_default_values(self):
        """기본값 테스트"""
        job = JobPosting(
            title="테스트",
            company_name="회사",
            experience_level=ExperienceLevel.ENTRY,
            source=JobSource.SARAMIN,
            source_url="https://example.com",
        )

        assert job.requirements == []
        assert job.preferred == []
        assert job.tech_stack == []
        assert job.is_active is True
        assert job.is_new is True
        assert job.crawled_at is not None


class TestJobSummary:
    """JobSummary 모델 테스트"""

    def test_create_job_summary(self):
        """JobSummary 생성"""
        summary = JobSummary(
            id="test1",
            title="데이터 분석가",
            company_name="테스트 회사",
            experience_text="신입",
            deadline_text="D-7",
            location="서울",
            source="saramin",
            source_url="https://example.com",
            crawled_at=datetime.now(),
            is_new=True,
            days_until_deadline=7,
        )

        assert summary.id == "test1"
        assert summary.days_until_deadline == 7

    def test_job_summary_optional_fields(self):
        """옵션 필드 테스트"""
        summary = JobSummary(
            id="test1",
            title="테스트",
            company_name="회사",
            source="saramin",
            source_url="https://example.com",
            crawled_at=datetime.now(),
        )

        assert summary.company_logo is None
        assert summary.experience_text is None
        assert summary.deadline_text is None
        assert summary.location is None
        assert summary.days_until_deadline is None
