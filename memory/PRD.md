# Remora.info — PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info.
Core features: Agent Query API, Translation Layer (web crawler), Agent Registry, API Key Auth, Webhook Subscriptions, Rate Limiting/Billing.

## Tech Stack
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB), Stripe Python SDK
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Database**: MongoDB (native text search, no Redis/Meilisearch)
- **Billing**: Stripe subscription management + auto-recharge
- **Auth**: Emergent-managed Google OAuth

## Architecture
```
/app/backend/
├── server.py              # ~265 lines: App setup, middleware, router registration
├── app/
│   ├── database.py        # MongoDB connection (Motor)
│   ├── models.py          # Pydantic models, PLANS, CREDIT_COSTS, RECHARGE_PACKS
│   ├── auth.py            # Auth + credit deduction + 80% alerts + auto-recharge
│   ├── crawler.py         # Web crawler + webhook queue processor
│   └── routers/
│       ├── auth.py        # Session auth endpoints
│       ├── keys.py        # API key CRUD
│       ├── agents.py      # Agent registry CRUD
│       ├── webhooks.py    # Webhook CRUD + deliveries
│       ├── search.py      # Search API (1 credit)
│       ├── crawl.py       # Crawl + bulk + schedule + history
│       ├── sources.py     # Content source CRUD
│       ├── analytics.py   # Usage stats
│       ├── rules.py       # Crawl rule CRUD
│       ├── ranking.py     # Ranking config CRUD
│       ├── orgs.py        # Organization CRUD + invites
│       ├── billing.py     # Stripe subscriptions + auto-recharge settings
│       └── notifications.py # Notification CRUD (alerts)
```

## Completed Features
- [x] Web crawler with structured data extraction
- [x] MongoDB text search + webhook queue
- [x] API key auth + Emergent Google OAuth session auth
- [x] Agent registry, Webhook subscriptions, Content sources
- [x] Crawl rules, Search ranking configs
- [x] Organizations & teams with invites
- [x] Credit-based billing with real-time credit counter
- [x] 5-tier pricing (Free $0, Starter $29, Growth $99, Scale $399, Enterprise custom)
- [x] Backend router extraction (server.py 2300→265 lines) — Feb 2026
- [x] Stripe subscription management (recurring, proration, cancel) — Feb 2026
- [x] 80% usage alerts (notification system + bell in dashboard) — Feb 2026
- [x] Auto-recharge packs (small $15/5k, medium $40/15k, large $100/50k) — Feb 2026

## Billing System
| Endpoint | Description |
|----------|-------------|
| POST /billing/checkout | Stripe subscription checkout |
| POST /billing/change-plan | Upgrade/downgrade with proration |
| POST /billing/cancel | Cancel → Free (3,000 credits) |
| GET /billing/subscription | Subscription status from Stripe |
| GET /billing/recharge-packs | Lists 3 recharge packs |
| GET/PUT /billing/settings | Auto-recharge toggle + pack selection |
| POST /webhook/stripe | Handles 4 subscription event types |

## Notification System
- `notifications` collection: { notification_id, user_id, type, title, message, read, created_at }
- Types: usage_alert, auto_recharge, auto_recharge_failed
- 80% alert: one per billing period (dedup by period_start)
- Bell icon in dashboard header with unread badge

## Pre-Launch Checklist
- [ ] Configure Stripe webhook URL in Dashboard → `/api/webhook/stripe`
- [ ] Add STRIPE_WEBHOOK_SECRET to backend/.env
- [ ] Enable email receipts in Stripe Dashboard (Settings → Emails)

## Upcoming
- Usage forecast widget on billing page (P2)
- Pay-as-you-go metered billing for overages (P2)
- Export functionality for crawled/saved data (P2)
