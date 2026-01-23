import aiosqlite
import json
import asyncio
from typing import Dict, List, Optional


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS vacancies (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    salary_start INTEGER,
    salary_to INTEGER,
    currency TEXT,
    salary_mode TEXT,
    experience TEXT,
    employment TEXT,
    employer_name TEXT,
    schedule TEXT,
    working_hours TEXT,
    work_format TEXT,
    city_vacancies TEXT,
    published_at TEXT,
    professional_roles TEXT,
    professional_roles_id TEXT,
    type TEXT,
    employer_trusted INTEGER,
    premium_status INTEGER,
    description TEXT,
    key_skills TEXT
)
"""

INSERT_SQL = """
INSERT OR REPLACE INTO vacancies (
    id, name, url, salary_start, salary_to, currency, salary_mode,
    experience, employment, employer_name, schedule, working_hours, work_format,
    city_vacancies, published_at, professional_roles, professional_roles_id,
    type, employer_trusted, premium_status, description, key_skills
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
)
"""


async def init_db(db_path: str):
    db = await aiosqlite.connect(db_path)
    # performance PRAGMAs for bulk insert
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA temp_store=MEMORY;")
    await db.execute(CREATE_SQL)
    await db.commit()
    return db


class AsyncDBWriter:
    def __init__(self, db_path: str, batch_size: int = 200, commit_interval: float = 1.0):
        self.db_path = db_path
        self.batch_size = batch_size
        self.commit_interval = commit_interval
        self.queue: "asyncio.Queue[Dict]" = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA synchronous=NORMAL;")
        await self._conn.execute("PRAGMA temp_store=MEMORY;")
        await self._conn.execute(CREATE_SQL)
        await self._conn.commit()
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        self._stop.set()
        if self._task:
            await self._task
        await self._conn.commit()
        await self._conn.close()

    async def enqueue(self, v: Dict):
        await self.queue.put(v)

    async def _worker(self):
        buffer: List[Dict] = []
        while not (self._stop.is_set() and self.queue.empty()):
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=self.commit_interval)
                buffer.append(item)
            except asyncio.TimeoutError:
                pass

            if len(buffer) >= self.batch_size or (self._stop.is_set() and buffer):
                await self._flush(buffer)
                buffer = []

        # final flush
        if buffer:
            await self._flush(buffer)

    async def _flush(self, buffer: List[Dict]):
        rows = []
        for v in buffer:
            rows.append(self._dict_to_tuple(v))
        try:
            await self._conn.executemany(INSERT_SQL, rows)
            await self._conn.commit()
        except Exception:
            # best-effort: log and continue
            import logging
            logging.exception("DB writer failed to insert batch")

    def _dict_to_tuple(self, v: Dict):
        return (
            v.get('id'),
            v.get('name'),
            v.get('url'),
            v.get('salary_start'),
            v.get('salary_to'),
            v.get('currency'),
            v.get('salary_mode'),
            v.get('experience'),
            v.get('employment'),
            v.get('employer_name'),
            json.dumps(v.get('schedule') or [], ensure_ascii=False),
            json.dumps(v.get('working_hours') or [], ensure_ascii=False),
            json.dumps(v.get('work_format') or [], ensure_ascii=False),
            v.get('city_vacancies'),
            v.get('published_at'),
            json.dumps(v.get('professional_roles') or [], ensure_ascii=False),
            json.dumps(v.get('professional_roles_id') or [], ensure_ascii=False),
            v.get('type'),
            1 if v.get('employer_trusted') else 0,
            1 if v.get('premium_status') else 0,
            v.get('description') or '',
            json.dumps(v.get('key_skills') or [], ensure_ascii=False),
        )

