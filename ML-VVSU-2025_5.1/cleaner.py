from bs4 import BeautifulSoup
import re
from config import MEDIA_ELEMENTS_TO_REMOVE, MIN_CLEANER_TEXT_LENGTH, STOP_KEYWORDS

def remove_media(soup: BeautifulSoup):
    """Удаляет медиа элементы и скрипты"""
    for sel in MEDIA_ELEMENTS_TO_REMOVE:
        for el in soup.select(sel):
            el.decompose()

def clean_text_from_html(html: str) -> str:
    """Очищает HTML и возвращает текст"""
    soup = BeautifulSoup(html, 'lxml')
    remove_media(soup)
    
    # Удаляем ссылки
    for a in soup.find_all('a'):
        a.replace_with(a.get_text(separator=' '))
    
    # Удаляем метаданные
    for bad in soup.select('.tm-article-snippet__hubs, .tm-article-snippet__meta'):
        bad.decompose()
    
    #  текст из параграфов
    paragraphs = []
    seen = set()
    
    for p in soup.find_all(['p', 'div']):
        text = p.get_text(separator=' ', strip=True)
        if not text or len(text) < MIN_CLEANER_TEXT_LENGTH:
            continue
        
        #  дубликаты
        normalized = re.sub(r'\s+', ' ', text.lower()).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        
        #  метаданные
        if text.lower().startswith(tuple(STOP_KEYWORDS)):
            break
        
        paragraphs.append(text)
    
    text = '\n'.join(paragraphs).strip()
    if not text:
        text = soup.get_text(separator=' ', strip=True)
    
    return text
