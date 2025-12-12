# Парсер статей

## Источники статей

- **habr** (habr.com) - IT-публикации и новости
- **newsvl.ru** (Новости Владивостока) - Региональные новости
- **ixbt.games** (Игровая индустрия) - Игровые новости
- **naked-science** (Naked Science) - Научные статьи
- **interfax.ru** (Интерфакс) - Новости

### Парсинг конкретного сайта:
```bash
python main.py --site habr
python main.py --site newsvl
python main.py --site ixbt
python main.py --site naked-science
python main.py --site interfax
```

### Парсинг нескольких страниц:
```bash
python main.py --site ixbt --pages 3
```

### Изменить количество статей на странице:
```bash
python main.py --site newsvl --articles-per-page 20
```

### Изменить путь к БД:
```bash
python main.py --db my_articles.sqlite
```

### Полный пример:
```bash
python main.py --site all --pages 2 --articles-per-page 15 --db articles.sqlite
```

## Параметры командной строки

- `--site` - Выбор сайта для парсинга (habr, newsvl, ixbt, naked-science, interfax, all). По умолчанию: `all`
- `--pages` - Количество страниц для парсинга. По умолчанию: `1`
- `--articles-per-page` - Максимальное количество статей на странице. По умолчанию: `10`
- `--db` - Путь к файлу БД. По умолчанию: `articles.sqlite`
- `--dry-run` - Режим тестирования без сохранения в БД

## Структура проекта

- `main.py` - Главный скрипт для запуска парсера
- `parser/` - Модули парсеров для разных сайтов
  - `base.py` - Базовый класс парсера
  - `newsvl.py` - Парсер для newsvl.ru
  - `ixbt.py` - Парсер для ixbt.games
  - `nakedscience.py` - Парсер для naked-science.ru
  - `interfax.py` - Парсер для interfax.ru
- `db.py` - Функции для работы с базой данных SQLite
- `cleaner.py` - Утилиты для очистки HTML контента
- `articles.sqlite` - База данных SQLite (создается автоматически)

## Структура базы данных

Таблица `articles`:
- `id` - Уникальный идентификатор
- `guid` - GUID статьи (уникальный)
- `title` - Заголовок статьи
- `description` - Текст статьи (очищенный от HTML)
- `url` - URL статьи (уникальный)
- `published_at` - Дата публикации
- `comments_count` - Количество комментариев
- `created_at_utc` - Время создания записи в БД
- `rating` - Рейтинг статьи (если доступен)

