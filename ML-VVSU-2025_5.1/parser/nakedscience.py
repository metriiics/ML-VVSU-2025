from .base import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from cleaner import clean_text_from_html
import uuid
from dateutil import parser as dtparser
import re
from config import (
    SITES_CONFIG, MIN_TEXT_LENGTH, ELEMENTS_TO_REMOVE, ARTICLE_SELECTORS,
    MIN_DESCRIPTION_LENGTH, MIN_NORMALIZED_LINE_LENGTH,
    TITLE_MATCH_MIN_WORDS, TITLE_MATCH_THRESHOLD
)

class NakedScienceParser(BaseParser):
    """Парсер для naked-science.ru"""

    def parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'lxml')
        articles = soup.select('.news-item')
        items = []

        if not articles:
            return items

        for article in articles:
            try:
                title_elem = article.select_one('.news-item-title h3 a') or article.select_one('.news-item-title a')
                if not title_elem:
                    continue

                url = title_elem.get("href", "")
                if url and not url.startswith('http'):
                    url = f"{SITES_CONFIG['naked-science']['domain']}{url}"
                title = title_elem.get_text(strip=True)

                title = re.sub(r'\s*<span[^>]*>.*?</span>\s*', '', title, flags=re.DOTALL)
                title = re.sub(r'\s*\d+\.\d+\s*$', '', title).strip()

                # дата публикации
                date_elem = article.select_one('.echo_date')
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
        
        #  основной контент статьи
        body = None
        for selector in ARTICLE_SELECTORS['naked-science']:
            body = soup.select_one(selector)
            if body:
                break
        
        if not body:
            return None

        # Удаляем навигацию, метаданные и рекламу
        for elem in body.select(', '.join(ELEMENTS_TO_REMOVE + ['.ads_single', '.ads', '[class*="ads"]', '[class*="ad"]'])):
            elem.decompose()
        
        paragraphs = []
        for p in body.find_all('p'):
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > MIN_TEXT_LENGTH:
                paragraphs.append(text)
        
        description = '\n\n'.join(paragraphs)

        if not description or len(description.strip()) < MIN_DESCRIPTION_LENGTH:
            return None

        #  дубликат
        title = meta.get("title", "")
        if title:
            title_normalized = re.sub(r'\s+', ' ', title.lower().strip())
            lines = description.split('\n')
            cleaned_lines = []
            title_found = False
            for line in lines[:3]:  
                line_normalized = re.sub(r'\s+', ' ', line.lower().strip())
                if not title_found and len(line_normalized) > MIN_NORMALIZED_LINE_LENGTH:
                    title_words = set(title_normalized.split())
                    line_words = set(line_normalized.split())
                    if title_words and len(title_words & line_words) >= min(TITLE_MATCH_MIN_WORDS, len(title_words) * TITLE_MATCH_THRESHOLD):
                        title_found = True
                        continue
                cleaned_lines.append(line)
            cleaned_lines.extend(lines[3:])
            description = '\n'.join(cleaned_lines).strip()

        #  рейтинг статьи
        rating = meta.get("rating")
        rating_elem = soup.select_one('.index_importance_news')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            match = re.search(r'(\d+\.?\d*)', rating_text)
            if match:
                try:
                    rating = float(match.group(1))
                except:
                    pass

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
            '[id*="comment"] [class*="count"]',
            '[id*="comment"] [class*="counter"]'
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
            "rating": rating,
        }
