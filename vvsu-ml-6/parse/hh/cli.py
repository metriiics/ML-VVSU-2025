import asyncio
import aiohttp
import logging
import argparse
from datetime import date

from .db import init_db, AsyncDBWriter
from .api import fetch_json, fetch_vacancy_detail, build_vacancy_dict, get_areas, search_items_by_range


async def collect(db_path: str, max_records: int = 300000, concurrency: int = 40, area_workers: int = 4):
    # use async DB writer for higher throughput
    writer = AsyncDBWriter(db_path, batch_size=200, commit_interval=1.0)
    await writer.start()

    connector = aiohttp.TCPConnector(limit=0)
    headers = {"User-Agent": "hh-async-parser/1.0 (+https://example.com)"}
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
        # list areas (cities/regions)
        areas = await get_areas(session)
        logging.info("Found %s areas to scan", len(areas))

        collected = 0
        sem = asyncio.Semaphore(concurrency)

        # default wide date range (includes archive). adjust if needed.
        start_date = '2000-01-01'
        end_date = date.today().isoformat()

        # parallelize areas with a small pool of workers
        area_q = asyncio.Queue()
        for a in areas:
            await area_q.put(a)

        collected_lock = asyncio.Lock()

        async def area_worker(worker_id: int):
            nonlocal collected
            while not area_q.empty():
                try:
                    area = await area_q.get()
                except Exception:
                    break
                area_id = area.get('id')
                area_name = area.get('name')
                logging.info("Worker %s scanning area %s (%s)", worker_id, area_name, area_id)

                batch_ids = []
                try:
                    async for item in search_items_by_range(session, area_id, start_date, end_date, per_page=100, archived=True):
                        vid = item.get('id')
                        if not vid:
                            continue
                        batch_ids.append(vid)

                        if len(batch_ids) >= 100:
                            tasks = [asyncio.create_task(fetch_vacancy_detail(session, _id, sem)) for _id in batch_ids]
                            try:
                                for fut in asyncio.as_completed(tasks):
                                    try:
                                        detail = await fut
                                    except asyncio.CancelledError:
                                        continue
                                    except Exception:
                                        logging.exception("Error fetching vacancy detail")
                                        continue

                                    if not detail:
                                        continue
                                    try:
                                        vdict = build_vacancy_dict(detail)
                                        await writer.enqueue(vdict)
                                        async with collected_lock:
                                            collected += 1
                                    except Exception as exc:
                                        logging.exception("Failed processing vacancy %s: %s", detail.get('id') if detail else None, exc)
                                    if collected % 500 == 0:
                                        logging.info("Collected %s vacancies so far", collected)
                                    if collected >= max_records:
                                        # cancel remaining tasks
                                        for t in tasks:
                                            if not t.done():
                                                t.cancel()
                                        break
                            finally:
                                # ensure all tasks are awaited to suppress warnings
                                for t in tasks:
                                    if not t.done():
                                        try:
                                            await t
                                        except asyncio.CancelledError:
                                            pass
                                        except Exception:
                                            logging.exception("Task error after cancel")

                            batch_ids = []

                            if collected >= max_records:
                                break

                    # remaining ids
                    if batch_ids and collected < max_records:
                        tasks = [asyncio.create_task(fetch_vacancy_detail(session, _id, sem)) for _id in batch_ids]
                        try:
                            for fut in asyncio.as_completed(tasks):
                                try:
                                    detail = await fut
                                except asyncio.CancelledError:
                                    continue
                                except Exception:
                                    logging.exception("Error fetching vacancy detail")
                                    continue

                                if not detail:
                                    continue
                                try:
                                    vdict = build_vacancy_dict(detail)
                                    await writer.enqueue(vdict)
                                    async with collected_lock:
                                        collected += 1
                                except Exception as exc:
                                    logging.exception("Failed processing vacancy %s: %s", detail.get('id') if detail else None, exc)
                                if collected % 500 == 0:
                                    logging.info("Collected %s vacancies so far", collected)
                                if collected >= max_records:
                                    for t in tasks:
                                        if not t.done():
                                            t.cancel()
                                    break
                        finally:
                            for t in tasks:
                                if not t.done():
                                    try:
                                        await t
                                    except asyncio.CancelledError:
                                        pass
                                    except Exception:
                                        logging.exception("Task error after cancel")

                except Exception:
                    logging.exception("Error scanning area %s (%s)", area_name, area_id)

                logging.info("Worker %s finished area %s; total collected %s", worker_id, area_name, collected)
                if collected >= max_records:
                    break

        workers = [asyncio.create_task(area_worker(i)) for i in range(area_workers)]
        await asyncio.gather(*workers)

        # stop writer and flush
        await writer.stop()
        logging.info("Finished; collected %s vacancies", collected)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='hh_vacancies.db', help='Path to sqlite DB file')
    parser.add_argument('--max', type=int, default=300000, help='Max number of vacancies to collect')
    parser.add_argument('--concurrency', type=int, default=40, help='Concurrent detail requests')
    parser.add_argument('--area-workers', type=int, default=4, help='Number of parallel area workers')
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    try:
        asyncio.run(collect(args.db, max_records=args.max, concurrency=args.concurrency, area_workers=args.area_workers))
    except KeyboardInterrupt:
        logging.info('Interrupted by user')
