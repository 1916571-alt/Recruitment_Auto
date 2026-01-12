"""
인터페이스 정의 (Protocol)

의존성 역전 원칙(DIP)을 위한 추상 인터페이스 정의.
구현체는 이 인터페이스에 의존하며, 런타임에 주입됩니다.
"""
from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from src.models import JobPosting


@runtime_checkable
class CrawlerProtocol(Protocol):
    """크롤러 인터페이스

    채용 사이트에서 공고를 수집하는 크롤러가 구현해야 할 인터페이스.
    """

    @property
    def source_name(self) -> str:
        """데이터 소스 이름"""
        ...

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 목록 크롤링

        Returns:
            수집된 채용 공고 리스트
        """
        ...

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """채용 공고 상세 정보 가져오기

        Args:
            job: 기본 정보가 담긴 JobPosting

        Returns:
            상세 정보가 추가된 JobPosting
        """
        ...


@runtime_checkable
class FilterProtocol(Protocol):
    """필터 인터페이스

    채용 공고 필터링 로직을 담당하는 인터페이스.
    """

    def matches(self, job: JobPosting) -> bool:
        """채용 공고가 필터 조건에 맞는지 확인

        Args:
            job: 확인할 채용 공고

        Returns:
            필터 조건 충족 여부
        """
        ...


@runtime_checkable
class ExporterProtocol(Protocol):
    """내보내기 인터페이스

    수집된 채용 공고를 저장/내보내기하는 인터페이스.
    """

    def export(self, jobs: List[JobPosting]) -> Path:
        """채용 공고 내보내기

        Args:
            jobs: 내보낼 채용 공고 리스트

        Returns:
            저장된 파일 경로
        """
        ...


@runtime_checkable
class NotifierProtocol(Protocol):
    """알림 인터페이스

    사용자에게 알림을 발송하는 인터페이스.
    """

    async def notify(self, recipient: str, subject: str, content: str) -> bool:
        """알림 발송

        Args:
            recipient: 수신자 (이메일, Issue ID 등)
            subject: 제목
            content: 내용

        Returns:
            발송 성공 여부
        """
        ...


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """임베딩 인터페이스

    텍스트를 벡터로 변환하는 인터페이스.
    """

    async def embed(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터
        """
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트를 배치로 임베딩

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        ...


@runtime_checkable
class MatcherProtocol(Protocol):
    """매칭 인터페이스

    프로필과 채용 공고를 매칭하는 인터페이스.
    """

    def calculate_score(self, profile_embedding: List[float], job_embedding: List[float]) -> float:
        """매칭 점수 계산

        Args:
            profile_embedding: 프로필 임베딩 벡터
            job_embedding: 채용 공고 임베딩 벡터

        Returns:
            매칭 점수 (0-100)
        """
        ...


class HttpClientProtocol(Protocol):
    """HTTP 클라이언트 인터페이스

    HTTP 요청을 처리하는 인터페이스. 테스트 시 Mock으로 대체 가능.
    """

    async def get(self, url: str, **kwargs) -> Optional[str]:
        """GET 요청

        Args:
            url: 요청 URL
            **kwargs: 추가 옵션

        Returns:
            응답 본문 또는 None
        """
        ...

    async def get_json(self, url: str, **kwargs) -> Optional[dict]:
        """GET 요청 (JSON 응답)

        Args:
            url: 요청 URL
            **kwargs: 추가 옵션

        Returns:
            JSON 응답 또는 None
        """
        ...

    async def post(self, url: str, data: dict, **kwargs) -> Optional[dict]:
        """POST 요청

        Args:
            url: 요청 URL
            data: 요청 데이터
            **kwargs: 추가 옵션

        Returns:
            JSON 응답 또는 None
        """
        ...


@runtime_checkable
class LLMProtocol(Protocol):
    """LLM 인터페이스

    텍스트 생성을 위한 대형 언어 모델 인터페이스.
    Groq, OpenAI, Anthropic 등 다양한 제공자로 구현 가능.
    """

    @property
    def model_name(self) -> str:
        """사용 중인 모델 이름"""
        ...

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 창의성 정도 (0.0-1.0)
            max_tokens: 최대 토큰 수

        Returns:
            생성된 텍스트
        """
        ...

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[dict] = None,
    ) -> dict:
        """JSON 형식 응답 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            response_schema: 응답 스키마 (JSON Schema)

        Returns:
            파싱된 JSON 딕셔너리
        """
        ...
