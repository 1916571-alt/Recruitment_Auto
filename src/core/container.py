"""
의존성 주입 컨테이너

런타임에 의존성을 관리하고 주입하는 컨테이너.
"""
from typing import Dict, List, Optional, Type, TypeVar

from loguru import logger

from .config import AppConfig, get_config
from .interfaces import (
    CrawlerProtocol,
    ExporterProtocol,
    FilterProtocol,
    NotifierProtocol,
)


T = TypeVar("T")


class Container:
    """의존성 주입 컨테이너

    싱글톤 패턴으로 구현되어 애플리케이션 전체에서 동일한 인스턴스를 공유합니다.

    사용 예시:
        ```python
        container = Container()

        # 크롤러 등록
        container.register_crawler(SaraminCrawler)
        container.register_crawler(InthisworkCrawler)

        # 크롤러 조회
        crawlers = container.get_crawlers()
        ```
    """

    _instance: Optional["Container"] = None

    def __new__(cls) -> "Container":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config: AppConfig = get_config()
        self._crawler_classes: List[Type[CrawlerProtocol]] = []
        self._filter: Optional[FilterProtocol] = None
        self._exporter: Optional[ExporterProtocol] = None
        self._notifiers: Dict[str, NotifierProtocol] = {}
        self._initialized = True

        logger.debug("Container initialized")

    @property
    def config(self) -> AppConfig:
        """설정 인스턴스"""
        return self._config

    # === 크롤러 관리 ===

    def register_crawler(self, crawler_class: Type[CrawlerProtocol]) -> None:
        """크롤러 클래스 등록

        Args:
            crawler_class: 등록할 크롤러 클래스
        """
        if crawler_class not in self._crawler_classes:
            self._crawler_classes.append(crawler_class)
            logger.debug(f"Crawler registered: {crawler_class.__name__}")

    def get_crawler_classes(self) -> List[Type[CrawlerProtocol]]:
        """등록된 크롤러 클래스 목록 반환"""
        return self._crawler_classes.copy()

    def create_crawlers(self) -> List[CrawlerProtocol]:
        """등록된 크롤러 인스턴스 생성

        Returns:
            크롤러 인스턴스 리스트
        """
        return [cls() for cls in self._crawler_classes]

    # === 필터 관리 ===

    def register_filter(self, filter_instance: FilterProtocol) -> None:
        """필터 인스턴스 등록

        Args:
            filter_instance: 등록할 필터 인스턴스
        """
        self._filter = filter_instance
        logger.debug(f"Filter registered: {type(filter_instance).__name__}")

    def get_filter(self) -> Optional[FilterProtocol]:
        """등록된 필터 인스턴스 반환"""
        return self._filter

    # === 내보내기 관리 ===

    def register_exporter(self, exporter_instance: ExporterProtocol) -> None:
        """내보내기 인스턴스 등록

        Args:
            exporter_instance: 등록할 내보내기 인스턴스
        """
        self._exporter = exporter_instance
        logger.debug(f"Exporter registered: {type(exporter_instance).__name__}")

    def get_exporter(self) -> Optional[ExporterProtocol]:
        """등록된 내보내기 인스턴스 반환"""
        return self._exporter

    # === 알림 관리 ===

    def register_notifier(self, name: str, notifier_instance: NotifierProtocol) -> None:
        """알림 인스턴스 등록

        Args:
            name: 알림기 이름 (예: "email", "github")
            notifier_instance: 등록할 알림 인스턴스
        """
        self._notifiers[name] = notifier_instance
        logger.debug(f"Notifier registered: {name}")

    def get_notifier(self, name: str) -> Optional[NotifierProtocol]:
        """이름으로 알림 인스턴스 조회

        Args:
            name: 알림기 이름

        Returns:
            알림 인스턴스 또는 None
        """
        return self._notifiers.get(name)

    def get_all_notifiers(self) -> Dict[str, NotifierProtocol]:
        """모든 알림 인스턴스 반환"""
        return self._notifiers.copy()

    # === 유틸리티 ===

    def reset(self) -> None:
        """컨테이너 상태 초기화 (테스트용)"""
        self._crawler_classes.clear()
        self._filter = None
        self._exporter = None
        self._notifiers.clear()
        logger.debug("Container reset")

    @classmethod
    def reset_instance(cls) -> None:
        """싱글톤 인스턴스 초기화 (테스트용)"""
        cls._instance = None


def get_container() -> Container:
    """컨테이너 인스턴스 반환"""
    return Container()
