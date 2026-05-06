# FinLedger — Finance Data Automation & Dashboard

A production-grade Django + Python finance automation system that ingests CSV data, performs intelligent reconciliation, exposes REST APIs, and visualizes everything in a clean dark dashboard.

---

## Features

| Feature | Details |
|---|---|
| **CSV Ingestion** | Upload bank statements & internal ledger via API or Django Admin |
| **Smart Reconciliation** | Fuzzy matching (SequenceMatcher + Jaccard token overlap) with ±2 day date window |
| **Auto-Categorization** | Rule-based engine: "Swiggy" → Food & Dining, "AWS" → SaaS & Software, etc. |
| **Duplicate Detection** | MD5 fingerprint per row to prevent double-counting |
| **Normalized Ledger** | Unified table with source, category, reconciliation status |
| **REST APIs** | `/summary`, `/reconciliation`, `/category-breakdown`, `/ledger`, `/export` |
| **Dashboard** | Dark-themed, Chart.js powered — cashflow trend, category pie, reconciliation table |
| **Background Jobs** | Celery workers + Celery Beat for scheduled reconciliation |
| **Docker** | Full docker-compose with PostgreSQL + Redis + Web + Worker + Beat |
| **API Docs** | Auto-generated Swagger UI at `/api/docs/` |

---

## Quick Start (Docker — Recommended)

```bash
git clone https://github.com/yourname/finledger.git
cd finledger

# Start everything
docker-compose up --build

# App will be at:
#   Dashboard:   http://localhost:8000
#   API Docs:    http://localhost:8000/api/docs/
#   Django Admin: http://localhost:8000/admin  (admin / admin123)
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### 2. Install dependencies
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your DB credentials
```

### 4. Set up database
```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE finledger;"

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 5. Run the server
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A finledger worker --loglevel=info

# Terminal 3: Celery beat (scheduled reconciliation)
celery -A finledger beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 6. Open the dashboard
Visit **http://localhost:8000**

---

## API Reference

### `GET /api/summary/`
Returns financial totals and daily cashflow trend.

**Query params:** `from_date`, `to_date` (YYYY-MM-DD)

```json
{
  "total_credits": 290000,
  "total_debits": 84726,
  "net_cashflow": 205274,
  "unmatched_amount": 18000,
  "unmatched_count": 1,
  "daily_cashflow": [
    { "date": "2025-05-01", "credits": 120000, "debits": 420 }
  ]
}
```

---

### `GET /api/reconciliation/`
Returns matched and unmatched transaction pairs.

**Query params:** `status` = `matched` | `unmatched_bank` | `unmatched_ledger`

```json
{
  "summary": { "matched": 24, "unmatched_bank": 1, "unmatched_ledger": 0, "match_rate": 96.0 },
  "matched": [...],
  "unmatched_bank": [...],
  "unmatched_ledger": [...]
}
```

---

### `POST /api/reconciliation/run/`
Triggers a background reconciliation run.

**Query params:** `sync=true` for synchronous execution.

---

### `GET /api/category-breakdown/`
Expenses grouped by auto-detected category.

**Query params:** `txn_type` (default: `debit`), `from_date`, `to_date`

```json
{
  "categories": [
    { "name": "SaaS & Software", "amount": 16684, "count": 5, "percentage": 19.69 }
  ]
}
```

---

### `GET /api/ledger/`
Paginated normalized ledger with filters.

**Query params:** `status`, `category`, `source`, `txn_type`, `from_date`, `to_date`, `page`, `page_size`

---

### `POST /api/ingest/upload/`
Upload a CSV file.

**Form data:** `file` (CSV), `source` (`bank` | `ledger`)

---

### `GET /api/export/?type=ledger|bank|recon`
Download data as CSV.

---

## CSV Format

### bank_statement.csv
```
date,narration,amount,type,reference,balance
2025-05-01,SWIGGY ORDER #812,420,debit,SW812,99580
2025-05-01,CLIENT PAYMENT ACME,120000,credit,ACM001,219580
```
**Required:** `date`, `narration`, `amount`, `type`

### internal_ledger.csv
```
date,description,amount,category,reference,notes
2025-05-01,Swiggy food delivery,420,Food & Dining,SW812,Team lunch
```
**Required:** `date`, `description`, `amount`, `category`

---

## Reconciliation Logic

```
For each bank transaction:
  1. Find ledger entries where amount matches exactly
  2. Filter to those within ±2 days
  3. Score similarity: 60% SequenceMatcher + 40% Jaccard token overlap
  4. Match if score ≥ 0.35 (configurable in engine.py)
  5. Each ledger entry matched at most once (greedy best-first)
```

---

## Auto-Categorization Rules

| Category | Triggers |
|---|---|
| Food & Dining | swiggy, zomato, mcdonalds, dominos, kfc, pizza, cafe… |
| Travel | uber, ola, irctc, indigo, makemytrip, petrol, fastag… |
| SaaS & Software | aws, github, digitalocean, notion, zoom, figma, vercel… |
| Utilities | electricity, bsnl, jio, airtel, broadband, gas bill… |
| Healthcare | apollo, hospital, pharmacy, insurance, diagnostic… |
| Shopping | amazon, flipkart, myntra, ajio, meesho… |
| Banking & Finance | emi, loan, credit card, hdfc, icici, upi, razorpay… |
| Revenue | salary, invoice, consulting, freelance, cashback… |

Add your own rules in `apps/reconciliation/categorizer.py`.

---

## Project Structure

```
finledger/
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── finledger/              # Django project
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── ingestion/          # CSV upload, parsing, duplicate detection
│   │   ├── models.py       # BankTransaction, InternalLedgerEntry, UploadLog
│   │   ├── services.py     # CSV parsing engine
│   │   └── views.py        # Upload API
│   ├── reconciliation/     # Matching engine
│   │   ├── engine.py       # Core reconciliation logic
│   │   ├── categorizer.py  # Auto-categorization rules
│   │   ├── tasks.py        # Celery background tasks
│   │   └── models.py       # ReconciliationResult
│   ├── ledger/             # Normalized ledger
│   │   └── models.py       # NormalizedLedger
│   └── api/                # REST endpoints + dashboard
│       ├── views.py        # All API views
│       └── urls.py
├── templates/
│   └── dashboard.html      # Full dark dashboard UI
└── sample_data/
    ├── bank_statement.csv
    └── internal_ledger.csv
```

---

## Deployment on Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
railway init
railway add postgresql
railway add redis

# Set env vars
railway variables set SECRET_KEY="your-secret-key"
railway variables set DEBUG=False

railway up
```

---

## Deployment on Render

1. Connect GitHub repo to Render
2. Add PostgreSQL and Redis services
3. Set environment variables from `.env.example`
4. Build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
5. Start command: `gunicorn finledger.wsgi:application`

---

## License
MIT
