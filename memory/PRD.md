# Remora.info - PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info with:
- Agent Query API — accepts structured JSON queries, returns JSON results
- Translation Layer — crawls human websites (HTML), extracts structured data, serves as JSON to agents
- Agent Registry — agents can register capabilities, endpoints, auth info
- API Key Auth — no cookies, just API keys for agent identity
- Webhook Subscriptions — agents subscribe to result updates
- Rate Limiting — FREE for everyone (track usage for now, add paid tiers later)

## Core Requirements (All Complete)
- [x] Agent Query API with JSON in/out (Meilisearch-powered)
- [x] Translation Layer (web crawler with structured data extraction)
- [x] Agent Registry with capabilities
- [x] API Key Authentication (X-API-Key header)
- [x] Webhook Subscriptions with Redis queue delivery
- [x] Usage tracking (FREE for all - no rate limits)
- [x] Full Dashboard with analytics
- [x] Emergent Google Social Login
- [x] Meilisearch for fast search
- [x] Web crawler for content extraction
- [x] Scheduled crawling for content freshness
- [x] Bulk crawl endpoint for batch processing
- [x] API docs page with interactive examples
- [x] Webhook delivery logs in dashboard
- [x] Content source management UI
- [x] Crawl history tracking
- [x] **Search result ranking improvements** (configurable ranking profiles)
- [x] **Custom crawl rules per domain** (CSS selectors, path filters, rate limiting)
- [x] **Team/Organization support** (create orgs, invite members, role-based access)

## What's Been Implemented

### Backend Endpoints
- `/api/auth/*` - Session management with Emergent OAuth
- `/api/keys` - API Key CRUD
- `/api/agents` - Agent Registry CRUD
- `/api/webhooks` - Webhook subscriptions
- `/api/webhooks/deliveries` - Webhook delivery logs
- `/api/webhooks/deliveries/stats` - Delivery statistics
- `/api/search` - Agent Query API with Meilisearch
- `/api/crawl` - Single URL crawl
- `/api/crawl/bulk` - Bulk crawl (up to 100 URLs)
- `/api/crawl/jobs` - Track bulk crawl jobs
- `/api/crawl/schedule` - Scheduled crawling
- `/api/crawl/history` - Crawl history tracking
- `/api/crawl/history/stats` - Crawl statistics
- `/api/sources` - Content source management
- `/api/usage/*` - Analytics
- `/api/docs/reference` - Full API documentation
- `/api/rules` - Custom crawl rules CRUD (GET, POST, PUT, DELETE)
- `/api/rules/domain/{domain}` - Get rule for specific domain
- `/api/ranking` - Search ranking config CRUD (GET, POST, PUT, DELETE)
- `/api/orgs` - Organization CRUD (GET, POST, DELETE)
- `/api/orgs/{org_id}/members` - Org member management
- `/api/orgs/{org_id}/invite` - Invite members
- `/api/orgs/invites/pending` - List pending invites
- `/api/orgs/invites/{invite_id}/accept` - Accept invite

### Frontend Pages
- Landing Page (hero, features, free pricing)
- API Docs Page (`/docs`) - Complete API reference
- Dashboard - Stats, charts, quick actions
- API Keys Management (`/keys`)
- Agent Registry (`/agents`)
- Content Sources (`/sources`) - Manage URLs to crawl
- Crawl Rules (`/crawl-rules`) - Custom extraction rules per domain
- Webhooks Management (`/webhooks`)
- Webhook Deliveries (`/webhooks/deliveries`) - Delivery logs
- Search Test Interface (`/search`)
- Search Ranking (`/ranking`) - Configure ranking profiles
- Crawl History (`/history`) - All crawl operations
- Analytics Dashboard (`/analytics`)
- Organizations (`/organizations`) - Team management
- Settings/Profile Page (`/settings`)

### Infrastructure
- Meilisearch: Full-text search
- Redis: Webhook delivery queue with 3 retries
- MongoDB: Data persistence
- Background Tasks: Scheduled crawl runner, webhook processor

## Pricing
- **Current**: FREE for everyone, unlimited usage
- **Future**: Add paid tiers when ready

## Completed Backlog
- [x] Core API endpoints
- [x] Authentication flow
- [x] Dashboard UI
- [x] Meilisearch integration
- [x] Web crawler
- [x] Redis webhook queue
- [x] Scheduled crawling
- [x] Bulk crawl endpoint
- [x] API docs page
- [x] Webhook delivery logs
- [x] Content source management
- [x] Crawl history tracking
- [x] Search result ranking improvements
- [x] Custom crawl rules per domain
- [x] Team/Organization support

## Future Enhancements (P2)
- [ ] Backend refactoring: Break server.py into organized modules
- [ ] Stripe billing (when ready for paid tiers)
- [ ] Export functionality

## Architecture
```
/app/
├── backend/
│   └── server.py         # FastAPI app (~2900 lines, needs modularization)
│   └── requirements.txt
│   └── .env
│   └── tests/
│       └── test_new_features.py
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main router (all 15 routes)
│   │   ├── index.css     # Global styles
│   │   ├── context/
│   │   │   └── AuthContext.js
│   │   ├── components/
│   │   │   └── layout/
│   │   │       └── DashboardLayout.js # Sidebar (12 nav items)
│   │   └── pages/        # 15 page components
│   ├── package.json
│   └── tailwind.config.js
├── memory/
│   └── PRD.md
└── test_reports/
    ├── iteration_1.json
    └── iteration_2.json
```

## Test Reports
- iteration_1.json: Initial feature testing
- iteration_2.json: Crawl Rules, Search Ranking, Organizations - ALL PASSED (21/21 backend, 100% frontend)
