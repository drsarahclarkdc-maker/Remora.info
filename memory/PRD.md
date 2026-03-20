# Remora.info — PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info.
Core features: Agent Query API, Translation Layer (web crawler), Agent Registry, API Key Auth, Webhook Subscriptions, Rate Limiting/Billing.

## Tech Stack
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Database**: MongoDB (native text search, no Redis/Meilisearch)
- **Billing**: Credit-based tier system via Stripe (emergentintegrations)
- **Auth**: Emergent-managed Google OAuth

## Architecture (Post-Refactor)
```
/app/backend/
├── server.py              # ~260 lines: App setup, middleware, router registration, startup/shutdown
├── app/
│   ├── database.py        # MongoDB connection (Motor)
│   ├── models.py          # All Pydantic models + billing constants (PLANS, CREDIT_COSTS)
│   ├── auth.py            # Auth helpers: get_current_user, credits, deduction
│   ├── crawler.py         # Web crawler + webhook queue processor
│   └── routers/
│       ├── auth.py        # POST /auth/session, GET /auth/me, POST /auth/logout
│       ├── keys.py        # GET/POST/DELETE /keys
│       ├── agents.py      # GET/POST/PUT/DELETE /agents
│       ├── webhooks.py    # GET/POST/PUT/DELETE /webhooks + delivery logs
│       ├── search.py      # POST /search (API key auth, 1 credit)
│       ├── crawl.py       # /crawl, /crawl/bulk, /crawl/schedule, /crawl/history + background tasks
│       ├── sources.py     # GET/POST/PUT/DELETE /sources + manual crawl
│       ├── analytics.py   # GET /usage/stats, GET /usage/recent
│       ├── rules.py       # GET/POST/PUT/DELETE /rules + domain lookup
│       ├── ranking.py     # GET/POST/PUT/DELETE /ranking
│       ├── orgs.py        # GET/POST/DELETE /orgs + invites + members
│       └── billing.py     # /billing/plans, /billing/usage, /billing/checkout, /webhook/stripe
```

## What's Been Implemented
- [x] Web crawler with structured data extraction
- [x] MongoDB text search (replaces Meilisearch)
- [x] MongoDB webhook queue (replaces Redis)
- [x] API key auth + session auth (Emergent Google OAuth)
- [x] Agent registry CRUD
- [x] Webhook subscriptions + delivery logs
- [x] Content sources with scheduled crawling
- [x] Crawl rules (per-domain custom selectors)
- [x] Search ranking configurations
- [x] Organizations & teams with invites
- [x] Credit-based billing with Stripe checkout
- [x] Real-time credit counter in dashboard
- [x] 5-tier pricing (Free, Starter, Growth, Scale, Enterprise)
- [x] **Backend router extraction refactoring** (server.py: 2300→260 lines) — Completed Feb 2026

## Billing
| Plan | Price | Credits/mo |
|------|-------|-----------|
| Free | $0 | 3,000 |
| Starter | $29 | 10,000 |
| Growth | $99 | 40,000 |
| Scale | $399 | 200,000 |
| Enterprise | Custom | Custom |

Credit costs: Search=1, Crawl=1, Bulk crawl=1/URL, Content extract=1

## P0 — Completed
- Backend router extraction: All routes migrated from monolithic server.py to 12 router modules
- Path conflict fixes: /crawl/history/stats before /{content_id}, /orgs/invites/pending before /{org_id}
- _id leak fixes in rules and ranking routers

## P1 — Upcoming
- Email usage alerts at 80% credit threshold
- Hard caps / auto-recharge packs

## P2 — Future/Backlog
- Usage forecast widget on billing page
- Pay-as-you-go metered billing for overages
- Export functionality for crawled/saved data
