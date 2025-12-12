from .base import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from cleaner import clean_text_from_html
import uuid
from dateutil import parser as dtparser
import re
from config import (
    SITES_CONFIG, MIN_TEXT_LENGTH, META_KEYWORDS, ELEMENTS_TO_REMOVE,
    MIN_DESCRIPTION_LENGTH
)


class HabrNewsParser(BaseParser):

    def parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        container = soup.select_one('.tm-articles-list')
        items = []

        if not container:
            return items

        for article in container.select('.tm-articles-list__item'):
            try:
                a = article.select_one('.tm-title__link')
                if not a:
                    continue

                url = a.get("href", "")
                if url and not url.startswith('http'):
                    url = f"{SITES_CONFIG['habr']['domain']}{url}"
                title = a.get_text(strip=True)

                # publish date
                time_el = article.select_one("time")
                published = None
                if time_el and time_el.has_attr("datetime"):
                    try:
                        published = dtparser.isoparse(time_el["datetime"]).isoformat()
                    except:
                        published = time_el.get_text(strip=True)

                # comments
                comments_el = article.select_one('[data-test-id="counter-comments"] .tm-comments-counter__value')
                comments_count = None
                if comments_el:
                    text = comments_el.get_text(strip=True)
                    comments_count = int(text) if text.isdigit() else None

                # rating (лайки)
                rating_el = article.select_one('[data-test-id="votes-meter-value"]')
                rating = None
                if rating_el:
                    txt = rating_el.get_text(strip=True)
                    num = re.sub(r"[^\d-]", "", txt)
                    if num:
                        try:
                            rating = int(num)
                        except:
                            rating = None

                items.append({
                    "title": title,
                    "url": url,
                    "published_at": published,
                    "comments_count": comments_count,
                    "rating": rating
                })

            except Exception:
                continue

        return items

    def parse_article_page(self, html: str, meta: Dict) -> Optional[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        # Ищем основной контент статьи
        body = soup.select_one('.tm-article-presenter__content') \
               or soup.select_one('.article-formatted-body') \
               or soup.select_one('article')

        if not body:
            return None
        
        for elem in body.select(', '.join(ELEMENTS_TO_REMOVE)):
            elem.decompose()

        # извлек. текст из параграфов
        paragraphs = []
        seen_texts = set()
        
        for p in body.find_all('p'):
            text = p.get_text(separator=' ', strip=True)
            if not text or len(text) < MIN_TEXT_LENGTH:
                continue
            
            # пропуск метаданных
            text_lower = text.lower()
            if any(kw in text_lower for kw in META_KEYWORDS):
                continue
            
            # дубликаты
            normalized = re.sub(r'\s+', ' ', text).strip().lower()
            if normalized in seen_texts:
                continue
            
            seen_texts.add(normalized)
            paragraphs.append(text)
        
        description = '\n\n'.join(paragraphs)

        if not description or len(description.strip()) < MIN_DESCRIPTION_LENGTH:
            return None

        #  кол-во комментариев  статьи
        comments_count = meta.get("comments_count")  
        comments_el = soup.select_one('[data-test-id="counter-comments"] .value') \
                      or soup.select_one('.article-comments-counter-link .value')
        if comments_el:
            text = comments_el.get_text(strip=True)
            if text.isdigit():
                comments_count = int(text)

        #  рейтинг  статьи
        rating = meta.get("rating") 
        rating_el = soup.select_one('[data-test-id="votes-meter-value"]')
        if rating_el:
            txt = rating_el.get_text(strip=True)
            num = re.sub(r"[^\d-]", "", txt)
            if num:
                try:
                    rating = int(num)
                except:
                    pass

        return {
            "guid": str(uuid.uuid4()),
            "title": meta.get("title"),
            "description": description,
            "url": meta.get("url"),
            "published_at": meta.get("published_at"),
            "comments_count": comments_count,
            "rating": rating,
        }
