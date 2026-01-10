# Recruitment Auto - 채용 정보 자동 수집 에이전트

> 데이터 분석 관련 채용 공고를 자동으로 수집하고 GitHub Pages에서 확인할 수 있는 에이전트

## 대시보드

**https://1916571-alt.github.io/Recruitment_Auto/**

## 특징

- **자동 수집**: GitHub Actions가 매일 1회 (09:00 KST) 자동 크롤링
- **무료 호스팅**: GitHub Pages로 서버 비용 없이 운영
- **실시간 필터**: 새 공고, 마감 임박 필터링
- **신입 전용**: 신입/경력무관/인턴 공고만 수집

## 대상 채용 사이트

| 사이트 | 상태 |
|--------|------|
| 사람인 | ✅ |
| 인디스워크 | ✅ |

> **주의**: 개인 학습/정보 수집 목적으로만 사용하세요

## 수집 정보

- 회사명 / 포지션명
- **마감일** (D-Day 표시)
- 경력 요건 (신입/경력무관/인턴)
- 근무 위치
- 원본 링크

## 빠른 시작

### 1. 저장소 Fork

이 저장소를 Fork 하세요.

### 2. GitHub Pages 활성화

1. Settings → Pages
2. Source: **GitHub Actions** 선택

### 3. 첫 실행

1. Actions 탭 → "채용 정보 수집" 워크플로우
2. "Run workflow" 클릭

### 4. 대시보드 확인

https://1916571-alt.github.io/Recruitment_Auto/

---

## 로컬 실행 (선택)

```bash
# 환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 크롤링 + JSON 저장
python -m src.main crawl-to-json

# 정적 사이트 생성
python -m src.main build-static

# 로컬 서버로 확인
cd docs && python -m http.server 8000
```

## 명령어

| 명령 | 설명 |
|------|------|
| `crawl` | 크롤링 → DB 저장 (로컬용) |
| `crawl-to-json` | 크롤링 → JSON 저장 (GitHub Actions용) |
| `build-static` | 정적 HTML 생성 → docs/ |
| `serve` | 로컬 웹 서버 실행 |
| `stats` | 수집 통계 출력 |

## 프로젝트 구조

```
Recruitment_Auto/
├── .github/
│   └── workflows/
│       └── crawl.yml         # GitHub Actions 워크플로우
├── src/
│   ├── crawlers/             # 사람인, 인디스워크 크롤러
│   ├── models/               # 데이터 모델
│   ├── storage/              # SQLite (로컬용)
│   ├── exporter.py           # JSON 내보내기
│   ├── web/                  # FastAPI 앱 (로컬용)
│   └── main.py               # CLI
├── data/
│   └── jobs.json             # 수집된 데이터
├── docs/                     # GitHub Pages 배포
│   ├── index.html
│   └── jobs.json
├── config/
│   └── settings.py           # 필터 설정
└── requirements.txt
```

## 필터 조건 수정

[config/settings.py](config/settings.py) 에서 키워드 변경:

```python
job_keywords = [
    "데이터 분석",
    "Data Analyst",
    "데이터 사이언티스트",
    # 원하는 키워드 추가
]
```

## 자동 업데이트 스케줄

- **매일 09:00 KST** (UTC 00:00)

수정: [.github/workflows/crawl.yml](.github/workflows/crawl.yml)

```yaml
schedule:
  - cron: '0 0 * * *'   # 09:00 KST
```

## License

MIT - 개인 학습 및 정보 수집 목적으로 사용하세요.
