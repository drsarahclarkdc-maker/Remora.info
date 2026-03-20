# Remora.info — PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info.
Core features: Agent Query API, Translation Layer (web crawler), Agent Registry, API Key Auth, Webhook Subscriptions, Rate Limiting/Billing.

## Tech Stack
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Database**: MongoDB (native text search, no Redis/Meilisearch)
- **Billing**: Stripe subscription management (stripe Python SDK 14.4.0)
- **Auth**: Emergent-managed Google OAuth

## Architecture (Post-Refactor)
```
/app/backend/
├── server.py              # ~260 lines: App setup, middleware, router registration
├── app/
│   ├── database.py        # MongoDB connection (Motor)
│   ├── models.py          # All Pydantic models + billing constants
│   ├── auth.py            # Auth helpers: get_current_user, credits, deduction
│   ├── crawler.py         # Web crawler + webhook queue processor
│   └── routers/
│       ├── auth.py        # POST /auth/session, GET /auth/me, POST /auth/logout
│       ├── keys.py        # GET/POST/DELETE /keys
│       ├── agents.py      # GET/POST/PUT/DELETE /agents
│       ├── webhooks.py    # GET/POST/PUT/DELETE /webhooks + delivery logs
│       ├── search.py      # POST /search (API key auth, 1 credit)
│       ├── crawl.py       # /crawl, /crawl/bulk, /crawl/schedule, /crawl/history
│       ├── sources.py     # GET/POST/PUT/DELETE /sources + manual crawl
│       ├── analytics.py   # GET /usage/stats, GET /usage/recent
│       ├── rules.py       # GET/POST/PUT/DELETE /rules + domain lookup
│       ├── ranking.py     # GET/POST/PUT/DELETE /ranking
│       ├── orgs.py        # GET/POST/DELETE /orgs + invites + members
│       └── billing.py     # Stripe subscriptions: subscribe, change-plan, cancel, webhook
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
- [x] Credit-based billing with real-time credit counter
- [x] 5-tier pricing (Free, Starter, Growth, Scale, Enterprise)
- [x] **Backend router extraction** — server.py from 2300→260 lines (Feb 2026)
- [x] **Stripe subscription management** — recurring billing, proration, cancel (Feb 2026)

## Stripe Subscription System
### Endpoints
| Endpoint | Description |
|----------|-------------|
| POST /billing/checkout | Creates Stripe Checkout session in subscription mode |
| GET /billing/checkout/status/{id} | Polls checkout, stores subscription on success |
| POST /billing/change-plan | Upgrades/downgrades with immediate proration |
| POST /billing/cancel | Cancels subscription, reverts to Free (3,000 credits) |
| GET /billing/subscription | Returns subscription info from Stripe |
| POST /webhook/stripe | Handles checkout.session.completed, invoice.paid, subscription.updated/deleted |

### Key Details
- Products/Prices created on-demand in Stripe, cached in `stripe_prices` MongoDB collection
- Customer IDs stored in `user_billing.stripe_customer_id`
- Subscription IDs stored in `user_billing.stripe_subscription_id`
- Proration: `always_invoice` for immediate pro-rata charges/credits
- Email receipts: Handled by Stripe automatically when Customer has email
- Monthly renewal: Handled via `invoice.paid` webhook + lazy reset in `deduct_credits()`

## Billing Plans
| Plan | Price | Credits/mo |
|------|-------|-----------|
| Free | $0 | 3,000 |
| Starter | $29 | 10,000 |
| Growth | $99 | 40,000 |
| Scale | $399 | 200,000 |
| Enterprise | Custom | Custom |

## P1 — Upcoming
- Email usage alerts at 80% credit threshold
- Hard caps / auto-recharge packs
- Set up Stripe webhook signing secret (STRIPE_WEBHOOK_SECRET) for production security

## P2 — Future/Backlog
- Usage forecast widget on billing page
- Pay-as-you-go metered billing for overages
- Export functionality for crawled/saved data
