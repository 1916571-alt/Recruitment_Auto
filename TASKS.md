# TASKS.md - Recruitment Auto v2.0 태스크 트래커

> PRD.md 기반 구현 체크리스트
> 최종 수정일: 2026-01-12
> **Phase 5 완료** - Groq API 기반 갭 분석 및 커리어 전략 기능 구현

---

## Phase 1: 데이터 소스 확장

### 1.1 Google Custom Search API
- [x] CSE ID 발급 및 설정
- [x] GoogleSearchCrawler 클래스 구현
- [x] JobSource enum에 GOOGLE_SEARCH 추가
- [x] 조건부 크롤러 로딩 (API 키 없으면 비활성화)
- [x] 직군별 검색 키워드 설정 (config/settings.py)
  - [x] 데이터 분석 (data)
  - [x] 프론트엔드 (frontend)
  - [x] 백엔드 (backend)
  - [x] 기획/PM (pm)
- [ ] GitHub Actions secrets 설정 (GOOGLE_API_KEY, GOOGLE_CSE_ID)

### 1.2 Perplexity API
- [ ] Perplexity API 가입 및 키 발급
- [ ] PerplexityCrawler 클래스 구현
- [ ] JobSource enum에 PERPLEXITY 추가
- [ ] 프롬프트 최적화 (구조화된 JSON 응답)

### 1.3 데이터 소스 추상화
- [x] CrawlerProtocol 인터페이스 정의 (src/core/interfaces.py)
- [x] BaseCrawler 추상 클래스 구현
- [x] 의존성 주입 패턴 적용

### 1.4 중복 제거 강화
- [ ] URL 정규화 (쿼리 파라미터 제거)
- [ ] 회사+포지션 기반 유사도 검사
- [ ] 크롤러 간 중복 제거 로직

---

## Phase 2: 채용 공고 상세화

### 2.1 자격 요건 추출 강화
- [ ] JobRequirements 모델 정의
- [ ] LLM 기반 요건 파싱 (필수/우대 분리)
- [ ] 기술 스택 자동 태깅

### 2.2 직무 카테고리 자동 분류
- [ ] JobCategory enum 정의
- [ ] 키워드 기반 분류 로직
- [ ] 분류 정확도 검증

---

## Phase 3: 알림 시스템

### 3.1 이메일 뉴스레터
- [ ] SendGrid 계정 생성 및 API 키 발급
- [ ] 이메일 템플릿 디자인
- [ ] EmailNotifier 클래스 구현
- [ ] 구독자 관리 (GitHub Issue 기반)

### 3.2 발송 스케줄
- [ ] 매일 09:00 KST 발송 워크플로우
- [ ] 개인화된 추천 공고 포함

---

## Phase 4: 프로필 매칭 시스템 ✅ 완료

### 4.1 프로필 등록
- [x] GitHub Issue 템플릿 생성 (.github/ISSUE_TEMPLATE/profile.yml)
- [x] Profile 모델 정의 (src/models/profile.py)
- [x] 프로필 파서 구현 (GitHubService.parse_issue_to_profile)

### 4.2 임베딩 서비스
- [x] 임베딩 모델 선택 (sentence-transformers/all-MiniLM-L6-v2)
- [x] EmbeddingService 클래스 구현
- [x] 채용 공고 임베딩 생성
- [x] 프로필 임베딩 생성

### 4.3 매칭 엔진
- [x] ProfileMatcher 클래스 구현 (src/services/matching_service.py)
- [x] 규칙 기반 1차 필터 (직무, 경력, 위치)
- [x] 임베딩 유사도 2차 점수화
- [x] 매칭 점수 산출 로직

### 4.4 매칭 결과 알림
- [x] GitHubService.post_comment() 구현
- [x] Issue 코멘트로 매칭 결과 전송
- [ ] 매칭 결과 대시보드 표시 (향후)

---

## Phase 5: 갭 분석 및 커리어 전략 ✅ 완료

> **구현 완료일**: 2026-01-12
> **LLM**: Groq API (Llama 3.3 70B Versatile)

### 5.1 역량 갭 분석
- [x] GapAnalysisResult 모델 정의 (src/models/gap_analysis.py)
- [x] SkillGap, SkillMatch, SkillGapLevel 모델
- [x] 규칙 기반 갭 분석 (GapAnalyzer.analyze_gaps)
- [x] 필수 기술 충족률 계산
- [x] 중요도 분류 (critical/important/nice_to_have)

### 5.2 커리어 전략 생성
- [x] GroqLLM 클래스 구현 (LLMProtocol)
- [x] CareerAdvice 모델 (학습 로드맵, 포트폴리오, 키워드)
- [x] LLM 기반 커리어 조언 생성 (GapAnalyzer.generate_career_advice)
- [x] 12주 학습 로드맵 생성
- [x] 포트폴리오 프로젝트 제안 (3개)
- [x] 자기소개서 키워드 추천 (5개)
- [x] 단기/중기 액션 아이템

### 5.3 GitHub Issue 연동
- [x] format_gap_analysis_comment() 마크다운 포맷터
- [x] GitHubService.post_comment() 연동
- [x] 갭 분석 결과 Issue 코멘트 작성

### 5.4 CLI 명령어
- [x] `analyze-gap` 커맨드 구현 (src/main.py)
- [x] `--all` 옵션 (모든 프로필 분석)
- [x] `--skip-llm` 옵션 (LLM 없이 갭 분석만)
- [x] `--top-k` 옵션 (분석할 채용 공고 수)

### 5.5 설정
- [x] AppConfig에 groq_api_key, groq_model 추가
- [x] AppConfig에 github_token 추가
- [x] LLMProtocol 인터페이스 정의

### 신규 파일
| 파일 | 설명 |
|------|------|
| `src/models/gap_analysis.py` | 갭 분석 데이터 모델 |
| `src/services/gap_analysis_service.py` | GroqLLM, GapAnalyzer 클래스 |

---

## 인프라 및 기타

### CI/CD
- [ ] GitHub Actions 워크플로우 업데이트
  - [ ] 환경변수 secrets 설정
  - [ ] 매칭 워크플로우 추가 (.github/workflows/match.yml)
- [ ] 테스트 자동화

### 문서화
- [x] CLAUDE.md 작성
- [x] PRD.md 작성
- [x] TASKS.md 작성 (현재 파일)
- [ ] README.md 업데이트

### 테스트
- [ ] 단위 테스트 작성 (pytest)
- [ ] 통합 테스트 작성
- [ ] 테스트 커버리지 80% 이상

---

## 완료된 작업 요약

| 날짜 | 작업 | 상태 |
|------|------|------|
| 2026-01-12 | Google Search API 크롤러 구현 | 완료 |
| 2026-01-12 | 직군별 검색 키워드 설정 확장 | 완료 |
| 2026-01-12 | BaseCrawler DI 패턴 적용 | 완료 |
| 2026-01-12 | Phase 4: 프로필 매칭 시스템 구현 | 완료 |
| 2026-01-12 | Phase 5: Groq API 기반 갭 분석 구현 | 완료 |
| 2026-01-12 | GitHub Issue 코멘트 알림 기능 | 완료 |
| 2026-01-12 | 테스트 프로필 Issue #1-4 생성 | 완료 |

---

## 다음 우선순위

1. **GitHub Actions secrets 설정** - GROQ_API_KEY, GITHUB_TOKEN 추가
2. **중복 제거 강화** - 데이터 품질 개선
3. **대시보드 UI 개선** - 갭 분석 결과 시각화
4. **Perplexity API 연동** - 데이터 소스 다각화

---

*이 파일은 PRD.md와 동기화되어야 합니다.*
