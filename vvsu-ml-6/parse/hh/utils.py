import re
import html
from typing import Optional


def clean_text(text: Optional[str]) -> str:
    """Clean text from HTML tags, entities and excess whitespace.

    Returns an empty string for None input.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Unescape HTML entities
    s = html.unescape(text)

    # Remove script/style blocks
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", s)

    # Remove all tags
    s = re.sub(r"<[^>]+>", "", s)

    # Replace non-breaking spaces and other weird whitespace
    s = s.replace('\xa0', ' ')

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)

    s = s.strip()

    # Decode literal unicode escape sequences (e.g. "\u0414\u0440...")
    if re.search(r"\\u[0-9a-fA-F]{4}", s):
        try:
            s = s.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass

    # If string is a JSON-encoded list or value, try to parse and normalize
    if re.match(r"^\s*[\[\{\"]", s):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                # join list items into readable string
                parsed = [clean_text(x) for x in parsed]
                return ' '.join([p for p in parsed if p])
            if isinstance(parsed, str):
                return clean_text(parsed)
        except Exception:
            pass

    return s


def clear_item(v: Optional[object]) -> Optional[str]:
    """Return cleaned string or None if input is None/empty after cleaning."""
    if v is None:
        return None
    cleaned = clean_text(v)
    return cleaned if cleaned != "" else None
