# parsers/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import uuid
import time
from config import DEFAULT_RATE_LIMIT_PER_SEC, DEFAULT_USER_AGENTS

class BaseParser(ABC):
    """
    Базовый абстрактный класс парсера
    """

    def __init__(self, rate_limit_per_sec: float = None, user_agents: Optional[List[str]] = None):
        self.rate_limit_per_sec = rate_limit_per_sec if rate_limit_per_sec is not None else DEFAULT_RATE_LIMIT_PER_SEC
        self._last_request_ts = 0.0
        self.user_agents = user_agents or DEFAULT_USER_AGENTS

    def _wait_rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_ts
        min_interval = 1.0 / max(self.rate_limit_per_sec, 1e-6)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    def _mark_request(self):
        self._last_request_ts = time.time()

    @abstractmethod
    def parse_list_page(self, html: str) -> List[Dict]:
        """
        Парсит страницу со списком новостей.
        Возвращает список dict:
            {'title': str, 'url': str, 'published_at': str_or_datetime, 'comments_count': int_or_None, 'rating': int_or_None, 'guid_source_id': maybe}
        """
        raise NotImplementedError

    @abstractmethod
    def parse_article_page(self, html: str, meta: Dict) -> Optional[Dict]:
        """
        Парсит страницу самой статьи.
           title, description, url, published_at, comments_count, rating, guid
        """
        raise NotImplementedError
