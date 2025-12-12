from .base import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from cleaner import clean_text_from_html
import uuid
from dateutil import parser as dtparser
import re
from config import SITES_CONFIG, MIN_TEXT_LENGTH, MIN_DESCRIPTION_LENGTH

class NewsVLParser(BaseParser):
    """Парсер для newsvl.ru"""

    def parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        container = soup.select_one('.story-list_default') or soup.select_one('.story-list')
        items = []

        if not container:
            return items

        for article in container.select('.story-list__item'):
            try:
                title_elem = article.select_one('.story-list__item-title a')
                if not title_elem:
                    continue

                url = title_elem.get("href", "")
                if url and not url.startswith('http'):
                    url = f"{SITES_CONFIG['newsvl']['domain']}{url}"
                title = title_elem.get_text(strip=True)

                # дата 
                date_elem = article.select_one('.story-list__item-date')
                published = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    try:
                        published = dtparser.parse(date_text, dayfirst=True, fuzzy=True).isoformat()
                    except:
                        published = date_text

                items.append({
                    "title": title,
                    "url": url,
                    "published_at": published,
                    "comments_count": None,
                    "rating": None
                })

            except Exception:
                continue

        return items

    def parse_article_page(self, html: str, meta: Dict) -> Optional[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        #  основной текст статьи 
        body = soup.select_one('.story__text')

        if not body:
            return None

        paragraphs = []
        for p in body.find_all('p'):
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > MIN_TEXT_LENGTH:
                paragraphs.append(text)
        
        description = '\n\n'.join(paragraphs)

        if not description or len(description.strip()) < MIN_DESCRIPTION_LENGTH:
            return None

        #  количество комментариев  статьи
        comments_count = meta.get("comments_count")
        comments_selectors = [
            '[class*="comment"] [class*="count"]',
            '[class*="comment"] [class*="counter"]',
            '[class*="comment"] [class*="num"]',
            '[data-comments-count]',
            '.comments-count',
            '.comment-count',
            '[class*="comments"]',
            '.story__comments-count'
        ]
        for selector in comments_selectors:
            comments_el = soup.select_one(selector)
            if comments_el:
                text = comments_el.get_text(strip=True)
                numbers = re.findall(r'\d+', text)
                if numbers:
                    try:
                        comments_count = int(numbers[0])
                        break
                    except:
                        pass

        return {
            "guid": str(uuid.uuid4()),
            "title": meta.get("title"),
            "description": description,
            "url": meta.get("url"),
            "published_at": meta.get("published_at"),
            "comments_count": comments_count,
            "rating": meta.get("rating"),
        }
