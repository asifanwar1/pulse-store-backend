# Pulse Store Backend

The API backend for the Pulse Store platform, built with FastAPI and Python.

## Tech Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** + **Alembic** (migrations)
- **PostgreSQL** (via `psycopg2` / **Supabase**)
- **Pydantic** / **Pydantic Settings**
- **Pydantic AI** (OpenAI, Anthropic, Groq)
- **Stripe** (payments)
- **Firebase Admin** (push notifications)
- **python-jose** + **bcrypt** (auth)
- **SlowAPI** (rate limiting)
- **Pytest**

## Prerequisites

- **Python** 3.11+
- **PostgreSQL** database (or a Supabase project)
- `pip` and `venv`

## Getting Started

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd pulse-store-backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file with the required settings (database URL, Stripe keys, Firebase credentials, JWT secrets, etc.) as read by `app/config.py`.

5. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

6. **Start the development server**

   ```bash
   uvicorn app.main:app --reload
   ```

7. **Run tests**

   ```bash
   pytest
   ```

## Project Structure

```
app/
├── core/         # Cross-cutting concerns (security, email, push, money, exceptions, AI agents)
├── features/     # Feature modules (auth, products, orders, cart, categories, offers,
│                 #   banners, reviews, shipments, wallet, users, dashboard, revenue,
│                 #   notifications, favourites, media, ai_agents)
├── config.py     # App configuration/settings
├── database.py   # Database session/engine setup
├── dependencies.py  # Shared FastAPI dependencies
└── main.py       # Application entry point

alembic/          # Database migrations
scripts/          # Utility/maintenance scripts
tests/            # Test suite
```

## Status

Complete.
