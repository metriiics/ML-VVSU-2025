from hh.cli import collect
import argparse
import asyncio
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='hh_vacancies.db', help='Path to sqlite DB file')
    parser.add_argument('--max', type=int, default=300000, help='Max number of vacancies to collect')
    parser.add_argument('--concurrency', type=int, default=40, help='Concurrent detail requests')
    parser.add_argument('--area-workers', type=int, default=4, help='Number of parallel area workers')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    try:
        asyncio.run(collect(args.db, max_records=args.max, concurrency=args.concurrency, area_workers=args.area_workers))
    except KeyboardInterrupt:
        logging.info('Interrupted by user')