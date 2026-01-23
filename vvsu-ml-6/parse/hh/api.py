import asyncio
import aiohttp
import async_timeout
import logging
import json
import random
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from .utils import clear_item, clean_text

HH_API = "https://api.hh.ru"

USER_AGENTS = [
    "hh-async-parser/1.0 (+https://example.com)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
]


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict = None, timeout: int = 30, retries: int = 3):
    for attempt in range(retries):
        try:
            async with async_timeout.timeout(timeout):
                # rotate user-agent per request to reduce bot detection
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 403:
                        # possible captcha or access block
                        text = await resp.text()
                        try:
                            payload = json.loads(text)
                        except Exception:
                            payload = None

                        if payload and isinstance(payload, dict):
                            # detect captcha_required indicator
                            errs = payload.get('errors') or []
                            captcha = False
                            for e in errs:
                                if isinstance(e, dict) and e.get('value') == 'captcha_required':
                                    captcha = True
                                    break
                            if captcha:
                                backoff = min(120, 15 * (attempt + 1))
                                jitter = random.uniform(0.5, 2.0)
                                sleep_for = backoff + jitter
                                logging.warning("Captcha detected for %s; sleeping %.1fs (attempt %s)", url, sleep_for, attempt + 1)
                                await asyncio.sleep(sleep_for)
                                continue
                        # unknown 403 -> log and stop retrying this request
                        logging.error("Unexpected 403 for %s: %s", url, text[:200])
                        return None
                    elif resp.status in (429, 502, 503, 504):
                        backoff = 1 + attempt * 2
                        logging.warning("%s -> %s; retrying in %s seconds", url, resp.status, backoff)
                        await asyncio.sleep(backoff)
                    else:
                        text = await resp.text()
                        logging.error("Unexpected status %s for %s: %s", resp.status, url, text[:200])
                        return None
        except asyncio.TimeoutError:
            logging.warning("Timeout fetching %s (attempt %s)", url, attempt + 1)
            await asyncio.sleep(1 + attempt)
    logging.error("Failed to fetch %s after %s attempts", url, retries)
    return None


async def fetch_vacancy_detail(session: aiohttp.ClientSession, vacancy_id: str, sem: asyncio.Semaphore):
    url = f"{HH_API}/vacancies/{vacancy_id}"
    async with sem:
        return await fetch_json(session, url)


def build_vacancy_dict(vacancy: dict) -> Dict:
    salary = vacancy.get('salary')
    salary_range = vacancy.get('salary_range')
    address = vacancy.get('address')

    vacancy_dict: Dict = {
        'id': clear_item(vacancy.get('id')),
        'name': clean_text(vacancy.get('name')),
        'url': vacancy.get('alternate_url'),
        'salary_start': salary.get('from') if salary is not None else None,
        'salary_to': salary.get('to') if salary is not None else None,
        'currency': salary.get('currency') if salary is not None else None,
        'salary_mode': salary_range.get('mode').get('name') if salary_range is not None and salary_range.get('mode') else None,
        'experience': vacancy.get('experience', {}).get('name'),
        'employment': vacancy.get('employment', {}).get('name'),
        'employer_name': vacancy.get('employer', {}).get('name'),

        'schedule': [
            clear_item(i.get('name'))
            for i in vacancy.get('work_schedule_by_days', [])
        ],
        'working_hours': [
            clear_item(i.get('name'))
            for i in vacancy.get('working_hours', [])
        ],
        'work_format': [
            clear_item(i.get('name'))
            for i in vacancy.get('work_format', [])
        ],

        'city_vacancies': address.get('city') if address is not None else None,
        'published_at': vacancy.get('published_at'),

        'professional_roles': [
            clear_item(i.get('name'))
            for i in vacancy.get('professional_roles', [])
        ],

        'professional_roles_id': [
            clear_item(i.get('id'))
            for i in vacancy.get('professional_roles', [])
        ],

        'type': vacancy.get('type', {}).get('name'),
        'employer_trusted': vacancy.get('employer', {}).get('trusted', False),
        'premium_status': vacancy.get('premium', False),

        'description': clean_text(vacancy.get('description', '')),
        'key_skills': [clean_text(s.get('name')) for s in vacancy.get('key_skills', [])]
    }
    return vacancy_dict


async def get_areas(session: aiohttp.ClientSession) -> List[Dict]:
    """Return flattened list of areas with their id and name."""
    data = await fetch_json(session, f"{HH_API}/areas")
    result: List[Dict] = []

    def walk(node_list):
        for node in node_list:
            result.append({"id": node.get('id'), "name": node.get('name')})
            sub = node.get('areas') or []
            if sub:
                walk(sub)

    if data:
        walk(data)
    return result


def _iso_to_date(s: Optional[str]) -> date:
    if not s:
        return date.today()
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return date.today()


def _date_to_iso(d: date) -> str:
    return d.isoformat()


async def search_items_by_range(session: aiohttp.ClientSession, area: Optional[str], date_from: str, date_to: str, per_page: int = 100, archived: bool = True, depth: int = 0):
    """Async generator yielding vacancy summary items for given area and date range.

    If the API reports too many results (near the 2000 limit), the function splits
    the date range recursively to circumvent the limit.
    """
    if depth > 12:
        logging.warning("Max recursion depth reached for range %s - %s", date_from, date_to)
    params_base = {
        'per_page': per_page,
        'archived': 'true' if archived else 'false',
    }
    if area:
        params_base['area'] = area
    params_base['date_from'] = date_from
    params_base['date_to'] = date_to

    # initial probe
    probe = await fetch_json(session, f"{HH_API}/vacancies", params={**params_base, 'page': 0})
    if not probe:
        return

    found = probe.get('found', 0)
    pages = probe.get('pages', 0)

    # If near or over API hard limit, split by date range
    if found > 1800 and depth < 12:
        # compute mid date
        d_from = _iso_to_date(date_from)
        d_to = _iso_to_date(date_to)
        if d_from >= d_to:
            # can't split further; fallback to paging
            logging.warning("High result count %s for single-day range %s; paging may miss items", found, date_from)
        else:
            mid = d_from + (d_to - d_from) // 2
            left_from, left_to = _date_to_iso(d_from), _date_to_iso(mid)
            right_from, right_to = _date_to_iso(mid + timedelta(days=1)), _date_to_iso(d_to)
            logging.info("Splitting range %s-%s into %s-%s and %s-%s (found=%s)", date_from, date_to, left_from, left_to, right_from, right_to, found)
            async for item in search_items_by_range(session, area, left_from, left_to, per_page=per_page, archived=archived, depth=depth + 1):
                yield item
            async for item in search_items_by_range(session, area, right_from, right_to, per_page=per_page, archived=archived, depth=depth + 1):
                yield item
            return

    # normal paging
    for page in range(pages):
        params = {**params_base, 'page': page}
        page_data = await fetch_json(session, f"{HH_API}/vacancies", params=params)
        if not page_data:
            continue
        for it in page_data.get('items', []):
            yield it

