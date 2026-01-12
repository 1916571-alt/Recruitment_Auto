# CLAUDE.md - Recruitment Auto 프로젝트 컨텍스트

> 이 파일은 Claude AI가 프로젝트를 이해하는 데 필요한 컨텍스트를 제공합니다.

## 프로젝트 개요

**Recruitment Auto**는 채용 정보를 자동으로 수집하고, 프로필 매칭 및 갭 분석을 제공하는 에이전트입니다.

- **대시보드**: https://1916571-alt.github.io/Recruitment_Auto/
- **자동 수집 + 매칭**: 매일 09:00 KST (GitHub Actions)
- **타겟**: 신입/주니어 (데이터, 백엔드, 프론트엔드, PM/기획)

## 자동화 파이프라인

```
GitHub Actions (매일 09:00 KST)
    ↓
1. crawl-to-json    : 채용 공고 수집 → data/jobs.json
    ↓
2. build-static     : 정적 사이트 생성 → docs/
    ↓
3. match-profiles   : 프로필-공고 매칭 → Issue 코멘트
    ↓
4. deploy           : GitHub Pages 배포
```

## 기술 스택

```
Python 3.11
├── 웹 프레임워크: FastAPI, uvicorn
├── 크롤링: aiohttp, BeautifulSoup4, Selenium
├── 데이터: Pydantic, Pandas, SQLAlchemy
├── CLI: Typer, Rich
├── 스케줄링: APScheduler
├── 임베딩: sentence-transformers
├── LLM: Groq API (Llama 3.3 70B)
└── 로깅: loguru
```

## 프로젝트 구조

```
src/
├── core/                  # 핵심 인터페이스 및 DI 컨테이너
│   ├── interfaces.py      # Protocol 정의 (CrawlerProtocol, LLMProtocol 등)
│   ├── container.py       # 의존성 주입 컨테이너
│   └── config.py          # 설정 관리 (API 키, 경로 등)
├── crawlers/              # 데이터 소스별 크롤러
│   ├── base.py            # BaseCrawler 추상 클래스
│   ├── saramin.py         # 사람인 크롤러
│   ├── inthiswork.py      # 인디스워크 크롤러
│   └── google_search.py   # Google Custom Search 크롤러
├── services/              # 비즈니스 로직
│   ├── job_collector.py   # 채용 공고 수집
│   ├── job_filter.py      # 필터링 로직
│   ├── matching_service.py    # 프로필-공고 매칭
│   ├── embedding_service.py   # 임베딩 생성/관리
│   ├── github_service.py      # GitHub Issue 연동
│   └── gap_analysis_service.py # 갭 분석 + LLM 커리어 조언
├── models/                # 데이터 모델
│   ├── job.py             # JobPosting, JobSource, ExperienceLevel
│   ├── profile.py         # Profile, JobCategory
│   ├── match.py           # MatchResult, ScoreBreakdown
│   └── gap_analysis.py    # GapAnalysisResult, CareerAdvice
├── notifiers/             # 알림
│   └── github_notifier.py # GitHub Issue 코멘트
├── exporters/             # 내보내기
│   ├── json_exporter.py   # JSON 저장
│   └── static_site.py     # HTML 생성
└── main.py                # CLI 진입점

config/
└── settings.py            # 필터 키워드, 크롤러 설정

data/
├── jobs.json              # 수집된 채용 공고
└── embeddings/            # 임베딩 캐시 (.npy)

docs/
├── index.html             # GitHub Pages 대시보드
├── jobs.json              # 배포용 데이터
└── PRD.md                 # 제품 요구사항 문서
```

## 주요 명령어

```bash
# 크롤링 → JSON 저장 (GitHub Actions용)
python -m src.main crawl-to-json

# 정적 사이트 생성
python -m src.main build-static

# 로컬 웹 서버
python -m src.main serve

# 통계 확인
python -m src.main stats

# 임베딩 업데이트
python -m src.main update-embeddings

# 프로필 매칭 실행
python -m src.main match-profiles

# 프로필 목록 조회
python -m src.main list-profiles

# 갭 분석 (LLM 커리어 조언 포함)
python -m src.main analyze-gap 1           # 특정 프로필
python -m src.main analyze-gap --all       # 모든 프로필
python -m src.main analyze-gap 1 --skip-llm  # LLM 없이
```

## 구현 완료된 기능

### Phase 1-3: 크롤링 및 필터링 ✅
- 사람인, 인디스워크, Google Search 크롤러
- 키워드 기반 필터링
- GitHub Pages 대시보드

### Phase 4: 프로필 매칭 ✅
- GitHub Issue 기반 프로필 등록
- **2-Stage 매칭**:
  1. 경력 조건 Hard Filter (불일치 시 제외)
  2. 직무 카테고리 (40점) + 스킬/설명 임베딩 유사도 (60점)
- GitHub Actions에서 자동 실행 → Issue 코멘트

### Phase 5: 갭 분석 ✅ (2026-01-12 구현)
- **GapAnalyzer**: 프로필 vs 채용공고 역량 비교
- **GroqLLM**: Groq API (Llama 3.3 70B) 기반 커리어 조언
- **결과 제공**:
  - 필수 기술 충족률
  - 부족한 기술 목록 (우선순위)
  - 12주 학습 로드맵
  - 포트폴리오 프로젝트 제안
  - 자기소개서 키워드
  - 단기/중기 액션 아이템
- **GitHub Issue 코멘트**로 결과 자동 전송

## 아키텍처 원칙

### 1. Protocol 기반 인터페이스

```python
# src/core/interfaces.py
class CrawlerProtocol(Protocol):
    async def crawl(self) -> List[JobPosting]: ...

class LLMProtocol(Protocol):
    async def generate(self, prompt: str, ...) -> str: ...
    async def generate_json(self, prompt: str, ...) -> dict: ...

class EmbeddingProtocol(Protocol):
    async def embed(self, text: str) -> List[float]: ...
```

### 2. 의존성 주입

```python
class GapAnalyzer:
    def __init__(self, llm: Optional[LLMProtocol] = None):
        self._llm = llm or GroqLLM()
```

### 3. 단일 책임 원칙

| 클래스 | 책임 |
|--------|------|
| `GapAnalyzer` | 갭 분석 + 커리어 조언 생성 |
| `GroqLLM` | Groq API 호출 |
| `ProfileMatcher` | 프로필-공고 매칭 |
| `SentenceTransformerEmbedding` | 임베딩 생성/캐싱 |

## 데이터 모델

### GapAnalysisResult

```python
class GapAnalysisResult(BaseModel):
    profile_id: str
    matched_skills: List[SkillMatch]      # 매칭된 기술
    skill_gaps: List[SkillGap]            # 부족한 기술
    match_coverage: float                  # 필수 기술 충족률 (0-100)
    top_missing_skills: List[str]          # 상위 5개 부족 기술
```

### CareerAdvice

```python
class CareerAdvice(BaseModel):
    executive_summary: str                 # 핵심 요약
    learning_roadmap: List[LearningRoadmapItem]  # 12주 학습 계획
    portfolio_suggestions: List[PortfolioSuggestion]  # 프로젝트 제안
    resume_keywords: List[ResumeKeyword]   # 자기소개서 키워드
    short_term_actions: List[str]          # 1개월 액션
    mid_term_goals: List[str]              # 3개월 목표
```

## 환경변수

```bash
# .env 파일
GROQ_API_KEY=gsk_xxxx           # Groq API (갭 분석용)
GITHUB_TOKEN=ghp_xxxx           # GitHub API (Issue 코멘트)
GOOGLE_API_KEY=AIza-xxxx        # Google Search (선택)
GOOGLE_CSE_ID=xxxx              # Google CSE ID (선택)
```

## 테스트

```bash
# 전체 테스트
pytest

# 갭 분석 테스트
pytest tests/unit/test_gap_analysis.py -v

# 커버리지
pytest --cov=src tests/
```

## GitHub Issue 프로필 형식

```markdown
### GitHub 사용자명
your-username

### 희망 직무
데이터 분석

### 경력 (년)
0

### 보유 기술
Python
SQL
Pandas

### 자격증 (선택)
SQLD

### 희망 근무지
서울, 판교

### 이메일 (뉴스레터용, 선택)
your@email.com

### 간단한 자기소개 (선택)
...
```

## 주의사항

1. **크롤링 제한**: 요청 간 2초 대기
2. **API 비용**: Groq은 무료, rate limit 있음
3. **개인정보**: 이메일 등 민감 정보 로깅 금지
4. **저작권**: 수집 데이터는 개인 학습 목적으로만 사용

## 문의

GitHub Issues로 문의해주세요.
