# Mini Item Statistics Service

Мини-сервис на Django для импорта и выдачи товарной статистики. Использует PostgreSQL, Redis, Celery и Pandas для обработки данных и публикации REST API.

## Возможности
- Импорт данных из CSV или JSON (HTTP/HTTPS) с резервом на локальный файл (`data/sample_items.csv`)
- Нормализация данных через Pandas и идемпотентная загрузка в БД
- Плановый импорт через Celery Beat (по умолчанию каждые 5 минут)
- REST API (`/api/items`, `/api/stats/avg-price-by-category`) с фильтрами, пагинацией и кэшированием (cacheops + Redis)
- Docker Compose инфраструктура: web, db, redis, celery worker, celery beat
- Pytest-автотесты для импорта, агрегации и фильтров API

## Быстрый старт
1. Скопируйте пример переменных окружения:
   ```bash
   cp example.env .env
   ```
   При необходимости измените `IMPORT_SOURCE_URL` (по умолчанию используется локальный образец данных).

2. Запустите сервис:
   ```bash
   docker compose up --build
   ```

3. Приложение станет доступно на `http://localhost:8000`.

### Ручной запуск импорта
- Через management-команду:
  ```bash
  docker compose exec web python manage.py import_items
  # или указать кастомный источник
  docker compose exec web python manage.py import_items --source-url https://example.com/items.json
  ```
- Через Celery-задачу:
  ```bash
  docker compose exec celery-worker celery -A config call items.tasks.import_items_task
  ```

Журналы импорта выводятся в консоль контейнера (`items.importer`).

## API Примеры
- Список товаров с фильтрацией и пагинацией:
  ```bash
  curl "http://localhost:8000/api/items?category=Electronics&price_min=10&price_max=100&limit=10"
  ```
- Средняя цена по категориям (кэшируется):
  ```bash
  curl "http://localhost:8000/api/stats/avg-price-by-category"
  ```

## Проверка работоспособности

### Автоматическая проверка
Запустите скрипт проверки (Windows PowerShell):
```powershell
.\check_health.ps1
```

Или для Linux/Mac:
```bash
chmod +x check_health.sh
./check_health.sh
```

### Ручная проверка

#### 1. Проверка статуса контейнеров
```bash
docker compose ps
```
Все контейнеры должны быть в статусе `Up` или `Up (healthy)`.

#### 2. Проверка импорта данных
```bash
# Запуск импорта вручную
docker compose exec web python manage.py import_items

# Проверка логов импорта
docker compose logs celery-worker | grep -i "import"
```

#### 3. Проверка API endpoints

**Список всех товаров:**
```bash
curl "http://localhost:8000/api/items"
```

**Фильтрация по категории:**
```bash
curl "http://localhost:8000/api/items?category=Electronics"
```

**Фильтрация по цене:**
```bash
curl "http://localhost:8000/api/items?price_min=10&price_max=100"
```

**Комбинированные фильтры:**
```bash
curl "http://localhost:8000/api/items?category=Electronics&price_min=20&price_max=200&limit=5"
```

**Пагинация:**
```bash
curl "http://localhost:8000/api/items?limit=2&offset=1"
```

**Статистика (средняя цена по категориям):**
```bash
curl "http://localhost:8000/api/stats/avg-price-by-category"
```

#### 4. Проверка базы данных
```bash
# Подключение к PostgreSQL
docker compose exec db psql -U items_user -d items_db

# В psql выполните:
SELECT COUNT(*) FROM items_item;
SELECT category, COUNT(*), AVG(price) FROM items_item GROUP BY category;
\q
```

#### 5. Проверка Redis и кэширования
```bash
# Подключение к Redis
docker compose exec redis redis-cli

# В redis-cli выполните:
KEYS *
GET cacheops:*
\q
```

#### 6. Проверка Celery
```bash
# Проверка логов worker
docker compose logs celery-worker

# Проверка логов beat (планировщик)
docker compose logs celery-beat

# Ручной запуск задачи импорта
docker compose exec celery-worker celery -A config call items.tasks.import_items_task
```

## Тестирование

### Автотесты (pytest)
Локально (без Docker) можно использовать SQLite:
```bash
pip install -r requirements.txt
USE_SQLITE=true python manage.py migrate
USE_SQLITE=true pytest
```

Или в Docker:
```bash
docker compose exec web pytest
```

### Что проверяют тесты:
- ✅ Парсинг и нормализация входных данных (CSV/JSON)
- ✅ Корректный расчёт средней цены по категориям
- ✅ Фильтрация в эндпоинте `/api/items` (category, price_min, price_max)
- ✅ Идемпотентность импорта (обновление существующих записей)

## Принятые решения
- **Pandas** отвечает за нормализацию источников и приведение типов.
- **Идемпотентность**: записи определяются по `source_uid` (хэш либо внешний идентификатор), что обеспечивает обновление вместо дублирования.
- **Cacheops + Redis** обеспечивают кэш агрегации средней цены и автоматическую инвалидизацию при обновлении товаров.
- **Celery beat** планирует регулярный импорт, worker выполняет задачи; оба используют Redis в качестве брокера и бекенда.
- **SQLite fallback** включается переменной `USE_SQLITE=true` для локального запуска тестов без PostgreSQL.

