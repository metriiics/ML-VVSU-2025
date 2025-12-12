import argparse
import sys
import requests
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta

from parser import (
    HabrNewsParser,
    NewsVLParser,
    IXBTParser,
    NakedScienceParser,
    InterfaxParser,
)
from db import init_db, insert_article, exists_url
from config import (
    SITES_CONFIG, DEFAULT_DB_PATH, DEFAULT_USER_AGENT,
    HTTP_REQUEST_TIMEOUT, DEFAULT_PAGES, DEFAULT_ARTICLES_PER_PAGE
)


def fetch_html(url: str, headers: Optional[Dict] = None) -> Optional[str]:
    """Загружает HTML страницы"""
    try:
        default_headers = {'User-Agent': DEFAULT_USER_AGENT}
        if headers:
            default_headers.update(headers)
        
        response = requests.get(url, headers=default_headers, timeout=HTTP_REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}", file=sys.stderr)
        return None


def parse_site(
    parser_instance,
    list_urls: List[str],
    max_pages: int = 1,
    max_articles_per_page: int = 10,
    db_conn=None
) -> int:
    """Парсит сайт и сохраняет статьи в БД"""
    parsed_count = 0
    saved_count = 0
    
    for page_num, list_url in enumerate(list_urls[:max_pages], 1):
        print(f"\nПарсинг страницы {page_num}: {list_url}")
        
        html = fetch_html(list_url)
        if not html:
            print(f"Не удалось загрузить страницу {list_url}")
            continue
        
        # список статей
        articles_meta = parser_instance.parse_list_page(html)
        print(f"Найдено статей на странице: {len(articles_meta)}")
        
        # Ограничиваем количество статей
        articles_meta = articles_meta[:max_articles_per_page]
        
        for i, meta in enumerate(articles_meta, 1):
            url = meta.get('url')
            if not url:
                continue
            
            # проверка exists
            if db_conn and exists_url(db_conn, url):
                print(f"  [{i}/{len(articles_meta)}] Пропущена (уже есть): {meta.get('title', '')[:60]}")
                continue
            
            print(f"  [{i}/{len(articles_meta)}] Парсинг: {meta.get('title', '')[:60]}")
            
            # грузим статью
            article_html = fetch_html(url)
            if not article_html:
                print(f"    Не удалось загрузить статью")
                continue
            
            #  полный текст статьи
            article_data = parser_instance.parse_article_page(article_html, meta)
            if not article_data:
                print(f"    Не удалось извлечь контент")
                continue
            
            parsed_count += 1
            
            if db_conn:
                article_id = insert_article(db_conn, article_data)
                if article_id:
                    saved_count += 1
                    print(f"    ✓ Сохранено (ID: {article_id})")
                else:
                    print(f"    ✗ Не удалось сохранить (дубликат или ошибка)")
            else:
                print(f"    ✓ Распарсено (БД не подключена)")
    
    return saved_count if db_conn else parsed_count


def main():
    parser = argparse.ArgumentParser(description='Парсер новостей')
    parser.add_argument(
        '--site',
        choices=['habr', 'newsvl', 'ixbt', 'naked-science', 'interfax', 'all'],
        default='all',
        help='Какой сайт парсить (по умолчанию: all)'
    )
    parser.add_argument(
        '--pages',
        type=int,
        default=DEFAULT_PAGES,
        help=f'Количество страниц для парсинга (по умолчанию: {DEFAULT_PAGES})'
    )
    parser.add_argument(
        '--articles-per-page',
        type=int,
        default=DEFAULT_ARTICLES_PER_PAGE,
        help=f'Максимальное количество статей на странице (по умолчанию: {DEFAULT_ARTICLES_PER_PAGE})'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=None,
        help=f'Путь к файлу БД (по умолчанию: {DEFAULT_DB_PATH})'
    )
    
    args = parser.parse_args()
    
    # Инициализируем БД
    db_conn = None
    db_path = args.db if args.db else DEFAULT_DB_PATH
    if not args.dry_run:
        print(f"Инициализация БД: {db_path}")
        db_conn = init_db(db_path)
        print("БД инициализирована")
    else:
        print("Режим dry-run: данные не будут сохранены в БД")
    
    # Конфигурация парсеров
    parsers = {
        'habr': HabrNewsParser(),
        'newsvl': NewsVLParser(),
        'ixbt': IXBTParser(),
        'naked-science': NakedScienceParser(),
        'interfax': InterfaxParser()
    }
    
    def get_urls(site_name, max_pages):
        config = SITES_CONFIG[site_name]
        if site_name == 'interfax':
            urls = []
            today = datetime.now()
            for i in range(max_pages):
                date = today - timedelta(days=i)
                urls.append(f"{config['base_url']}{date.strftime('%Y/%m/%d')}/")
            return urls
        urls = [config['base_url']]
        for i in range(2, max_pages + 1):
            urls.append(config['base_url'] + config['page_pattern'].format(i=i))
        return urls
    
    
    sites_to_parse = list(SITES_CONFIG.keys()) if args.site == 'all' else [args.site]
    
    total_saved = 0
    for site_name in sites_to_parse:
        if site_name not in SITES_CONFIG:
            print(f"Неизвестный сайт: {site_name}", file=sys.stderr)
            continue
        
        print(f"\n{'='*60}")
        print(f"Парсинг сайта: {site_name}")
        print(f"{'='*60}")
        
        saved = parse_site(
            parsers[site_name],
            get_urls(site_name, args.pages),
            max_pages=args.pages,
            max_articles_per_page=args.articles_per_page,
            db_conn=db_conn
        )
        total_saved += saved
        print(f"\nОбработано статей: {saved}")
    
    print(f"\n{'='*60}")
    print(f"Всего сохранено статей: {total_saved}")
    print(f"{'='*60}")
    
    if db_conn:
        db_conn.close()


if __name__ == '__main__':
    main()
