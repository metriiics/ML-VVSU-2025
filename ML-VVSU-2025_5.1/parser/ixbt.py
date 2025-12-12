from .base import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import uuid
from dateutil import parser as dtparser
from datetime import datetime
import re
from config import SITES_CONFIG, MIN_TEXT_LENGTH, ELEMENTS_TO_REMOVE, MIN_TITLE_LENGTH

class IXBTParser(BaseParser):
    """Парсер для ixbt.games"""

    def parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        links = soup.select('a[href*="/news/"]') or soup.select('a[href*="/article/"]')
        if not links:
            return []

        items = []
        seen_urls = set()
        for link in links:
            try:
                url = link.get("href")
                if not url or url in seen_urls:
                    continue
                
                if url.startswith('/'):
                    url = f"{SITES_CONFIG['ixbt']['domain']}{url}"
                elif not url.startswith('http'):
                    continue
                seen_urls.add(url)

                # дата из URL
                published = None
                url_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
                if url_match:
                    try:
                        published = datetime(*map(int, url_match.groups())).isoformat()
                    except:
                        pass

                # title
                card = link.find_parent(class_=re.compile(r'card', re.I))
                title_elem = (card or link).select_one('h3')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if len(title) < MIN_TITLE_LENGTH:
                    continue

                items.append({
                    "title": title,
                    "url": url,
                    "published_at": published,
                    "comments_count": None,
                    "rating": None
                })
            except:
                continue
        return items

    def parse_article_page(self, html: str, meta: Dict) -> Optional[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        body = soup.select_one('article') or soup.select_one('[class*="article-content"]') or soup.select_one('main')
        if not body:
            return None

        # del лишние элементы
        for elem in body.select(', '.join(ELEMENTS_TO_REMOVE + ['ul', 'ol'])):
            elem.decompose()

        # текст из параграфов
        paragraphs = []
        for p in body.find_all('p'):
            if p.find_parent(['ul', 'ol']):
                continue
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > MIN_TEXT_LENGTH:
                paragraphs.append(text)
        
        description = '\n\n'.join(paragraphs)
        if not description or len(description.strip()) < MIN_TEXT_LENGTH:
            return None

        # кол-во Комментарии
        comments_count = meta.get("comments_count")
        h2_comments = soup.find('h2', string=re.compile(r'Комментарии', re.I))
        if h2_comments:
            text = h2_comments.get_text(strip=True)

            match = re.search(r'\((\d+)\)', text)
            if match:
                try:
                    comments_count = int(match.group(1))
                except:
                    pass
        
        # если не нашли, другие селекторы
        if comments_count is None:
            for selector in ['[data-comments-count]', '[class*="comment"] [class*="count"]', '.comments-count']:
                el = soup.select_one(selector)
                if el:
                    if el.has_attr('data-comments-count'):
                        try:
                            comments_count = int(el['data-comments-count'])
                            break
                        except:
                            pass
                    numbers = re.findall(r'\d+', el.get_text(strip=True))
                    if numbers:
                        try:
                            comments_count = int(numbers[0])
                            break
                        except:
                            pass

        # дата
        published_at = meta.get("published_at")
        if not published_at:
            url_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', meta.get("url", ""))
            if url_match:
                try:
                    published_at = datetime(*map(int, url_match.groups())).isoformat()
                except:
                    pass
            if not published_at:
                date_elem = soup.select_one('time[datetime]') or soup.select_one('[datetime]')
                if date_elem and date_elem.has_attr('datetime'):
                    try:
                        published_at = dtparser.isoparse(date_elem['datetime']).isoformat()
                    except:
                        pass

        return {
            "guid": str(uuid.uuid4()),
            "title": meta.get("title"),
            "description": description,
            "url": meta.get("url"),
            "published_at": published_at,
            "comments_count": comments_count,
            "rating": meta.get("rating"),
        }
