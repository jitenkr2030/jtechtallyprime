# JTech Tally Bridge

A modular Python integration engine for TallyPrime. Reads
accounting data from TallyPrime over its HTTP/XML protocol,
persists it to SQLite, exposes REST + dashboard interfaces, and
runs reporting / reconciliation logic.

**Read-only by design.** The bridge never issues CREATE / MODIFY
requests to Tally; every XML envelope uses `TALLYREQUEST=EXPORT`.

## Architecture

```
jtech-tally-bridge/
├── config/         Settings, .env, logging, connection profiles
├── core/           Connection, XML sanitizer/parser, balance parser,
│                   retry decorator, shared request service, sync tracker,
│                   incremental sync helpers
├── modules/        Master readers (Phase 2) + transactions/ (Phase 3)
├── services/       Tier 3.11 - service layer (sync_service, report_service)
├── storage/        SQLite schema + migrations + company registry + repositories/
│                   + sync_runs audit log
├── reports/        Tier 2.6/2.7/2.8 - all standard reports + aging + GSTR-1/3B
│                   + Excel export
├── scheduler/      Background sync (master + transactions)
├── web/            Django backend (production-hardened)
│   ├── api/        REST API + multi-Tally profiles + sync history endpoints
│   ├── dashboard/  Server-rendered HTML dashboard (sync, reports, aging, GSTR)
│   ├── settings.py Production-grade settings (HSTS, SECURE_*, WhiteNoise)
│   └── urls.py     Root URL config
├── deploy/         Tier 1.3 - gunicorn config, nginx config, systemd services
├── Dockerfile      Multi-stage Python 3.12 production image
├── docker-compose.yml  web + scheduler + nginx services
├── diagnostics/    Probing / inspection scripts (pre-implementation)
├── tests/          Unit tests
├── data/           Generated at runtime (DB, exports, logs, static)
├── main.py         CLI entry point (Phase 1-4 commands)
└── manage.py       Django management entry point (Phase 5)
```

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core connector, company management, XML handling, shared request service | Complete |
| 2 | Master data: Ledger, Group, Voucher Type, Stock Group, Stock Item, UOM, Cost Centre, Cost Category, Godown | Complete |
| 3 | Transactions: Voucher header + ledger allocations + inventory allocations (with GST breakdown); convenience readers for Sales / Purchase / Receipt / Payment / Journal / Credit Note / Debit Note / Inventory | Complete |
| 4 | Accounting intelligence: Trial Balance, P&L, Balance Sheet, Day Book, Ledger Statement, GST summary, Bank recon skeleton, Reconciliation | Complete |
| 5 | Django backend/API, auth, multi-Tally profiles, scheduler, dashboard | Complete |

## Tier 1/2 improvements

| Tier | Feature | Status |
|------|---------|--------|
| 1.1 | `sync_runs` audit log + `data-freshness` CLI command + dashboard sync page | Complete |
| 1.2 | Incremental sync via `last_master_sync_at` / `last_voucher_sync_at` + `ALTEREDON` filter | Complete |
| 1.3 | Production hardening: Dockerfile + docker-compose + gunicorn + nginx + systemd + HSTS / SECURE_* | Complete |
| 1.4 | Bulk voucher insert via `executemany` inside single transaction | Complete |
| 2.6 | Aging analysis (debtors/creditors, 0-30/31-60/61-90/90+ buckets) | Complete |
| 2.7 | Excel export via openpyxl for all 10 reports (API + CLI + dashboard) | Complete |
| 2.8 | GSTR-1 (B2B/B2C/HSN-wise) + GSTR-3B (output tax vs ITC) | Complete |
| 3.11 | Service layer: `services/sync_service.py` + `services/report_service.py` | Complete |

## Setup

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure `.env`**

   ```bash
   cp .env.example .env
   # edit .env: TALLY_PROFILE=auto, TALLY_PORT=9000
   ```

3. **Make sure TallyPrime is running** with the gateway enabled:
   `Gateway of Tally > F1 (Help) > Settings > Connectivity > Client/Server configuration`
   - **TallyPrime is on Windows, you are on Linux/WSL:** set
     `TALLY_PROFILE=auto`. The bridge auto-detects the WSL gateway
     IP.
   - **TallyPrime is on the same host:** `TALLY_PROFILE=localhost`.
   - **Manual override:** `TALLY_PROFILE=manual` and `TALLY_HOST=<ip>`.

## CLI usage

```bash
# Discover companies and pick one
python main.py sync-companies
python main.py list-companies
python main.py select-company 1

# Read all masters
python main.py read-all-masters

# Or read individually
python main.py read-ledgers
python main.py read-groups
python main.py read-voucher-types
python main.py read-stock-items

# Read transactions for a date range
python main.py read-vouchers --from 2024-04-01 --to 2025-03-31
python main.py read-vouchers --from 2024-04-01 --to 2025-03-31 --type Sales

# Reports
python main.py trial-balance --from 2024-04-01 --to 2025-03-31
python main.py profit-loss   --from 2024-04-01 --to 2025-03-31
python main.py balance-sheet --as-on 2025-03-31
python main.py day-book      --from 2024-04-01 --to 2025-03-31
python main.py ledger-statement "Cash" --from 2024-04-01 --to 2025-03-31
python main.py gst-summary
python main.py reconcile
```

## Web / API usage

```bash
# Apply migrations (creates admin user tables etc. in the same SQLite)
python manage.py migrate

# Create an admin user
python manage.py createsuperuser

# Start the dev server
python main.py runserver
# or
python manage.py runserver 0.0.0.0:8000
```

Visit:

- `http://localhost:8000/` - Dashboard (login required)
- `http://localhost:8000/admin/` - Django admin
- `http://localhost:8000/api/` - REST endpoints (see below)

### REST endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/login/` | Session login |
| POST | `/api/auth/logout/` | Logout |
| GET  | `/api/companies/` | List companies |
| POST | `/api/companies/` | Sync companies from Tally |
| POST | `/api/companies/<id>/select/` | Select active company |
| GET  | `/api/masters/` | All masters in one call |
| GET  | `/api/ledgers/` | Ledgers |
| GET  | `/api/vouchers/?from=&to=&type=` | Vouchers |
| GET  | `/api/reports/trial-balance/?from=&to=` | Trial balance |
| GET  | `/api/reports/profit-loss/?from=&to=` | P&L |
| GET  | `/api/reports/balance-sheet/?as_on=` | Balance sheet |
| GET  | `/api/reports/day-book/?from=&to=` | Day book |
| GET  | `/api/reports/ledger-statement/<name>/?from=&to=` | Ledger stmt |
| GET  | `/api/reports/gst-summary/?from=&to=` | GST summary |
| GET  | `/api/reports/bank-reconciliation/?as_on=` | Bank recon |
| GET  | `/api/reports/reconcile/` | Reconciliation |
| GET  | `/api/profiles/` | List multi-Tally profiles |
| POST | `/api/profiles/` | Add a profile |
| DELETE | `/api/profiles/<name>/` | Delete a profile |

## Scheduler

```bash
# Schedule periodic master sync (every hour)
python main.py schedule-sync --every 3600

# Run the scheduler loop
python main.py run-scheduler
```

For production deployments, replace the loop runner with APScheduler
backed by a job store (Redis/SQLAlchemy) so multiple workers do not
duplicate jobs.

## Tests

```bash
python -m unittest discover tests -v
```

## Security

- All Tally XML requests use `TALLYREQUEST=EXPORT` (read-only).
- `.env` is gitignored. Real accounting data, the SQLite DB and the
  `data/exports/` JSON files must never be committed.
- The dashboard and API require authentication by default.
- For multi-user deployments, configure Django's auth backends and
  consider adding per-user company-access ACLs.

## Important caveat - field-level verification

The bridge implements all reader modules against TallyPrime's
**standard XML conventions**. Field names returned by Tally can
vary slightly across versions and across user-customised data
files. The diagnostics/ folder is kept deliberately so that
before relying on any report you can run the matching probe:

```bash
python -m diagnostics.probe_voucher_type_fields
python -m diagnostics.probe_group_xml_fields
# etc.
```

If a probe reveals a different field name in your Tally data,
update the corresponding `FETCH` clause in the reader's XML and
the matching `get_field()` call in its extractor. This is the
same workflow used during Phase 1/2 development and is why the
diagnostics folder ships with the project.

## Docker deployment (Tier 1.3)

For production:

```bash
# 1. Configure env
cp .env.prod.example .env.prod
# Edit .env.prod: set TALLY_HOST, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS

# 2. Build and start
docker compose up -d --build

# 3. Apply migrations (uses the same SQLite volume)
docker compose exec web python manage.py migrate

# 4. Create admin user
docker compose exec web python manage.py createsuperuser

# 5. Visit https://your-host/  (nginx terminates TLS)
```

For systemd (without Docker):

```bash
sudo cp deploy/jtech-tally-bridge.service /etc/systemd/system/
sudo cp deploy/jtech-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jtech-tally-bridge jtech-scheduler
```

Production hardening features:
- `DEBUG=False` enforced unless `DJANGO_DEBUG=True` explicitly
- SECRET_KEY check refuses to start with default dev key in prod
- HSTS 30 days, X-Frame DENY, X-Content-Type nosniff
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HttpOnly
- WhiteNoise for compressed static files
- gunicorn with auto-tuned workers = (2 * cores) + 1
- nginx with TLS 1.2/1.3 only, security headers, static caching
- Health check at `/health/` for container orchestration

## Roadmap (post Tier 1/2)

- **Bank reconciliation full BRS** - extend voucher extraction
  with the `BANKALLOCATIONS` block (cheque no, value date,
  clearance date).
- **Cost-centre-wise P&L** - extend `voucher_ledger_allocations`
  to capture cost centre per allocation.
- **TDS tracking** - TDS section, deductee-wise, quarterly returns
  (194C, 194J, 194I etc.).
- **Multi-company consolidation** - inter-company elimination.
- **Mobile responsive dashboard + Hindi UI** - i18n framework,
  dark mode toggle.
- **Email notifications** on sync failures.
- **OpenAPI/Swagger docs** for the REST API (drf-spectacular).
- **Licensing** - per-deployment licence token checked at
  scheduler start and dashboard login.
