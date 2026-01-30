"""
Generated DAG: pipeline__recruitment_auto

================================================================================
👶 어린이를 위한 100% 이해 가능 설명서 (Kindergarten Guide) 👶
================================================================================

안녕! 이 파일은 "채용 공고 배달 로봇 지도"예요.
매일 아침 9시마다 로봇 친구들이 깨어나서 일을 시작해요.

우리가 하려는 일은 4단계예요:
1. 🕵️ **공고 수집 (crawl_jobs_to_json)**: "새로운 일자리 없나?" 하고 탐정 로봇이 인터넷을 뒤져서 가져와요.
2. 🧠 **공부 하기 (update_job_embeddings)**: "이건 어떤 일이지?" 하고 똑똑한 로봇이 공고 내용을 공부해서 머릿속에 정리해요.
3. 🏭 **홈페이지 짓기 (build_static_site)**: 사람들이 볼 수 있게 예쁜 홈페이지를 만들어요.
4. 📬 **편지 보내기 (match_and_notify_users)**: "여기 딱 맞는 일자리가 있어요!" 하고 기다리던 사람들에게 알려줘요.

자, 이제 로봇들을 만나볼까요?
"""
from airflow import DAG
import pendulum
from datetime import datetime, timedelta
from airflow.providers.standard.operators.python import PythonOperator
import sys
import os

# Import Wrapper Functions
# 로봇들이 실제로 할 일을 적어둔 책(라이브러리)을 가져와요.
try:
    from src.pipeline_wrappers import (
        run_crawl_json,
        run_update_embeddings,
        run_build_static,
        run_match_profiles,
    )
except ImportError:
    # 로컬 개발 환경이나 테스트를 위해 Mock 함수를 준비했어요.
    print("Warning: src.pipeline_wrappers not found. Using mocks.")
    run_crawl_json = lambda: print("Mock: Crawling jobs...")
    run_update_embeddings = lambda: print("Mock: Updating embeddings...")
    run_build_static = lambda: print("Mock: Building site...")
    run_match_profiles = lambda **kwargs: print("Mock: Matching profiles...")


# Default arguments
# 로봇들의 기본 약속이에요.
default_args = {
    "owner": "geon_yul",
    "retries": 1,                      # 실수하면 1번 더 해봐요.
    "retry_delay": timedelta(seconds=600), # 10분 쉬었다가 다시 해요.
}

# Pipeline Definition
# "채용 공고 배달" 지도를 펼칩니다!
with DAG(
    dag_id="pipeline__recruitment_auto",
    default_args=default_args,
    schedule="0 9 * * *",              # 매일 아침 9시에 알람이 울려요!
    catchup=False,
    tags=["recruitment", "automation"],
) as dag:

    # ==========================================================================
    # 1. 공고 수집 탐정 (Crawler)
    # ==========================================================================
    crawl_jobs_to_json = PythonOperator(
        task_id="crawl_jobs_to_json",
        python_callable=run_crawl_json,
        doc_md="""
        ### 🕵️ 공고 수집
        인터넷에서 채용 공고를 긁어와서 `jobs.json` 파일로 만들어요.
        """,
    )

    # ==========================================================================
    # 2. 똑똑한 공부벌레 (Embedding)
    # ==========================================================================
    update_job_embeddings = PythonOperator(
        task_id="update_job_embeddings",
        python_callable=run_update_embeddings,
        doc_md="""
        ### 🧠 임베딩 업데이트
        새로 가져온 공고를 잘 검색할 수 있게 숫자로 변환(Vectorizing)해요.
        """,
    )

    # ==========================================================================
    # 3. 홈페이지 건축가 (Builder)
    # ==========================================================================
    build_static_site = PythonOperator(
        task_id="build_static_site",
        python_callable=run_build_static,
        doc_md="""
        ### 🏭 정적 사이트 빌드
        GitHub Pages에 올릴 웹사이트 파일들을 만들어요.
        """,
    )

    # ==========================================================================
    # 4. 우편 배달부 (Notifier)
    # ==========================================================================
    match_and_notify_users = PythonOperator(
        task_id="match_and_notify_users",
        python_callable=run_match_profiles,
        op_kwargs={"all_profiles": True}, # "모든 사람에게 다 알려줘!" 라고 주문했어요.
        doc_md="""
        ### 📬 매칭 및 알림
        사람들의 프로필과 공고를 비교해서 딱 맞는 걸 찾아서 Issue 댓글을 달아줘요.
        """,
    )

    # ==========================================================================
    # 5. 순서 정하기 (Dependencies)
    # ==========================================================================
    
    # 순서대로 착착착!
    # 수집 -> 공부 -> (홈페이지 만들기, 편지 보내기) 
    
    crawl_jobs_to_json >> update_job_embeddings
    
    update_job_embeddings >> build_static_site
    update_job_embeddings >> match_and_notify_users
