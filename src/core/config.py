"""
애플리케이션 설정 관리

환경변수 기반 설정과 기본값을 통합 관리합니다.
"""
import os
from pathlib import Path
from typing import List, Optional, Dict

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# =============================================================================
# 직군별 키워드 설정 (스코어 기반 매칭용)
# =============================================================================
# must_have: 필수 키워드 (하나 이상 매칭 필요) - +10점
# good_to_have: 보조 키워드 - +3점
# exclude: 제외 키워드 - 즉시 제외

JOB_CATEGORY_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    # =========================================================================
    # 데이터 직군
    # =========================================================================
    "data": {
        "must_have": [
            # 직무명
            "데이터 분석", "데이터분석", "데이터 분석가", "Data Analyst",
            "데이터 사이언티스트", "Data Scientist", "데이터 사이언스",
            "BI 분석", "BI 분석가", "비즈니스 분석", "비즈니스 인텔리전스",
            "데이터 엔지니어", "Data Engineer", "데이터엔지니어",
            "머신러닝 엔지니어", "ML Engineer", "MLOps",
            "AI 엔지니어", "인공지능", "딥러닝",
            # 신입 특화
            "데이터 신입", "분석가 신입", "주니어 데이터",
        ],
        "good_to_have": [
            # 기술 스택
            "SQL", "Python", "R", "SAS", "SPSS",
            "Tableau", "Power BI", "Looker", "Redash", "Metabase",
            "BigQuery", "Snowflake", "Redshift", "Databricks",
            "Spark", "Hadoop", "Airflow", "Kafka",
            "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch",
            # 역량
            "통계", "분석", "시각화", "대시보드", "리포팅",
            "ETL", "데이터 파이프라인", "데이터 웨어하우스",
            "A/B 테스트", "지표 분석", "코호트 분석",
        ],
        "exclude": [
            "데이터 입력", "데이터입력", "단순 입력", "자료 입력", "타이핑",
            "데이터 관리", "데이터관리", "문서 관리", "자료 관리",
            "데이터 라벨링", "라벨링", "어노테이션", "태깅 작업",
            "데이터 센터", "IDC", "서버실",
        ],
    },
    # =========================================================================
    # 백엔드 직군
    # =========================================================================
    "backend": {
        "must_have": [
            # 직무명
            "백엔드", "Backend", "Back-end", "백엔드 개발자",
            "서버 개발", "서버개발", "서버 개발자", "Server Developer",
            "API 개발", "API 개발자", "웹 서버 개발",
            # 언어/프레임워크 특화
            "Java 개발", "자바 개발", "자바 개발자",
            "Spring 개발", "스프링 개발", "Spring Boot",
            "Python 개발", "파이썬 개발", "Django 개발", "FastAPI",
            "Node.js 개발", "노드 개발", "Express",
            "Go 개발", "Golang", "Kotlin 개발",
            # 신입 특화
            "백엔드 신입", "서버 신입", "주니어 백엔드",
        ],
        "good_to_have": [
            # 언어
            "Java", "Python", "Node.js", "Go", "Kotlin", "C#", "PHP", "Ruby",
            # 프레임워크
            "Spring", "Spring Boot", "JPA", "MyBatis", "Hibernate",
            "Django", "FastAPI", "Flask",
            "Express", "NestJS", "Koa",
            # DB
            "MySQL", "PostgreSQL", "MariaDB", "Oracle",
            "MongoDB", "Redis", "Elasticsearch", "Cassandra",
            # 인프라
            "Docker", "Kubernetes", "AWS", "GCP", "Azure",
            "CI/CD", "Jenkins", "GitHub Actions",
            # 아키텍처
            "REST API", "GraphQL", "gRPC",
            "MSA", "마이크로서비스", "모놀리식",
            "메시지 큐", "RabbitMQ", "Kafka",
        ],
        "exclude": [
            "서버 관리", "서버관리", "서버 운영", "시스템 운영",
            "IDC", "인프라 관리", "인프라 운영",
            "시스템 관리", "시스템관리", "운영 관리",
            "네트워크 관리", "네트워크관리", "네트워크 엔지니어",
            "DBA", "데이터베이스 관리자",
        ],
    },
    # =========================================================================
    # 프론트엔드 직군
    # =========================================================================
    "frontend": {
        "must_have": [
            # 직무명
            "프론트엔드", "Frontend", "Front-end", "프론트엔드 개발자",
            "웹 개발", "웹개발", "웹 개발자", "Web Developer",
            "웹 프론트", "웹 프론트엔드",
            "UI 개발", "UI 개발자",
            # 프레임워크 특화
            "React 개발", "리액트 개발", "React 개발자",
            "Vue 개발", "뷰 개발", "Vue.js 개발자",
            "Angular 개발", "앵귤러 개발",
            # 퍼블리셔
            "퍼블리셔", "웹 퍼블리셔", "마크업 개발", "HTML 개발",
            # 신입 특화
            "프론트엔드 신입", "웹 개발 신입", "주니어 프론트",
        ],
        "good_to_have": [
            # 언어
            "JavaScript", "TypeScript", "ES6", "ES2015+",
            # 프레임워크/라이브러리
            "React", "Vue.js", "Angular", "Svelte",
            "Next.js", "Nuxt.js", "Gatsby",
            # 상태관리
            "Redux", "MobX", "Recoil", "Zustand", "Jotai",
            "Vuex", "Pinia",
            # 스타일링
            "HTML", "CSS", "SCSS", "Sass", "Less",
            "Tailwind", "styled-components", "Emotion",
            # 빌드 도구
            "Webpack", "Vite", "Babel", "ESLint", "Prettier",
            # 기타
            "반응형", "크로스브라우징", "웹 접근성", "SEO",
            "PWA", "SPA", "SSR", "CSR",
        ],
        "exclude": [
            "웹 디자인", "웹디자인", "그래픽 디자인", "시각 디자인",
            "UI 디자인", "UX 디자인", "UI/UX 디자이너", "디자이너",
            "웹 에이전시", "홈페이지 제작",
        ],
    },
    # =========================================================================
    # PM/기획 직군
    # =========================================================================
    "pm": {
        "must_have": [
            # 직무명
            "서비스 기획", "서비스기획", "서비스 기획자",
            "IT 기획", "IT기획", "IT 기획자", "웹 기획",
            "프로덕트 매니저", "Product Manager", "프로덕트매니저",
            "PM", "프로젝트 매니저", "Project Manager",
            "프로덕트 오너", "Product Owner", "프로덕트오너", "PO",
            "앱 기획", "플랫폼 기획", "콘텐츠 기획",
            # 신입 특화
            "기획자 신입", "PM 신입", "주니어 기획",
        ],
        "good_to_have": [
            # 도구
            "Jira", "Confluence", "Notion", "Asana", "Monday",
            "Figma", "Sketch", "Zeplin", "Miro",
            # 방법론
            "애자일", "Agile", "스크럼", "Scrum", "칸반", "Kanban",
            "린", "Lean", "스프린트", "Sprint",
            # 역량
            "사용자 조사", "유저 리서치", "고객 인터뷰",
            "A/B 테스트", "데이터 분석", "지표 분석",
            "PRD", "기획서", "요구사항 정의", "스펙 문서",
            "와이어프레임", "프로토타입", "스토리보드",
            "UX", "사용자 경험", "고객 여정", "퍼널 분석",
        ],
        "exclude": [
            "PM/AM", "오전/오후", "교대 근무", "교대",
            "생산관리", "공정관리", "제조 기획", "생산 기획",
            "품질관리", "QC", "QA 관리", "품질 기획",
            "물류 기획", "SCM 기획",
        ],
    },
    # =========================================================================
    # 영업 직군
    # =========================================================================
    "sales": {
        "must_have": [
            # 직무명
            "영업", "영업 담당", "영업담당자", "영업대표",
            "세일즈", "Sales", "Sales Representative",
            "Account Manager", "AM", "Account Executive", "AE",
            # B2B/B2C
            "B2B 영업", "B2C 영업", "기업영업", "법인영업",
            "솔루션 영업", "IT 영업", "기술영업", "Tech Sales",
            "SaaS 영업", "소프트웨어 영업", "클라우드 영업",
            # 신입 특화
            "영업 신입", "세일즈 신입", "주니어 영업",
        ],
        "good_to_have": [
            # 도구
            "CRM", "Salesforce", "HubSpot", "Pipedrive",
            # 역량
            "제안서", "PT", "프레젠테이션", "데모",
            "고객관리", "거래처 관리", "리드 관리",
            "파트너십", "채널 영업", "총판",
            "매출", "실적", "목표 달성", "KPI",
            "계약", "협상", "클로징", "딜 클로징",
            "신규 개척", "아웃바운드", "콜드콜",
        ],
        "exclude": [
            "영업지원", "영업 지원", "세일즈 지원",
            "영업관리자", "영업 관리", "매장 관리",
            "영업 사무", "영업사무", "내근 영업", "내근직",
            "고객센터", "CS", "상담", "콜센터", "컨택센터",
            "텔레마케팅", "TM", "인바운드 상담",
            "매장 영업", "점포 영업", "현장 영업",
        ],
    },
    # =========================================================================
    # 구매/CRM 직군 (신규)
    # =========================================================================
    "procurement": {
        "must_have": [
            # 구매 직무
            "구매", "구매 담당", "구매담당자", "구매팀",
            "바이어", "Buyer", "Purchasing", "Procurement",
            "조달", "조달 담당", "소싱", "Sourcing",
            "자재", "자재 관리", "자재담당", "원자재 구매",
            "외주 관리", "협력사 관리", "벤더 관리",
            # SCM 관련
            "SCM", "Supply Chain", "공급망 관리",
            # CRM 직무
            "CRM", "CRM 담당", "CRM 마케팅", "CRM 기획",
            "고객관계관리", "Customer Relationship",
            "리텐션", "Retention", "고객 유지",
            "고객 분석", "고객 세그먼트", "고객 데이터",
            # 신입 특화
            "구매 신입", "CRM 신입", "조달 신입",
        ],
        "good_to_have": [
            # 구매 관련
            "ERP", "SAP", "Oracle", "발주", "입고", "검수",
            "원가 분석", "원가 절감", "비용 절감",
            "계약", "협상", "네고", "단가",
            "품질 관리", "QC", "입고 검사",
            # CRM 관련
            "Salesforce", "HubSpot", "Braze", "Amplitude",
            "마케팅 자동화", "Marketing Automation",
            "이메일 마케팅", "푸시 알림", "카카오톡",
            "고객 여정", "Customer Journey", "퍼널",
            "세그멘테이션", "타겟팅", "개인화",
            "LTV", "Churn", "이탈 방지",
            # 분석
            "데이터 분석", "SQL", "Excel", "엑셀",
        ],
        "exclude": [
            "구매대행", "해외구매", "직구",
            "매장 관리", "점포 관리", "재고 관리 알바",
            "콜센터", "CS", "고객센터", "상담사",
            "텔레마케터", "TM",
        ],
    },
}

# 스코어 설정
SCORE_CONFIG = {
    "must_have_score": 10,      # 필수 키워드 매칭 시 점수
    "good_to_have_score": 3,    # 보조 키워드 매칭 시 점수
    "threshold": 10,            # 통과 기준 점수
}


class FilterConfig(BaseModel):
    """필터링 설정"""

    job_keywords: List[str] = Field(
        default=[
            # 데이터 분석
            "데이터 분석", "데이터분석", "Data Analyst", "Data Analysis",
            "데이터 사이언티스트", "Data Scientist", "BI 분석", "비즈니스 분석",
            "데이터 엔지니어", "Data Engineer", "머신러닝", "ML Engineer",
            # 백엔드 개발
            "백엔드", "Backend", "서버 개발", "Server Developer",
            "Java 개발", "Spring", "Python 개발", "Node.js",
            # 프론트엔드 개발
            "프론트엔드", "Frontend", "React", "Vue", "웹 개발", "퍼블리셔",
            # PM/기획
            "서비스 기획", "PM", "프로덕트 매니저", "Product Manager",
            "IT 기획", "프로덕트 오너", "PO",
            # 영업
            "영업", "세일즈", "Sales", "Account Manager",
            "B2B 영업", "B2C 영업", "솔루션 영업", "IT 영업", "기술영업",
            # 구매/CRM
            "구매", "바이어", "Buyer", "Procurement", "조달", "소싱",
            "CRM", "고객관계관리", "리텐션", "Retention",
        ],
        description="포함할 직무 키워드 (OR 조건) - 사람인 검색용",
    )

    exclude_keywords: List[str] = Field(
        default=[
            # 경력직 키워드 (Manager/매니저는 Account Manager, PM 등 유효한 포지션 포함하므로 제외하지 않음)
            "시니어", "Senior", "Sr.", "선임",
            "팀장", "리드", "Lead", "Tech Lead",
            "Principal", "Staff", "Head", "Chief",
            "책임", "파트장", "그룹장",
            # 경력 연차
            "5년 이상", "7년 이상", "10년 이상",
            "5년이상", "7년이상", "10년이상",
            # 단순 업무
            "데이터 입력", "데이터입력", "단순 입력", "자료 입력",
            "문서 정리", "문서정리", "서류 정리",
        ],
        description="제외할 키워드",
    )

    entry_level_keywords: List[str] = Field(
        default=[
            "신입",
            "경력무관",
            "경력 무관",
            "인턴",
            "intern",
            "entry",
            "junior",
            "신입/경력",
            "경력/신입",
        ],
        description="신입 가능 키워드",
    )


class CrawlerConfig(BaseModel):
    """크롤러 설정"""

    request_delay_seconds: float = Field(
        default=2.0,
        description="요청 간 대기 시간 (초)",
    )

    request_timeout: int = Field(
        default=30,
        description="요청 타임아웃 (초)",
    )

    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        description="User-Agent 헤더",
    )

    max_detail_fetch: int = Field(
        default=5,
        description="상세 정보를 가져올 최대 공고 수",
    )


class ExporterConfig(BaseModel):
    """내보내기 설정"""

    new_threshold_hours: int = Field(
        default=48,
        description="새 공고 판정 시간 (시간)",
    )


class ApiConfig(BaseModel):
    """외부 API 설정"""

    perplexity_api_key: Optional[str] = Field(
        default=None,
        description="Perplexity API 키",
    )

    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API 키",
    )

    google_cse_id: Optional[str] = Field(
        default=None,
        description="Google Custom Search Engine ID",
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API 키 (임베딩용)",
    )


class AppConfig(BaseSettings):
    """애플리케이션 전체 설정

    환경변수에서 값을 읽어옵니다:
    - PERPLEXITY_API_KEY
    - GOOGLE_API_KEY
    - GOOGLE_CSE_ID
    - OPENAI_API_KEY
    - GROQ_API_KEY
    """

    # 서브 설정
    filter: FilterConfig = Field(default_factory=FilterConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    exporter: ExporterConfig = Field(default_factory=ExporterConfig)

    # API 키 (환경변수에서 로드)
    perplexity_api_key: Optional[str] = Field(default=None, alias="PERPLEXITY_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_cse_id: Optional[str] = Field(default=None, alias="GOOGLE_CSE_ID")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq 모델 ID")
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")

    # 경로 설정
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    @property
    def data_dir(self) -> Path:
        """데이터 디렉토리 경로"""
        return self.base_dir / "data"

    @property
    def docs_dir(self) -> Path:
        """문서 디렉토리 경로 (GitHub Pages)"""
        return self.base_dir / "docs"

    @property
    def jobs_json_path(self) -> Path:
        """jobs.json 경로"""
        return self.data_dir / "jobs.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 싱글톤 인스턴스
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """설정 인스턴스 반환 (싱글톤)"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    """설정 인스턴스 리셋 (테스트용)"""
    global _config
    _config = None
