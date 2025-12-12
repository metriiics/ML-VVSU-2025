# config.py
# Конфигурация и константы для парсера

# Настройки БД
DEFAULT_DB_PATH = 'articles.sqlite'

# Настройки парсинга
MIN_TEXT_LENGTH = 30
MIN_PARAGRAPH_LENGTH = 30

# Конфигурация сайтов
SITES_CONFIG = {
    'habr': {
        'base_url': 'https://habr.com/ru/news/',
        'page_pattern': 'page{i}/',
        'domain': 'https://habr.com'
    },
    'newsvl': {
        'base_url': 'https://www.newsvl.ru/',
        'page_pattern': '?page={i}',
        'domain': 'https://www.newsvl.ru'
    },
    'ixbt': {
        'base_url': 'https://ixbt.games/news',
        'page_pattern': '?page={i}',
        'domain': 'https://ixbt.games'
    },
    'naked-science': {
        'base_url': 'https://naked-science.ru/article/',
        'page_pattern': 'page/{i}/',
        'domain': 'https://naked-science.ru'
    },
    'interfax': {
        'base_url': 'https://www.interfax.ru/world/news/',
        'page_pattern': None,  
        'domain': 'https://www.interfax.ru'
    }
}

# Селекторы для извлечения контента статей
ARTICLE_SELECTORS = {
    'habr': ['.tm-article-presenter__content', '.article-formatted-body', 'article'],
    'newsvl': ['.story__text'],
    'ixbt': ['article', '[class*="article-content"]', '[class*="post-content"]', 'main'],
    'naked-science': ['.body', '.content', '.single-post .body', '.single-post .content'],
    'interfax': ['.textMTitle', '.articleText', 'article']
}

# Элементы для удаления из контента
ELEMENTS_TO_REMOVE = [
    'nav', 'header', 'script', 'style', 'ul', 'ol',
    '.tm-article-snippet', '.tm-article-snippet__meta', '.tm-article-snippet__hubs',
    '.tm-article-snippet__footer', '.tm-article-snippet__title',
    '.tm-article-snippet__read-time', '.tm-article-snippet__views-count',
    '.tm-article-snippet__tags', '.tm-article-snippet__hubs-list',
    '.social-share', '.share-buttons', '.article-meta', '.article-header',
    '.breadcrumbs', '.article-tags', '.article-author', '.textMTags', '.textMMat',
    '.list-disc', '.list-decimal', '[class*="list"]'
]

# Метаданные для фильтрации
META_KEYWORDS = [
    'время на прочтение', 'охват и читатели', 'теги:', 'хабы:', 
    'читатели', 'cutcode', 'час назад', 'релиз'
]

# Таймауты
HTTP_REQUEST_TIMEOUT = 30
DB_CONNECTION_TIMEOUT = 30

# Настройки парсинга по умолчанию
DEFAULT_PAGES = 1
DEFAULT_ARTICLES_PER_PAGE = 10

# Минимальные длины текста
MIN_DESCRIPTION_LENGTH = 20
MIN_TITLE_LENGTH = 5
MIN_CLEANER_TEXT_LENGTH = 10
MIN_NORMALIZED_LINE_LENGTH = 20

# Настройки парсера
DEFAULT_RATE_LIMIT_PER_SEC = 1.0
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# SQL схема 
DB_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    url TEXT,
    published_at TEXT,
    comments_count INTEGER,
    created_at_utc INTEGER,
    rating INTEGER
);
CREATE INDEX IF NOT EXISTS idx_guid ON articles(guid);
CREATE INDEX IF NOT EXISTS idx_published ON articles(published_at);
-- unique index on url to avoid duplicates; will be created only if possible
"""

# Медиа элементы для удаления
MEDIA_ELEMENTS_TO_REMOVE = [
    'video', 'audio', 'iframe', 'picture', 'img', 'svg', 'figure', 
    'script', 'style', 'noscript'
]

# Ключевые слова для остановки парсинга
STOP_KEYWORDS = ['теги', 'хабы', 'источник']

# Настройки для сравнения заголовков
TITLE_MATCH_MIN_WORDS = 3
TITLE_MATCH_THRESHOLD = 0.6

