"""
채용 정보 자동 수집 에이전트 - 메인 진입점
"""
import asyncio
import json
from typing import Optional, Annotated

import typer
from typer import Option, Argument
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.crawlers import SaraminCrawler, InthisworkCrawler, GoogleSearchCrawler
from src.storage import Database
from src.exporter import JSONExporter
from src.exporters.static_site_builder import StaticSiteBuilder
from src.core.config import get_config
from src.models import JobPosting
from config import settings

app = typer.Typer(help="채용 정보 자동 수집 에이전트")
console = Console()


def get_crawlers():
    """사용 가능한 크롤러 목록 반환

    환경변수 설정에 따라 크롤러를 동적으로 로드합니다.
    """
    crawlers = [
        SaraminCrawler,
        InthisworkCrawler,
    ]

    # Google Search 크롤러 - 현재 비활성화
    # 활성화하려면 아래 주석 해제
    # config = get_config()
    # if config.google_api_key and config.google_cse_id:
    #     crawlers.append(GoogleSearchCrawler)
    #     logger.info("GoogleSearchCrawler 활성화됨")

    return crawlers


# 크롤러 목록 (기본값, 동적 로딩은 get_crawlers() 사용)
CRAWLERS = [
    SaraminCrawler,
    InthisworkCrawler,
]


async def run_crawlers():
    """모든 크롤러 실행"""
    db = Database()
    total_jobs = []
    crawlers = get_crawlers()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for CrawlerClass in crawlers:
            crawler_name = CrawlerClass.__name__
            task = progress.add_task(f"[cyan]{crawler_name} 수집 중...", total=None)

            try:
                async with CrawlerClass() as crawler:
                    jobs = await crawler.crawl()
                    total_jobs.extend(jobs)

                    # 상세 정보 가져오기 (처음 10개만)
                    for job in jobs[:10]:
                        try:
                            await crawler.get_job_detail(job)
                        except Exception as e:
                            logger.error(f"상세 정보 오류: {e}")

                progress.update(task, description=f"[green]{crawler_name}: {len(jobs)}건 완료")

            except Exception as e:
                logger.error(f"{crawler_name} 오류: {e}")
                progress.update(task, description=f"[red]{crawler_name}: 오류 발생")

    # 저장
    if total_jobs:
        saved = db.save_jobs(total_jobs)
        console.print(f"\n[bold green]수집 완료![/] 총 {len(total_jobs)}건 수집, {saved}건 신규 저장")

    # 마감된 공고 처리
    db.mark_expired_jobs()

    return total_jobs


@app.command()
def crawl():
    """채용 공고 크롤링 실행 (DB 저장)"""
    console.print("[bold blue]채용 정보 수집을 시작합니다...[/]")
    asyncio.run(run_crawlers())


@app.command("crawl-to-json")
def crawl_to_json():
    """채용 공고 크롤링 후 JSON으로 저장 (GitHub Actions용)"""
    console.print("[bold blue]채용 정보 수집을 시작합니다 (JSON 모드)...[/]")

    async def run():
        total_jobs = []
        crawlers = get_crawlers()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for CrawlerClass in crawlers:
                crawler_name = CrawlerClass.__name__
                task = progress.add_task(f"[cyan]{crawler_name} 수집 중...", total=None)

                try:
                    async with CrawlerClass() as crawler:
                        jobs = await crawler.crawl()
                        total_jobs.extend(jobs)

                        # 상세 정보 가져오기 (처음 5개만 - API 제한 고려)
                        for job in jobs[:5]:
                            try:
                                await crawler.get_job_detail(job)
                            except Exception as e:
                                logger.error(f"상세 정보 오류: {e}")

                    progress.update(task, description=f"[green]{crawler_name}: {len(jobs)}건 완료")

                except Exception as e:
                    logger.error(f"{crawler_name} 오류: {e}")
                    progress.update(task, description=f"[red]{crawler_name}: 오류 발생")

        # JSON으로 저장
        if total_jobs:
            exporter = JSONExporter()
            exporter.export_jobs(total_jobs)
            console.print(f"\n[bold green]수집 완료![/] 총 {len(total_jobs)}건")

        return total_jobs

    asyncio.run(run())


@app.command("build-static")
def build_static():
    """정적 사이트 생성 (GitHub Pages용)"""
    console.print("[bold blue]정적 사이트를 생성합니다...[/]")
    builder = StaticSiteBuilder()
    builder.build()
    console.print("[bold green]완료![/] docs/ 폴더에 생성됨")


@app.command()
def serve(
    host: Annotated[str, Option(help="서버 호스트")] = "0.0.0.0",
    port: Annotated[int, Option(help="서버 포트")] = 8000,
    reload: Annotated[bool, Option(help="자동 리로드")] = False,
):
    """웹 대시보드 서버 실행"""
    console.print(f"[bold blue]웹 대시보드를 시작합니다...[/]")
    console.print(f"[green]http://localhost:{port}[/]")

    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def schedule(
    interval: Annotated[int, Option(help="크롤링 간격 (분)")] = 60,
):
    """스케줄러와 함께 웹 서버 실행"""
    console.print(f"[bold blue]스케줄러 모드로 시작합니다...[/]")
    console.print(f"크롤링 간격: {interval}분")

    async def main():
        # 스케줄러 설정
        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_crawlers, "interval", minutes=interval)

        # 즉시 한 번 실행
        await run_crawlers()

        # 스케줄러 시작
        scheduler.start()

        # 웹 서버 실행
        config = uvicorn.Config(
            "src.web.app:app",
            host="0.0.0.0",
            port=8000,
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())


@app.command()
def stats():
    """수집된 데이터 통계 출력"""
    db = Database()
    stats = db.get_statistics()

    console.print("\n[bold]채용 공고 통계[/]")
    console.print("-" * 40)

    table = Table(show_header=True, header_style="bold")
    table.add_column("항목", style="cyan")
    table.add_column("수량", justify="right", style="green")

    table.add_row("전체 공고", str(stats["total"]))
    table.add_row("새 공고", str(stats["new"]))
    table.add_row("7일 내 마감", str(stats["expiring_7days"]))

    console.print(table)

    console.print("\n[bold]사이트별 통계[/]")
    source_table = Table(show_header=True, header_style="bold")
    source_table.add_column("사이트", style="cyan")
    source_table.add_column("수량", justify="right", style="green")

    for source, count in stats["by_source"].items():
        source_table.add_row(source.upper(), str(count))

    console.print(source_table)


@app.command()
def list_jobs(
    limit: Annotated[int, Option(help="출력할 공고 수")] = 20,
    source: Annotated[Optional[str], Option(help="필터할 소스")] = None,
):
    """수집된 채용 공고 목록 출력"""
    db = Database()

    if source:
        jobs = db.get_jobs_by_source(source)
    else:
        jobs = db.get_all_jobs()

    jobs = jobs[:limit]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("회사", style="cyan", width=20)
    table.add_column("포지션", width=35)
    table.add_column("경력", width=10)
    table.add_column("마감", width=12)
    table.add_column("소스", width=10)

    for job in jobs:
        new_marker = "[green]★[/]" if job.is_new else ""
        table.add_row(
            f"{new_marker} {job.company_name[:18]}",
            job.title[:33],
            job.experience_text or "-",
            job.deadline_text or "상시",
            job.source.upper(),
        )

    console.print(table)
    console.print(f"\n총 {len(jobs)}건 표시")


@app.command("update-embeddings")
def update_embeddings():
    """채용 공고 임베딩 업데이트"""
    console.print("[bold blue]임베딩 업데이트 시작...[/]")

    async def run():
        from src.services.embedding_service import SentenceTransformerEmbedding

        config = get_config()

        # jobs.json 로드
        with open(config.jobs_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        jobs = data.get("jobs", [])

        if not jobs:
            console.print("[yellow]저장된 채용 공고가 없습니다.[/]")
            return

        # 임베딩 서비스
        embedding_service = SentenceTransformerEmbedding()

        # 텍스트 생성
        texts = []
        ids = []
        for job in jobs:
            text = f"{job['title']} {job.get('description', '') or ''} {' '.join(job.get('tech_stack', []) or [])}"
            texts.append(text)
            ids.append(job['id'])

        console.print(f"[cyan]{len(ids)}개 채용 공고 임베딩 생성 중...[/]")

        # 배치 임베딩
        embeddings = await embedding_service.embed_batch(texts)

        # 저장
        embedding_service.save_embeddings(ids, embeddings, "jobs")

        console.print(f"[bold green]완료![/] {len(ids)}개 임베딩 저장됨")

    asyncio.run(run())


@app.command("match-profiles")
def match_profiles(
    issue_number: Annotated[Optional[int], Argument(help="매칭할 프로필 Issue 번호")] = None,
    all_profiles: Annotated[bool, Option("--all", help="모든 프로필 매칭")] = False,
    top_k: Annotated[int, Option(help="추천할 상위 공고 수")] = 10,
):
    """프로필과 채용 공고 매칭 후 추천 공고를 Issue 코멘트로 전달

    Examples:
        # 특정 프로필 매칭
        python -m src.main match-profiles 1

        # 모든 프로필 매칭
        python -m src.main match-profiles --all
    """
    console.print("[bold blue]프로필 매칭 시작...[/]")

    async def run():
        from src.services.embedding_service import SentenceTransformerEmbedding
        from src.services.matching_service import ProfileMatcher
        from src.services.github_service import GitHubService
        from src.notifiers.github_notifier import GitHubNotifier

        config = get_config()

        # 서비스 초기화
        github_service = GitHubService(token=config.github_token)
        embedding_service = SentenceTransformerEmbedding()
        matcher = ProfileMatcher()
        notifier = GitHubNotifier(github_service)

        # 1. 프로필 로드
        console.print("[cyan]GitHub Issues에서 프로필 로드 중...[/]")
        issues = await github_service.get_profile_issues()
        profiles = []
        for issue in issues:
            profile = github_service.parse_issue_to_profile(issue)
            if profile:
                if issue_number and str(profile.id) != str(issue_number):
                    continue
                profiles.append(profile)

        if not profiles:
            console.print("[yellow]등록된 프로필이 없습니다.[/]")
            return

        if not all_profiles and not issue_number:
            console.print("[yellow]프로필 Issue 번호를 지정하거나 --all 옵션을 사용하세요.[/]")
            return

        console.print(f"  프로필 {len(profiles)}개 로드됨")

        # 2. 채용 공고 로드
        console.print("[cyan]채용 공고 로드 중...[/]")
        with open(config.jobs_json_path, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)

        jobs = [JobPosting(**j) for j in jobs_data.get("jobs", [])]
        jobs_map = {j.id: j for j in jobs}
        console.print(f"  채용 공고 {len(jobs)}개 로드됨")

        # 3. 채용 공고 임베딩 로드
        if not embedding_service.embeddings_exist("jobs"):
            console.print("[yellow]채용 공고 임베딩이 없습니다. update-embeddings를 먼저 실행하세요.[/]")
            return

        job_ids, job_emb_arr = embedding_service.load_embeddings("jobs")
        job_embeddings = dict(zip(job_ids, job_emb_arr.tolist()))

        # 4. 매칭 실행
        console.print("[cyan]매칭 실행 중...[/]")
        for profile in profiles:
            console.print(f"\n[bold cyan]#{profile.id} @{profile.github_username} 매칭 중...[/]")

            # 프로필 임베딩
            profile_texts = [profile.to_embedding_text()]
            profile_embeddings = await embedding_service.embed_batch(profile_texts)
            profile.embedding = profile_embeddings[0]

            # 매칭
            matches = matcher.match_profile_to_jobs(profile, jobs, job_embeddings)
            matches = matches[:top_k]

            if matches:
                # 매칭 결과 테이블
                match_table = Table(title="매칭 결과", show_header=True, header_style="bold")
                match_table.add_column("회사", style="cyan")
                match_table.add_column("포지션", style="white")
                match_table.add_column("매칭률", style="green")
                match_table.add_column("URL", style="blue")

                for match in matches[:5]:
                    job = jobs_map.get(match.job_id)
                    if job:
                        match_table.add_row(
                            job.company_name[:15],
                            job.title[:25] + "..." if len(job.title) > 25 else job.title,
                            f"{match.total_score:.0f}%",
                            job.source_url[:40] + "..." if len(job.source_url) > 40 else job.source_url
                        )

                console.print(match_table)

                # GitHub Issue 코멘트 작성
                comment = notifier.format_match_comment(matches, jobs_map)
                success = await notifier.notify(profile.id, "매칭 결과", comment)

                if success:
                    console.print(f"  [green]Issue #{profile.id}에 추천 공고 코멘트 완료[/]")
                else:
                    console.print(f"  [red]코멘트 작성 실패[/]")
            else:
                console.print(f"  [yellow]매칭된 공고가 없습니다.[/]")

        console.print("\n[bold green]매칭 완료![/]")

    asyncio.run(run())


@app.command("list-profiles")
def list_profiles():
    """등록된 프로필 목록 출력"""

    async def run():
        from src.services.github_service import GitHubService

        github_service = GitHubService()
        issues = await github_service.get_profile_issues()

        if not issues:
            console.print("[yellow]등록된 프로필이 없습니다.[/]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Issue #", style="cyan")
        table.add_column("사용자", width=15)
        table.add_column("직무", width=15)
        table.add_column("경력", justify="right")
        table.add_column("기술", width=30)

        for issue in issues:
            profile = github_service.parse_issue_to_profile(issue)
            if profile:
                table.add_row(
                    f"#{profile.id}",
                    profile.github_username,
                    profile.job_category.value,
                    f"{profile.experience_years}년",
                    ", ".join(profile.skills[:5]),
                )

        console.print(table)
        console.print(f"\n총 {len(issues)}개 프로필")

    asyncio.run(run())


@app.command("analyze-gap")
def analyze_gap(
    issue_number: Annotated[Optional[int], Argument(help="분석할 프로필 Issue 번호")] = None,
    all_profiles: Annotated[bool, Option("--all", help="모든 프로필 분석")] = False,
    top_k: Annotated[int, Option(help="분석할 상위 매칭 공고 수")] = 10,
    skip_llm: Annotated[bool, Option("--skip-llm", help="LLM 조언 생성 건너뛰기")] = False,
):
    """프로필 vs 채용 공고 갭 분석 및 커리어 조언 생성

    Groq API (Llama 3.3 70B)를 사용하여 부족한 기술 학습 로드맵,
    포트폴리오 강화 포인트, 자기소개서 키워드를 추천합니다.

    Examples:
        # 특정 프로필 분석
        python -m src.main analyze-gap 5

        # 모든 프로필 분석
        python -m src.main analyze-gap --all

        # LLM 조언 없이 갭 분석만
        python -m src.main analyze-gap 5 --skip-llm
    """
    console.print("[bold blue]갭 분석을 시작합니다...[/]")

    async def run():
        from src.services.github_service import GitHubService
        from src.services.gap_analysis_service import GapAnalyzer, GroqLLM, format_gap_analysis_comment
        from src.services.matching_service import ProfileMatcher
        from src.services.embedding_service import SentenceTransformerEmbedding

        config = get_config()

        # 서비스 초기화
        github_service = GitHubService(token=config.github_token)
        embedding_service = SentenceTransformerEmbedding()
        matcher = ProfileMatcher()

        # LLM 초기화 (skip_llm이 아닌 경우)
        llm = None
        if not skip_llm:
            if not config.groq_api_key:
                console.print("[yellow]GROQ_API_KEY가 설정되지 않았습니다. --skip-llm 옵션을 사용하세요.[/]")
                return
            llm = GroqLLM(api_key=config.groq_api_key, model=config.groq_model)

        gap_analyzer = GapAnalyzer(llm=llm)

        # 1. 프로필 로드
        console.print("[cyan]GitHub Issues에서 프로필 로드 중...[/]")
        issues = await github_service.get_profile_issues()
        profiles = []
        for issue in issues:
            profile = github_service.parse_issue_to_profile(issue)
            if profile:
                if issue_number and str(profile.id) != str(issue_number):
                    continue
                profiles.append(profile)

        if not profiles:
            console.print("[yellow]분석할 프로필이 없습니다.[/]")
            return

        if not all_profiles and not issue_number:
            console.print("[yellow]프로필 Issue 번호를 지정하거나 --all 옵션을 사용하세요.[/]")
            return

        console.print(f"  프로필 {len(profiles)}개 로드됨")

        # 2. 채용 공고 로드
        console.print("[cyan]채용 공고 로드 중...[/]")
        with open(config.jobs_json_path, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)

        jobs = [JobPosting(**j) for j in jobs_data.get("jobs", [])]
        console.print(f"  채용 공고 {len(jobs)}개 로드됨")

        # 3. 임베딩 로드
        if not embedding_service.embeddings_exist("jobs"):
            console.print("[yellow]채용 공고 임베딩이 없습니다. update-embeddings를 먼저 실행하세요.[/]")
            return

        job_ids, job_emb_arr = embedding_service.load_embeddings("jobs")
        job_embeddings = dict(zip(job_ids, job_emb_arr.tolist()))
        jobs_map = {j.id: j for j in jobs}

        # 4. 각 프로필에 대해 분석
        for profile in profiles:
            console.print(f"\n[bold cyan]#{profile.id} @{profile.github_username} 분석 중...[/]")

            # 프로필 임베딩
            profile_texts = [profile.to_embedding_text()]
            profile_embeddings = await embedding_service.embed_batch(profile_texts)
            profile.embedding = profile_embeddings[0]

            # 매칭된 상위 공고 찾기
            matches = matcher.match_profile_to_jobs(profile, jobs, job_embeddings)
            matched_jobs = [jobs_map[m.job_id] for m in matches[:top_k] if m.job_id in jobs_map]

            if not matched_jobs:
                console.print("  [yellow]매칭된 공고가 없습니다.[/]")
                continue

            console.print(f"  상위 {len(matched_jobs)}개 공고로 분석")

            # 갭 분석
            gap_result = gap_analyzer.analyze_gaps(profile, matched_jobs)

            # 갭 분석 결과 테이블
            gap_table = Table(title="갭 분석 결과", show_header=True, header_style="bold")
            gap_table.add_column("항목", style="cyan")
            gap_table.add_column("내용", style="green")

            gap_table.add_row("분석 공고 수", str(gap_result.total_jobs_analyzed))
            gap_table.add_row("필수 기술 충족률", f"{gap_result.match_coverage}%")
            gap_table.add_row("매칭된 기술", ", ".join([s.skill_name for s in gap_result.matched_skills[:5]]))
            gap_table.add_row("부족한 기술", ", ".join(gap_result.top_missing_skills))

            console.print(gap_table)

            # LLM 커리어 조언
            career_advice = None
            if not skip_llm:
                console.print("  [cyan]Groq API로 커리어 조언 생성 중...[/]")
                career_advice = await gap_analyzer.generate_career_advice(
                    profile, gap_result, matched_jobs
                )
                console.print("  [green]커리어 조언 생성 완료![/]")

                if career_advice.executive_summary:
                    console.print(f"\n  [bold]요약:[/] {career_advice.executive_summary}")

            # GitHub Issue 코멘트 작성
            comment = format_gap_analysis_comment(gap_result, career_advice)
            success = await github_service.post_comment(int(profile.id), comment)

            if success:
                console.print(f"  [green]Issue #{profile.id}에 분석 결과 코멘트 완료[/]")
            else:
                console.print(f"  [red]코멘트 작성 실패[/]")

        console.print("\n[bold green]갭 분석 완료![/]")

    asyncio.run(run())


if __name__ == "__main__":
    app()
