# 📰 Jarvis Invest – News Aggregator

A professional, real-time news terminal and aggregator powered by **FastAPI**, **MySQL**, **Celery**, and **NewsAPI**.

## 🚀 Overview

Jarvis Invest is a full-stack news dashboard designed for financial and technology monitoring. It automatically aggregates global headlines into a persistent local database, providing a high-performance interface for both real-time discovery and historical archive exploration.

---

## ✨ Key Features

- **Real-time Ingestion**: Automatically fetches global news headlines (default: "Tesla") every minute.
- **Historical Archiving**: Stores thousands of articles in a MySQL database with optimized indexing.
- **Dual-Mode UI**:
  - **Headlines Grid**: A visual, image-heavy discovery feed for today's news.
  - **Database Archive**: A professional data table for browsing years of historical news with full pagination.
- **On-Demand Backfill**: Request news for any specific date; the system automatically fetches from NewsAPI if the local database is empty.
- **Robust Character Handling**: Custom Python-side scrubbing to support legacy MySQL versions and handle 4-byte emojis safely.
- **Background Tasking**: Decoupled fetching architecture using Celery workers and Redis.

---

## 🛠️ Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com) (Python 3.12+)
- **Database**: [MySQL](https://www.mysql.com/) + [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Task Queue**: [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/)
- **Frontend**: [Tailwind CSS v3](https://tailwindcss.com/) + Native JavaScript
- **API**: [NewsAPI.org](https://newsapi.org/)

---

## 🚦 Getting Started

### 1. Prerequisites
- Python 3.10+
- MySQL Server
- Redis Server
- [NewsAPI Key](https://newsapi.org/register)

### 2. Environment Setup
Clone the repository and create a `.env` file in the root directory:

```env
NEWS_API_KEY=your_news_api_key_here
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/jarvis_news?charset=utf8
REDIS_URL=redis://localhost:6379/0
```

### 3. Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application

**Start the Web Server:**
```bash
uvicorn app.main:app --reload
```

**Start the Celery Worker (Separately):**
```bash
celery -A app.celery_app.worker worker --loglevel=info
```

**Start the Celery Beat (Periodic Tasks):**
```bash
celery -A app.celery_app.scheduler beat --loglevel=info
```

---

## 🐳 Docker Deployment
The project includes a `docker-compose.yml` for quick infrastructure provisioning (MySQL & Redis):

```bash
docker-compose up -d
```

---

## 📡 API Endpoints

- `GET /`: Main Dashboard UI.
- `GET /news`: Returns latest 100 headlines. Supports `?date=DD-MM-YYYY`.
- `GET /news/all`: Paginated database exploration. Supports `?skip=0&limit=15&date=DD-MM-YYYY`.
- `POST /news/fetch`: Manually trigger a fresh news sync.

---

## 📜 License
© 2025 Jarvis Invest. All rights reserved.
