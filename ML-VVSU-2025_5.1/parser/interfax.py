from .base import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from cleaner import clean_text_from_html
import uuid
from dateutil import parser as dtparser
from datetime import datetime
import re
from config import SITES_CONFIG, MIN_TEXT_LENGTH, ELEMENTS_TO_REMOVE, MIN_DESCRIPTION_LENGTH

class InterfaxParser(BaseParser):
    """Парсер для interfax.ru"""

    def parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        container = soup.select_one('.an')
        items = []

        if not container:
            return items

        #  дат
        date_from_page = None
        date_script = soup.find('script', string=re.compile(r'data_date'))
        if date_script:
            match = re.search(r'data_date="(\d{4}-\d{2}-\d{2})"', date_script.string)
            if match:
                date_from_page = match.group(1)

        for article_div in container.select('div[data-id]'):
            try:
                link = article_div.select_one('a[href]')
                if not link:
                    continue

                url = link.get("href", "")
                if url and not url.startswith('http'):
                    url = f"{SITES_CONFIG['interfax']['domain']}{url}"

                title_elem = link.select_one('h3')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)

                # дата публикации
                time_elem = article_div.select_one('span')
                published = None
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    if date_from_page and re.match(r'\d{2}:\d{2}', time_text):
                        try:
                            full_datetime = f"{date_from_page} {time_text}"
                            published = dtparser.parse(full_datetime, dayfirst=False).isoformat()
                        except:
                            published = time_text
                    else:
                        published = time_text

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
        body = soup.select_one('.textMTitle') \
               or soup.select_one('.articleText') \
               or soup.select_one('article')

        if not body:
            return None

        for elem in body.select(', '.join(ELEMENTS_TO_REMOVE)):
            elem.decompose()

        paragraphs = []
        for p in body.find_all(['p', 'div']):
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > MIN_TEXT_LENGTH:
                paragraphs.append(text)
        
        description = '\n\n'.join(paragraphs)

        if not description or len(description.strip()) < MIN_DESCRIPTION_LENGTH:
            return None

        #  кол-во комментариев  статьи
        comments_count = meta.get("comments_count")
        comments_selectors = [
            '[class*="comment"] [class*="count"]',
            '[class*="comment"] [class*="counter"]',
            '[class*="comment"] [class*="num"]',
            '[data-comments-count]',
            '.comments-count',
            '.comment-count',
            '[class*="comments"]'
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
