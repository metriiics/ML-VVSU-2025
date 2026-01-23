# HH.ru Async Parser

Асинхронный парсер вакансий через API HeadHunter (hh.ru). Собирает вакансии и сохраняет в SQLite.

Установка:

```bash
python -m pip install -r requirements.txt
```

Пример запуска:

```bash
python hh_parser_async.py --db hh_vacancies.db --max 300000 --concurrency 40
```

Параметры:
- `--db` путь к sqlite файлу (по умолчанию `hh_vacancies.db`).
- `--max` максимальное количество записей для сбора.
- `--concurrency` количество конкурентных запросов к деталям вакансий.

Файл `hh_parser_async.py` содержит реализацию: инициализация БД, асинхронная загрузка страниц поиска, загрузка деталей вакансий и вставка/обновление в БД.
