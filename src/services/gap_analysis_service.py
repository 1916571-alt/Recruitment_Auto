"""
갭 분석 서비스

프로필과 채용 공고를 비교하여 역량 갭을 분석하고,
LLM 기반 커리어 조언을 생성합니다.
"""
import json
import os
from collections import Counter
from typing import List, Optional

import aiohttp
from loguru import logger

from src.core.interfaces import LLMProtocol
from src.models.job import JobPosting
from src.models.profile import Profile
from src.models.gap_analysis import (
    CareerAdvice,
    GapAnalysisResult,
    LearningRoadmapItem,
    LearningResource,
    PortfolioSuggestion,
    ResumeKeyword,
    SkillGap,
    SkillGapLevel,
    SkillMatch,
)


class GroqLLM(LLMProtocol):
    """Groq API 기반 LLM 서비스

    Llama 3.3 70B 모델을 사용한 빠른 추론.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    API_BASE = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._model = model or self.DEFAULT_MODEL

        if not self._api_key:
            logger.warning("GROQ_API_KEY가 설정되지 않았습니다")

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Groq API를 통한 텍스트 생성"""
        if not self._api_key:
            raise ValueError("GROQ_API_KEY가 필요합니다")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Groq API error: {resp.status} - {error_text}")
                    raise Exception(f"Groq API error: {resp.status}")

                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[dict] = None,
    ) -> dict:
        """JSON 형식 응답 생성"""
        json_system = (system_prompt or "") + "\n\n응답은 반드시 유효한 JSON 형식으로만 작성하세요. 다른 텍스트 없이 JSON만 반환하세요."

        response = await self.generate(
            prompt=prompt,
            system_prompt=json_system,
            temperature=0.3,
        )

        try:
            # 코드 블록 제거
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.debug(f"원본 응답: {response}")
            return {}


class GapAnalyzer:
    """갭 분석 서비스

    규칙 기반 갭 분석 + LLM 기반 커리어 조언 생성.
    """

    # 필수 기술 임계값 (이 비율 이상 등장하면 필수)
    CRITICAL_THRESHOLD = 0.6
    IMPORTANT_THRESHOLD = 0.3

    def __init__(self, llm: Optional[LLMProtocol] = None):
        self._llm = llm or GroqLLM()

    def analyze_gaps(
        self,
        profile: Profile,
        jobs: List[JobPosting],
    ) -> GapAnalysisResult:
        """규칙 기반 갭 분석"""
        if not jobs:
            return GapAnalysisResult(
                profile_id=profile.id,
                total_jobs_analyzed=0,
            )

        # 1. 채용 공고에서 요구 기술 집계
        required_skills: Counter = Counter()
        preferred_skills: Counter = Counter()
        all_certifications: Counter = Counter()

        for job in jobs:
            # tech_stack에서 추출 (주요 기술)
            for skill in job.tech_stack or []:
                required_skills[self._normalize_skill(skill)] += 1

            # requirements에서 추출
            for req in job.requirements or []:
                required_skills[self._normalize_skill(req)] += 1

            # preferred에서 추출
            for pref in job.preferred or []:
                preferred_skills[self._normalize_skill(pref)] += 1

        total_jobs = len(jobs)
        profile_skills_lower = {self._normalize_skill(s) for s in profile.skills}
        profile_certs_lower = {c.lower() for c in profile.certifications}

        # 2. 매칭된 스킬 분석
        matched_skills = []
        for skill in profile.skills:
            skill_lower = self._normalize_skill(skill)
            freq_required = required_skills.get(skill_lower, 0) / total_jobs
            freq_preferred = preferred_skills.get(skill_lower, 0) / total_jobs
            total_freq = freq_required + freq_preferred

            if total_freq > 0:
                matched_skills.append(SkillMatch(
                    skill_name=skill,
                    is_highlight=freq_required >= self.IMPORTANT_THRESHOLD,
                ))

        # 3. 부족한 스킬 분석
        skill_gaps = []
        all_skills = set(required_skills.keys()) | set(preferred_skills.keys())

        for skill in all_skills:
            if skill in profile_skills_lower:
                continue

            req_freq = required_skills.get(skill, 0) / total_jobs
            pref_freq = preferred_skills.get(skill, 0) / total_jobs

            # 갭 수준 결정
            if req_freq >= self.CRITICAL_THRESHOLD:
                gap_level = SkillGapLevel.CRITICAL
                priority = 1
            elif req_freq >= self.IMPORTANT_THRESHOLD:
                gap_level = SkillGapLevel.IMPORTANT
                priority = 2
            elif pref_freq >= self.IMPORTANT_THRESHOLD:
                gap_level = SkillGapLevel.NICE_TO_HAVE
                priority = 3
            else:
                continue  # 너무 낮은 빈도는 스킵

            skill_gaps.append(SkillGap(
                skill_name=skill.title(),
                gap_level=gap_level,
                frequency=max(req_freq, pref_freq),
                learning_priority=priority,
            ))

        # 우선순위순 정렬
        skill_gaps.sort(key=lambda x: (x.learning_priority, -x.frequency))

        # 4. 필수 기술 충족률 계산
        critical_skills = {
            s for s, c in required_skills.items()
            if c / total_jobs >= self.CRITICAL_THRESHOLD
        }
        matched_critical = critical_skills & profile_skills_lower
        match_coverage = (
            len(matched_critical) / len(critical_skills) * 100
        ) if critical_skills else 100

        # 5. 추천 자격증 (프로필에 없는 것)
        recommended_certs = [
            cert for cert, count in all_certifications.most_common(5)
            if cert not in profile_certs_lower
        ]

        return GapAnalysisResult(
            profile_id=profile.id,
            job_ids=[job.id for job in jobs if job.id],
            matched_skills=matched_skills,
            skill_gaps=skill_gaps[:10],
            total_jobs_analyzed=total_jobs,
            match_coverage=round(match_coverage, 1),
            top_missing_skills=[g.skill_name for g in skill_gaps[:5]],
            recommended_certifications=recommended_certs,
        )

    def _normalize_skill(self, skill: str) -> str:
        """스킬명 정규화"""
        return skill.lower().strip()

    async def generate_career_advice(
        self,
        profile: Profile,
        gap_analysis: GapAnalysisResult,
        jobs: List[JobPosting],
    ) -> CareerAdvice:
        """LLM 기반 커리어 조언 생성"""

        system_prompt = """당신은 IT 채용 전문 커리어 코치입니다.
사용자의 프로필과 채용 시장 분석을 바탕으로 실용적인 커리어 조언을 제공합니다.
조언은 구체적이고 실행 가능해야 합니다.
한국어로 응답하세요."""

        user_prompt = f"""## 프로필 정보
- 희망 직무: {profile.job_category.value}
- 경력: {profile.experience_years}년
- 보유 기술: {', '.join(profile.skills)}
- 자격증: {', '.join(profile.certifications) if profile.certifications else '없음'}
- 자기소개: {profile.introduction or '없음'}

## 채용 시장 분석 결과
- 분석된 채용 공고 수: {gap_analysis.total_jobs_analyzed}
- 필수 기술 충족률: {gap_analysis.match_coverage}%
- 가장 부족한 기술: {', '.join(gap_analysis.top_missing_skills)}

## 부족한 기술 상세
{self._format_skill_gaps(gap_analysis.skill_gaps)}

## 요청
위 정보를 바탕으로 다음을 제공해주세요:

1. 핵심 요약 (2-3문장): 현재 상태와 개선 방향
2. 12주 학습 로드맵: 주차별 학습 목표와 리소스
3. 포트폴리오 프로젝트 3개: 부족한 기술을 증명할 수 있는 프로젝트 아이디어
4. 자기소개서 키워드 5개: 채용 공고에서 자주 등장하는 키워드와 활용 예시
5. 단기 액션 아이템 (1개월): 당장 실행할 수 있는 것 3가지
6. 중기 목표 (3개월): 취업 준비 전략

JSON 형식으로 응답해주세요:
```json
{{
  "executive_summary": "...",
  "learning_roadmap": [
    {{"week": 1, "skill": "...", "goal": "...", "resources": [{{"name": "...", "type": "강의", "url": "..."}}]}}
  ],
  "portfolio_suggestions": [
    {{"project_idea": "...", "skills_demonstrated": ["..."], "difficulty": "중", "estimated_duration": "2주"}}
  ],
  "resume_keywords": [
    {{"keyword": "...", "context": "...", "frequency_in_jobs": 0.7}}
  ],
  "short_term_actions": ["..."],
  "mid_term_goals": ["..."]
}}
```"""

        try:
            response = await self._llm.generate_json(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            return CareerAdvice(
                profile_id=profile.id,
                executive_summary=response.get("executive_summary", "분석 결과를 생성하지 못했습니다."),
                learning_roadmap=self._parse_roadmap(response.get("learning_roadmap", [])),
                portfolio_suggestions=self._parse_portfolio(response.get("portfolio_suggestions", [])),
                resume_keywords=self._parse_keywords(response.get("resume_keywords", [])),
                short_term_actions=response.get("short_term_actions", []),
                mid_term_goals=response.get("mid_term_goals", []),
                llm_model=self._llm.model_name,
            )
        except Exception as e:
            logger.error(f"커리어 조언 생성 실패: {e}")
            return CareerAdvice(
                profile_id=profile.id,
                executive_summary=f"조언 생성 중 오류가 발생했습니다: {str(e)}",
                llm_model=self._llm.model_name,
            )

    def _format_skill_gaps(self, gaps: List[SkillGap]) -> str:
        """스킬 갭을 텍스트로 포맷"""
        lines = []
        for gap in gaps:
            level_text = {
                SkillGapLevel.CRITICAL: "필수",
                SkillGapLevel.IMPORTANT: "중요",
                SkillGapLevel.NICE_TO_HAVE: "우대",
            }.get(gap.gap_level, "")
            lines.append(f"- {gap.skill_name} [{level_text}]: 공고 {gap.frequency*100:.0f}%에서 요구")
        return "\n".join(lines) or "없음"

    def _parse_roadmap(self, data: List[dict]) -> List[LearningRoadmapItem]:
        """학습 로드맵 파싱"""
        items = []
        for item in data[:12]:
            resources = [
                LearningResource(
                    name=r.get("name", ""),
                    type=r.get("type", "강의"),
                    url=r.get("url"),
                    estimated_duration=r.get("estimated_duration"),
                )
                for r in item.get("resources", [])
            ]
            items.append(LearningRoadmapItem(
                week=item.get("week", len(items) + 1),
                skill=item.get("skill", ""),
                goal=item.get("goal", ""),
                resources=resources,
            ))
        return items

    def _parse_portfolio(self, data: List[dict]) -> List[PortfolioSuggestion]:
        """포트폴리오 제안 파싱"""
        return [
            PortfolioSuggestion(
                project_idea=item.get("project_idea", ""),
                skills_demonstrated=item.get("skills_demonstrated", []),
                difficulty=item.get("difficulty", "중"),
                estimated_duration=item.get("estimated_duration", "2주"),
            )
            for item in data[:5]
        ]

    def _parse_keywords(self, data: List[dict]) -> List[ResumeKeyword]:
        """키워드 파싱"""
        return [
            ResumeKeyword(
                keyword=item.get("keyword", ""),
                context=item.get("context", ""),
                frequency_in_jobs=item.get("frequency_in_jobs", 0.0),
            )
            for item in data[:10]
        ]


def format_gap_analysis_comment(
    gap: GapAnalysisResult,
    advice: Optional[CareerAdvice] = None,
) -> str:
    """GitHub Issue 코멘트 포맷"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"## 역량 갭 분석 결과 ({today})",
        "",
        f"**{gap.total_jobs_analyzed}개** 채용 공고를 분석했습니다.",
        "",
        "### 요약",
        f"- 필수 기술 충족률: **{gap.match_coverage}%**",
        "",
    ]

    # 보유 기술 (매칭됨)
    if gap.matched_skills:
        lines.extend([
            "### 보유 기술 (채용 공고와 매칭)",
            "",
        ])
        for skill in gap.matched_skills:
            highlight = " **[강조 추천]**" if skill.is_highlight else ""
            lines.append(f"- {skill.skill_name}{highlight}")
        lines.append("")

    # 부족한 기술
    if gap.skill_gaps:
        lines.extend([
            "### 부족한 기술",
            "",
            "| 기술 | 중요도 | 등장 비율 | 우선순위 |",
            "|------|--------|-----------|----------|",
        ])
        for skill in gap.skill_gaps:
            level_emoji = {
                "critical": "필수",
                "important": "중요",
                "nice_to_have": "우대",
            }.get(skill.gap_level.value, "")
            lines.append(
                f"| {skill.skill_name} | {level_emoji} | "
                f"{skill.frequency*100:.0f}% | {skill.learning_priority} |"
            )
        lines.append("")

    # LLM 커리어 조언
    if advice:
        lines.extend([
            "---",
            "",
            "## 커리어 조언",
            "",
            f"> {advice.executive_summary}",
            "",
        ])

        # 단기 액션
        if advice.short_term_actions:
            lines.extend([
                "### 단기 액션 아이템 (1개월)",
                "",
            ])
            for action in advice.short_term_actions:
                lines.append(f"- [ ] {action}")
            lines.append("")

        # 학습 로드맵 (처음 4주만 표시)
        if advice.learning_roadmap:
            lines.extend([
                "### 학습 로드맵 (첫 4주)",
                "",
            ])
            for item in advice.learning_roadmap[:4]:
                lines.append(f"**Week {item.week}**: {item.skill}")
                lines.append(f"- 목표: {item.goal}")
                if item.resources:
                    for res in item.resources[:2]:
                        url_text = f" ([링크]({res.url}))" if res.url else ""
                        lines.append(f"- 리소스: {res.name} ({res.type}){url_text}")
                lines.append("")

        # 포트폴리오 제안
        if advice.portfolio_suggestions:
            lines.extend([
                "### 포트폴리오 프로젝트 제안",
                "",
            ])
            for proj in advice.portfolio_suggestions[:3]:
                lines.append(f"**{proj.project_idea}**")
                lines.append(f"- 기술: {', '.join(proj.skills_demonstrated)}")
                lines.append(f"- 난이도: {proj.difficulty} | 기간: {proj.estimated_duration}")
                lines.append("")

        # 자기소개서 키워드
        if advice.resume_keywords:
            lines.extend([
                "### 자기소개서 추천 키워드",
                "",
                "| 키워드 | 활용 예시 |",
                "|--------|-----------|",
            ])
            for kw in advice.resume_keywords[:5]:
                context_short = kw.context[:50] + "..." if len(kw.context) > 50 else kw.context
                lines.append(f"| {kw.keyword} | {context_short} |")
            lines.append("")

    lines.extend([
        "---",
        "*자동 생성됨 by [Recruitment Auto](https://1916571-alt.github.io/Recruitment_Auto/) | "
        "Powered by Groq (Llama 3.3 70B)*",
    ])

    return "\n".join(lines)
