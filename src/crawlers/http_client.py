"""
HTTP 클라이언트

단일 책임: HTTP 요청 처리
"""
import asyncio
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger

from src.core.config import CrawlerConfig, get_config
from src.core.interfaces import HttpClientProtocol


class AioHttpClient(HttpClientProtocol):
    """aiohttp 기반 HTTP 클라이언트

    HTTP 요청을 처리하는 클라이언트 구현체.
    요청 간 대기 시간, 타임아웃 등을 관리합니다.
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        Args:
            config: 크롤러 설정. None이면 기본 설정 사용.
        """
        self._config = config or get_config().crawler
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "AioHttpClient":
        """컨텍스트 매니저 진입"""
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self._config.user_agent},
            timeout=aiohttp.ClientTimeout(total=self._config.request_timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료"""
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def delay_seconds(self) -> float:
        """요청 간 대기 시간 (초)"""
        return self._config.request_delay_seconds

    async def get(self, url: str, **kwargs) -> Optional[str]:
        """GET 요청 (HTML 응답)

        Args:
            url: 요청 URL
            **kwargs: aiohttp 추가 옵션

        Returns:
            응답 본문 문자열 또는 None (실패 시)
        """
        if not self._session:
            raise RuntimeError("HTTP client not initialized. Use async with statement.")

        try:
            await asyncio.sleep(self.delay_seconds)
            async with self._session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"HTTP GET 실패: {url} (status={response.status})")
                return None
        except asyncio.TimeoutError:
            logger.error(f"HTTP GET 타임아웃: {url}")
            return None
        except Exception as e:
            logger.error(f"HTTP GET 오류: {url} - {e}")
            return None

    async def get_json(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """GET 요청 (JSON 응답)

        Args:
            url: 요청 URL
            **kwargs: aiohttp 추가 옵션

        Returns:
            JSON 딕셔너리 또는 None (실패 시)
        """
        if not self._session:
            raise RuntimeError("HTTP client not initialized. Use async with statement.")

        try:
            await asyncio.sleep(self.delay_seconds)
            async with self._session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                logger.warning(f"HTTP GET JSON 실패: {url} (status={response.status})")
                return None
        except asyncio.TimeoutError:
            logger.error(f"HTTP GET JSON 타임아웃: {url}")
            return None
        except Exception as e:
            logger.error(f"HTTP GET JSON 오류: {url} - {e}")
            return None

    async def post(self, url: str, data: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """POST 요청

        Args:
            url: 요청 URL
            data: 요청 데이터
            **kwargs: aiohttp 추가 옵션

        Returns:
            JSON 응답 딕셔너리 또는 None (실패 시)
        """
        if not self._session:
            raise RuntimeError("HTTP client not initialized. Use async with statement.")

        try:
            await asyncio.sleep(self.delay_seconds)
            async with self._session.post(url, json=data, **kwargs) as response:
                if response.status in (200, 201):
                    return await response.json()
                logger.warning(f"HTTP POST 실패: {url} (status={response.status})")
                return None
        except asyncio.TimeoutError:
            logger.error(f"HTTP POST 타임아웃: {url}")
            return None
        except Exception as e:
            logger.error(f"HTTP POST 오류: {url} - {e}")
            return None
