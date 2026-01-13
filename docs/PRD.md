# PRD: Recruitment Auto v2.0

> 채용 정보 자동 수집 및 프로필 매칭 플랫폼

**문서 버전**: 2.1
**최종 수정일**: 2026-01-12
**상태**: Phase 5 완료

---

## 1. 제품 개요

### 1.1 배경 및 목적

기존 Recruitment Auto는 데이터 분석 직무의 채용 공고를 사람인/인디스워크에서 자동 수집하여 GitHub Pages로 제공하는 서비스였습니다.

v2.0에서는 다음을 목표로 확장합니다:

1. **다양한 데이터 소스** - Perplexity API, Google Search API 등을 통한 수집 채널 다각화
2. **직무 다양화** - 데이터 분석 외 백엔드, 프론트엔드, 기획 등 추가
3. **프로필 매칭** - GitHub Issue로 등록된 사용자 프로필과 채용 공고 매칭
4. **갭 분석** - 프로필 vs 채용 요건 비교를 통한 커리어 전략 제시
5. **알림 시스템** - 이메일 뉴스레터 및 GitHub Issue 코멘트 알림

### 1.2 타겟 사용자

| 사용자 유형 | 설명 |
|-------------|------|
| 취업준비생 | 신입/주니어 포지션을 찾는 구직자 |
| 재학생 | 인턴십/취업 준비 중인 대학생 |
| 이직 준비자 | 새로운 기회를 찾는 현직자 |

### 1.3 핵심 가치

- **자동화**: 매일 자동으로 채용 정보 수집
- **무료**: GitHub Actions + Pages로 서버 비용 없음
- **개인화**: 프로필 기반 맞춤 공고 추천
- **인사이트**: 역량 갭 분석 및 커리어 전략 제시

---

## 2. 기능 명세

### Phase 1: 데이터 소스 확장

#### 2.1 Perplexity API 연동

**목적**: AI 기반 검색으로 다양한 채용 사이트에서 정보 통합 수집

**기능**:
- Perplexity Sonar API를 통한 채용 정보 검색
- 자연어 쿼리로 여러 사이트의 채용 정보 수집
- 구조화된 JSON 응답으로 파싱

**API 엔드포인트**: `POST https://api.perplexity.ai/chat/completions`

**환경변수**: `PERPLEXITY_API_KEY`

**검색 쿼리 예시**:
```
"데이터 분석가 신입 채용 공고 2026년 1월"
"주니어 백엔드 개발자 채용 서울"
```

#### 2.2 Google Custom Search API 연동

**목적**: Google 검색을 통한 추가 채용 정보 수집

**기능**:
- Programmable Search Engine으로 채용 사이트 검색
- site: 연산자로 특정 사이트 타겟팅
- 최신 공고 우선 정렬

**환경변수**:
- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID` (Custom Search Engine ID)

**타겟 사이트**:
- wanted.co.kr
- jobkorea.co.kr
- programmers.co.kr
- linkedin.com/jobs

#### 2.3 데이터 소스 추상화

새로운 데이터 소스를 쉽게 추가할 수 있도록 인터페이스 정의:

```python
class DataSource(Protocol):
    """데이터 소스 인터페이스"""

    async def search(self, query: SearchQuery) -> List[JobPosting]:
        """채용 공고 검색"""
        ...

    @property
    def source_name(self) -> str:
        """소스 이름"""
        ...
```

---

### Phase 2: 채용 공고 상세화

#### 2.4 자격 요건 추출 강화

**현재 상태**: `requirements` 필드 존재하나 활용 미흡

**개선 방안**:
- LLM을 활용한 자격 요건 구조화 파싱
- 필수 요건 / 우대 사항 분리
- 기술 스택 자동 태깅

**데이터 구조**:
```python
class JobRequirements(BaseModel):
    education: Optional[str]           # 학력 요건
    experience_years: Optional[int]    # 경력 연수
    required_skills: List[str]         # 필수 기술
    preferred_skills: List[str]        # 우대 기술
    certifications: List[str]          # 자격증
    language: List[str]                # 언어 요건
```

---

### Phase 3: 알림 시스템

#### 2.5 이메일 뉴스레터

**목적**: 매일 오전 새 공고 요약 발송

**기능**:
- 구독자 관리 (GitHub Issue로 등록)
- 일간 요약 이메일 생성
- 개인화된 공고 추천 포함

**발송 시간**: 매일 09:00 KST

**이메일 구성**:
```
[오늘의 채용 공고] 2026년 1월 12일

새 공고 15건이 등록되었습니다.

## 추천 공고 (내 프로필 기준)
1. [네이버] 데이터 분석가 - 매칭률 85%
2. [카카오] ML 엔지니어 - 매칭률 78%

## 전체 새 공고
...

## 마감 임박 (7일 이내)
...
```

**기술 선택지**:
- SendGrid API
- AWS SES
- GitHub Actions + nodemailer

---

### Phase 4: 프로필 매칭 시스템 (핵심 기능)

#### 2.6 직무 카테고리 확장

**현재**: 데이터 분석 전용

**확장 직무**:
| 카테고리 | 키워드 |
|----------|--------|
| 데이터 | 데이터 분석, Data Analyst, ML Engineer, 데이터 엔지니어 |
| 백엔드 | Backend, 서버 개발, Java, Python, Node.js |
| 프론트엔드 | Frontend, React, Vue, 웹 개발 |
| 풀스택 | Full Stack, 웹 개발자 |
| 기획 | PM, PO, 서비스 기획, 프로덕트 |
| 디자인 | UI/UX, 프로덕트 디자이너 |

#### 2.7 GitHub 프로필 등록 시스템

**Issue 템플릿**: `.github/ISSUE_TEMPLATE/profile.yml`

```yaml
name: 프로필 등록
description: 채용 공고 매칭을 위한 프로필을 등록합니다
title: "[프로필] {사용자명}"
labels: ["profile"]
body:
  - type: input
    id: github_username
    attributes:
      label: GitHub 사용자명
      placeholder: "예: johndoe"
    validations:
      required: true

  - type: dropdown
    id: job_category
    attributes:
      label: 희망 직무
      options:
        - 데이터 분석
        - 백엔드 개발
        - 프론트엔드 개발
        - 풀스택 개발
        - 기획/PM
        - 디자인
    validations:
      required: true

  - type: input
    id: experience_years
    attributes:
      label: 경력 (년)
      placeholder: "0 (신입), 1, 2..."

  - type: textarea
    id: skills
    attributes:
      label: 보유 기술
      placeholder: |
        - Python
        - SQL
        - Pandas
        - Tableau

  - type: textarea
    id: certifications
    attributes:
      label: 자격증
      placeholder: |
        - 정보처리기사
        - SQLD

  - type: input
    id: preferred_location
    attributes:
      label: 희망 근무지
      placeholder: "서울, 판교, 재택 등"

  - type: input
    id: email
    attributes:
      label: 이메일 (뉴스레터 수신용)
      placeholder: "your@email.com"
```

#### 2.8 프로필-공고 매칭 엔진

**매칭 알고리즘**:

1. **규칙 기반 매칭** (1차 필터)
   - 직무 카테고리 일치
   - 경력 조건 부합
   - 위치 조건 부합

2. **임베딩 기반 매칭** (2차 점수화)
   - 프로필 텍스트 → 임베딩 벡터
   - 채용 공고 텍스트 → 임베딩 벡터
   - 코사인 유사도 계산

**임베딩 모델 선택지**:
- OpenAI `text-embedding-3-small` (유료, 고성능)
- `sentence-transformers/all-MiniLM-L6-v2` (무료, 오픈소스)
- `intfloat/multilingual-e5-small` (무료, 한국어 지원)

**매칭 점수 산출**:
```python
def calculate_match_score(profile: Profile, job: JobPosting) -> float:
    # 기본 점수 (규칙 기반)
    base_score = 0.0

    # 직무 카테고리 일치: +30점
    if profile.job_category == job.category:
        base_score += 30

    # 경력 조건 부합: +20점
    if job.min_experience <= profile.experience_years:
        base_score += 20

    # 임베딩 유사도: 0~50점
    embedding_score = cosine_similarity(
        profile.embedding,
        job.embedding
    ) * 50

    return base_score + embedding_score
```

#### 2.9 매칭 결과 알림

**GitHub Issue 코멘트**:

프로필 Issue에 매칭된 공고를 코멘트로 추가:

```markdown
## 새로운 매칭 공고 (2026-01-12)

총 3건의 새 공고가 프로필과 매칭되었습니다.

| 회사 | 포지션 | 매칭률 | 마감 |
|------|--------|--------|------|
| [네이버](link) | 데이터 분석가 | 85% | D-7 |
| [카카오](link) | ML 엔지니어 | 78% | D-14 |
| [라인](link) | 주니어 데이터 분석가 | 72% | 상시 |

---
*자동 생성됨 by Recruitment Auto*
```

---

### Phase 5: 갭 분석 및 커리어 전략 ✅ 구현 완료

> **구현 완료일**: 2026-01-12
> **LLM**: Groq API (Llama 3.3 70B Versatile) - 무료, 빠른 응답

#### 2.10 역량 갭 분석

**목적**: 프로필 vs 채용 요건 비교를 통한 부족한 역량 도출

**구현된 기능**:

| 항목 | 설명 | 파일 |
|------|------|------|
| 규칙 기반 갭 분석 | 채용 공고 기술 요구사항 vs 프로필 기술 비교 | `gap_analysis_service.py` |
| 중요도 분류 | critical (60%+), important (30%+), nice_to_have | `GapAnalyzer.analyze_gaps()` |
| 필수 기술 충족률 | 프로필 기술 / 요구 기술 비율 계산 | `GapAnalysisResult.match_coverage` |

**데이터 모델** (`src/models/gap_analysis.py`):
```python
class SkillGapLevel(str, Enum):
    CRITICAL = "critical"      # 60% 이상 공고에서 요구
    IMPORTANT = "important"    # 30% 이상 공고에서 요구
    NICE_TO_HAVE = "nice_to_have"

class GapAnalysisResult(BaseModel):
    profile_id: str
    matched_skills: List[SkillMatch]
    skill_gaps: List[SkillGap]
    match_coverage: float  # 0-100%
    top_missing_skills: List[str]
    analyzed_jobs_count: int
    analyzed_at: datetime
```

#### 2.11 커리어 전략 제시

**Groq LLM 기반 커리어 조언 생성**:

```python
class CareerAdvice(BaseModel):
    executive_summary: str              # 종합 조언
    learning_roadmap: List[LearningRoadmapItem]  # 12주 학습 계획
    portfolio_suggestions: List[PortfolioSuggestion]  # 프로젝트 3개
    resume_keywords: List[ResumeKeyword]  # 자기소개서 키워드 5개
    short_term_actions: List[str]       # 단기 액션 (1개월)
    mid_term_goals: List[str]           # 중기 목표 (3개월)
```

**CLI 명령어**:
```bash
# 특정 프로필 분석
python -m src.main analyze-gap 5

# 모든 프로필 분석
python -m src.main analyze-gap --all

# LLM 없이 갭 분석만 (빠른 테스트)
python -m src.main analyze-gap 5 --skip-llm
```

**GitHub Issue 코멘트 예시**:
```markdown
## 역량 갭 분석 결과 (2026-01-12)

**10개** 채용 공고를 분석했습니다.

### 요약
- 필수 기술 충족률: **65.0%**

### 부족한 기술
| 기술 | 중요도 | 등장 비율 |
|------|--------|-----------|
| Tableau | 🔴 필수 | 70% |
| Power BI | 🔴 필수 | 65% |

## 커리어 조언
> Python과 SQL 역량이 탄탄하지만, 시각화 도구를 보강하면...

### 12주 학습 로드맵
| 주차 | 주제 | 목표 |
|------|------|------|
| 1-2주 | Tableau 기초 | 대시보드 3개 제작 |
| 3-4주 | 통계학 기초 | 가설 검정 실습 |

### 포트폴리오 프로젝트
1. **쇼핑몰 고객 분석** - Python, Pandas, Tableau
2. **AB 테스트 분석** - 통계, Python

---
*Powered by Groq Llama 3.3 70B*
```

---

## 3. 기술 아키텍처

### 3.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (매일 09:00)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Saramin   │  │ Perplexity  │  │   Google    │         │
│  │   Crawler   │  │     API     │  │  Search API │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│                 ┌─────────────────┐                         │
│                 │   Job Collector │                         │
│                 │    (통합/필터)   │                         │
│                 └────────┬────────┘                         │
│                          │                                  │
│         ┌────────────────┼────────────────┐                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  jobs.json  │  │  Embedding  │  │   Profile   │         │
│  │   (저장)    │  │   Engine    │  │   Matcher   │         │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘         │
│                          │                │                 │
│                          └────────┬───────┘                 │
│                                   ▼                         │
│                          ┌─────────────────┐                │
│                          │  Notification   │                │
│                          │ (Issue Comment) │                │
│                          └─────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  GitHub Pages   │
                    │   (Dashboard)   │
                    └─────────────────┘
```

### 3.2 데이터 흐름

```
1. 크롤링 단계
   Saramin/Perplexity/Google → JobPosting 객체 → 필터링 → jobs.json

2. 임베딩 단계
   jobs.json → 텍스트 추출 → 임베딩 생성 → embeddings.json

3. 프로필 수집 단계
   GitHub Issues (label:profile) → Profile 객체 → profiles.json

4. 매칭 단계
   profiles.json + embeddings.json → 유사도 계산 → matches.json

5. 알림 단계
   matches.json → GitHub Issue Comment / Email
```

### 3.3 파일 구조 (리팩토링 후)

```
Recruitment_Auto/
├── .github/
│   ├── workflows/
│   │   ├── crawl.yml              # 크롤링 워크플로우
│   │   └── match.yml              # 매칭 워크플로우
│   └── ISSUE_TEMPLATE/
│       └── profile.yml            # 프로필 등록 템플릿
│
├── src/
│   ├── core/                      # 핵심 인터페이스 및 의존성
│   │   ├── __init__.py
│   │   ├── interfaces.py          # Protocol 정의
│   │   ├── container.py           # 의존성 컨테이너
│   │   └── config.py              # 설정 관리
│   │
│   ├── crawlers/                  # 크롤러 (단일 책임)
│   │   ├── __init__.py
│   │   ├── base.py                # 기본 크롤러 인터페이스
│   │   ├── saramin.py             # 사람인 크롤러
│   │   ├── inthiswork.py          # 인디스워크 크롤러
│   │   ├── perplexity.py          # Perplexity API 크롤러
│   │   └── google_search.py       # Google Search API 크롤러
│   │
│   ├── models/                    # 데이터 모델
│   │   ├── __init__.py
│   │   ├── job.py                 # 채용 공고 모델
│   │   ├── profile.py             # 사용자 프로필 모델
│   │   └── match.py               # 매칭 결과 모델
│   │
│   ├── services/                  # 비즈니스 로직 (단일 책임)
│   │   ├── __init__.py
│   │   ├── job_collector.py       # 채용 공고 수집 서비스
│   │   ├── job_filter.py          # 필터링 서비스
│   │   ├── embedding_service.py   # 임베딩 생성 서비스
│   │   ├── matching_service.py    # 매칭 서비스
│   │   ├── profile_service.py     # 프로필 관리 서비스
│   │   ├── gap_analysis.py        # 갭 분석 서비스
│   │   └── notification_service.py # 알림 서비스
│   │
│   ├── exporters/                 # 내보내기 (단일 책임)
│   │   ├── __init__.py
│   │   ├── json_exporter.py       # JSON 내보내기
│   │   └── static_site_builder.py # 정적 사이트 빌더
│   │
│   ├── notifiers/                 # 알림 발송 (단일 책임)
│   │   ├── __init__.py
│   │   ├── base.py                # 알림 인터페이스
│   │   ├── github_notifier.py     # GitHub Issue 알림
│   │   └── email_notifier.py      # 이메일 알림
│   │
│   ├── web/                       # 웹 인터페이스
│   │   ├── __init__.py
│   │   └── app.py                 # FastAPI 앱
│   │
│   └── main.py                    # CLI 진입점
│
├── tests/                         # 테스트 코드
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   ├── unit/                      # 단위 테스트
│   │   ├── test_job_filter.py
│   │   ├── test_matching_service.py
│   │   └── test_models.py
│   ├── integration/               # 통합 테스트
│   │   ├── test_crawlers.py
│   │   └── test_exporters.py
│   └── fixtures/                  # 테스트 데이터
│       ├── sample_jobs.json
│       └── sample_profiles.json
│
├── config/
│   └── settings.py                # 설정 파일
│
├── data/
│   ├── jobs.json                  # 수집된 채용 공고
│   ├── profiles.json              # 등록된 프로필
│   ├── embeddings.json            # 임베딩 벡터
│   └── matches.json               # 매칭 결과
│
├── docs/                          # GitHub Pages
│   ├── index.html
│   └── jobs.json
│
├── CLAUDE.md                      # AI 어시스턴트 컨텍스트
├── README.md
├── requirements.txt
├── pyproject.toml                 # 프로젝트 설정
└── pytest.ini                     # pytest 설정
```

---

## 4. 데이터 모델

### 4.1 JobPosting (확장)

```python
class JobPosting(BaseModel):
    # 기존 필드
    id: str
    title: str
    company_name: str
    company_logo: Optional[str]
    experience_level: ExperienceLevel
    experience_text: Optional[str]
    deadline: Optional[datetime]
    deadline_text: Optional[str]
    location: Optional[str]

    # 신규 필드
    category: JobCategory              # 직무 카테고리
    required_skills: List[str]         # 필수 기술
    preferred_skills: List[str]        # 우대 기술
    education: Optional[str]           # 학력 요건
    salary_range: Optional[str]        # 급여 범위
    benefits: List[str]                # 복리후생
    embedding: Optional[List[float]]   # 임베딩 벡터

    # 메타 정보
    source: JobSource
    source_url: str
    crawled_at: datetime
```

### 4.2 Profile (신규)

```python
class Profile(BaseModel):
    id: str                            # GitHub Issue ID
    github_username: str
    email: Optional[str]

    # 희망 조건
    job_category: JobCategory
    experience_years: int
    preferred_locations: List[str]

    # 역량
    skills: List[str]
    certifications: List[str]
    education: Optional[str]
    portfolio_url: Optional[str]

    # 임베딩
    embedding: Optional[List[float]]

    # 메타
    created_at: datetime
    updated_at: datetime
```

### 4.3 MatchResult (신규)

```python
class MatchResult(BaseModel):
    profile_id: str
    job_id: str
    score: float                       # 0-100
    score_breakdown: ScoreBreakdown    # 점수 상세
    matched_skills: List[str]          # 매칭된 기술
    missing_skills: List[str]          # 부족한 기술
    matched_at: datetime
```

---

## 5. API 키 및 환경변수

### 5.1 필수 환경변수

```bash
# Perplexity API (Phase 1)
PERPLEXITY_API_KEY=pplx-xxxx

# Google Custom Search (Phase 1)
GOOGLE_API_KEY=AIza-xxxx
GOOGLE_CSE_ID=xxxx

# OpenAI Embeddings (Phase 4, 선택적)
OPENAI_API_KEY=sk-xxxx

# Groq API (Phase 5) - 갭 분석 LLM
GROQ_API_KEY=gsk_xxxx

# Email (Phase 3)
SENDGRID_API_KEY=SG.xxxx
NOTIFICATION_EMAIL=from@example.com

# GitHub (Issue 코멘트 작성용)
GITHUB_TOKEN=ghp_xxxx
```

### 5.2 GitHub Secrets 설정

Repository Settings > Secrets and variables > Actions에서 설정:

```
PERPLEXITY_API_KEY
GOOGLE_API_KEY
GOOGLE_CSE_ID
OPENAI_API_KEY (선택)
GROQ_API_KEY (Phase 5)
GITHUB_TOKEN (Issue 코멘트용)
SENDGRID_API_KEY (선택)
```

---

## 6. 마일스톤

### Phase 1: 데이터 소스 확장 (1주차)
- [ ] Perplexity API 크롤러 구현
- [ ] Google Search API 크롤러 구현
- [ ] 데이터 소스 추상화 리팩토링
- [ ] 통합 테스트

### Phase 2: 채용 공고 상세화 (1주차)
- [ ] 자격 요건 파싱 강화
- [ ] 기술 스택 자동 태깅
- [ ] 직무 카테고리 자동 분류

### Phase 3: 알림 시스템 (2주차)
- [ ] 이메일 뉴스레터 템플릿
- [ ] SendGrid 연동
- [ ] 구독자 관리

### Phase 4: 프로필 매칭 (2주차)
- [ ] Issue 템플릿 생성
- [ ] 프로필 파서 구현
- [ ] 임베딩 서비스 구현
- [ ] 매칭 엔진 구현
- [ ] GitHub Issue 코멘트 알림

### Phase 5: 갭 분석 (3주차) ✅ 완료
- [x] 역량 갭 분석 로직 (`GapAnalyzer.analyze_gaps()`)
- [x] Groq LLM 커리어 전략 생성 (`GapAnalyzer.generate_career_advice()`)
- [x] GitHub Issue 코멘트 알림 (`format_gap_analysis_comment()`)
- [x] CLI 명령어 (`analyze-gap`)
- [ ] 대시보드 UI 개선 (향후)

---

## 7. UI/UX 방향성

### 7.1 디자인 시스템

- **프레임워크**: Next.js + Tailwind CSS (향후 확장 시)
- **현재**: 정적 HTML + Tailwind CDN
- **폰트**: Pretendard (한글 최적화)
- **색상**: Primary #3B82F6 (Blue-500)

### 7.2 대시보드 개선 (향후)

참고: [NEXTJS_UI_TUTORIAL.md](../NEXTJS_UI_TUTORIAL.md)의 디자인 시스템 활용

- 깔끔한 카드 기반 레이아웃
- 반응형 그리드
- 필터링 및 검색
- 매칭 점수 시각화
- 갭 분석 차트

---

## 8. 성공 지표

| 지표 | 목표 |
|------|------|
| 일간 수집 공고 수 | 100+ |
| 등록 프로필 수 | 50+ |
| 매칭 정확도 | 70%+ (사용자 피드백 기준) |
| 이메일 오픈율 | 30%+ |
| GitHub Star | 100+ |

---

## 9. 리스크 및 대응

| 리스크 | 대응 방안 |
|--------|-----------|
| API 비용 증가 | 무료 티어 우선 사용, 캐싱 적용 |
| 크롤링 차단 | User-Agent 로테이션, 요청 간격 조절 |
| 임베딩 성능 | 오픈소스 모델 우선, OpenAI는 옵션 |
| 개인정보 이슈 | 최소 정보만 수집, 명시적 동의 |

---

## 10. 참고 자료

- [Perplexity API Docs](https://docs.perplexity.ai/)
- [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)
- [Sentence Transformers](https://www.sbert.net/)
- [GitHub Actions](https://docs.github.com/actions)

---

*이 문서는 프로젝트 진행에 따라 지속적으로 업데이트됩니다.*
