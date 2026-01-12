# Recruitment Auto - 채용 정보 자동 수집 & 매칭 에이전트

> 채용 공고를 자동 수집하고, GitHub Issue 프로필 기반으로 맞춤 공고를 추천하는 에이전트

## 대시보드

**https://1916571-alt.github.io/Recruitment_Auto/**

## 특징

- **자동 수집**: GitHub Actions가 매일 09:00 KST 자동 크롤링
- **프로필 매칭**: GitHub Issue로 프로필 등록 → 맞춤 공고 추천
- **무료 호스팅**: GitHub Pages로 서버 비용 없이 운영
- **다양한 직군**: 데이터, 백엔드, 프론트엔드, PM/기획
- **신입 전용**: 신입/경력무관/인턴/주니어 공고만 수집

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

## 프로필 등록 방법

1. [Issues](../../issues) 탭에서 "New Issue" 클릭
2. "프로필 등록" 템플릿 선택
3. 정보 입력 후 제출
4. 매일 자동으로 맞춤 공고가 코멘트로 전달됨

### 프로필 형식

```markdown
### GitHub 사용자명
your-username

### 희망 직무
데이터 분석 / 백엔드 개발 / 프론트엔드 개발 / PM/기획

### 경력 (년)
0

### 보유 기술
Python
SQL
Pandas

### 희망 근무지
서울, 판교
```

## 대상 채용 사이트

| 사이트 | 상태 |
|--------|------|
| 사람인 | ✅ |
| 인디스워크 | ✅ |
| Google Search | ✅ |

## 매칭 로직

**2-Stage 매칭:**
1. **경력 필터** (Hard Filter): 경력 조건 불일치 시 제외
2. **점수 계산**:
   - 직무 카테고리 매칭: 40점
   - 스킬/설명 임베딩 유사도: 60점

## 빠른 시작

### 1. 저장소 Fork

이 저장소를 Fork 하세요.

### 2. GitHub Pages 활성화

1. Settings → Pages
2. Source: **GitHub Actions** 선택

### 3. Secrets 설정 (선택)

Settings → Secrets and variables → Actions:
- `GOOGLE_API_KEY`: Google Custom Search API 키
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

### 4. 첫 실행

1. Actions 탭 → "채용 정보 수집" 워크플로우
2. "Run workflow" 클릭

### 5. 프로필 등록

Issues 탭에서 프로필을 등록하면 맞춤 공고 추천을 받을 수 있습니다.

---

## 로컬 실행

```bash
# 환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 크롤링 + JSON 저장
python -m src.main crawl-to-json

# 정적 사이트 생성
python -m src.main build-static

# 프로필 매칭 실행
python -m src.main match-profiles

# 로컬 서버로 확인
cd docs && python -m http.server 8000
```

## 명령어

| 명령 | 설명 |
|------|------|
| `crawl-to-json` | 크롤링 → JSON 저장 |
| `build-static` | 정적 HTML 생성 → docs/ |
| `match-profiles` | 프로필 매칭 → Issue 코멘트 |
| `list-profiles` | 등록된 프로필 목록 |
| `serve` | 로컬 웹 서버 실행 |
| `stats` | 수집 통계 출력 |

## 프로젝트 구조

```
Recruitment_Auto/
├── .github/
│   └── workflows/
│       └── crawl.yml           # GitHub Actions 워크플로우
├── src/
│   ├── crawlers/               # 크롤러 (사람인, 인디스워크, Google)
│   ├── services/               # 매칭, 임베딩, GitHub 연동
│   ├── models/                 # 데이터 모델
│   └── main.py                 # CLI
├── config/
│   └── settings.py             # 필터 설정
├── data/
│   └── jobs.json               # 수집된 데이터
└── docs/                       # GitHub Pages 배포
    ├── index.html
    └── jobs.json
```

## 필터 조건 수정

[config/settings.py](config/settings.py) 에서 키워드 변경:

```python
job_keywords = [
    # 데이터 분석
    "데이터 분석", "Data Analyst", "데이터 사이언티스트",
    # 백엔드 개발
    "백엔드", "Backend", "Spring", "Node.js",
    # 프론트엔드 개발
    "프론트엔드", "Frontend", "React", "Vue",
    # PM/기획
    "서비스 기획", "PM", "프로덕트 매니저",
]
```

## License

MIT - 개인 학습 및 정보 수집 목적으로 사용하세요.
