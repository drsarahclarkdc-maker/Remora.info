# Remora.info - PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info with:
- Agent Query API — accepts structured JSON queries, returns JSON results
- Translation Layer — crawls human websites (HTML), extracts structured data, serves as JSON to agents
- Agent Registry — agents can register capabilities, endpoints, auth info
- API Key Auth — no cookies, just API keys for agent identity
- Webhook Subscriptions — agents subscribe to result updates
- Rate Limiting — FREE for everyone (track usage for now, add paid tiers later)

## User Personas
1. **AI Developer** - Needs structured data access for their AI agents
2. **Bot Creator** - Wants to connect agents to world knowledge
3. **Automation Engineer** - Requires reliable API with usage tracking

## Core Requirements (Static)
- [x] Agent Query API with JSON in/out
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

## What's Been Implemented (Jan 2026)

### Backend (FastAPI + MongoDB + Meilisearch + Redis)
- `/api/auth/*` - Session management with Emergent OAuth
- `/api/keys` - API Key CRUD (create, list, revoke)
- `/api/agents` - Agent Registry CRUD
- `/api/webhooks` - Webhook subscription management with Redis queue
- `/api/search` - Agent Query API with Meilisearch
- `/api/crawl` - Single URL crawl endpoint
- `/api/crawl/bulk` - Bulk crawl endpoint (up to 100 URLs)
- `/api/crawl/jobs` - Track bulk crawl job status
- `/api/crawl/schedule` - Scheduled crawling (hourly/daily/weekly)
- `/api/usage/*` - Analytics (tracking only, no limits)
- `/api/content` - Crawled content listing
- `/api/docs/reference` - Full API documentation

### Frontend (React + Tailwind + Shadcn)
- Landing Page (hero, features, single free pricing)
- API Docs Page (quick start, auth, endpoints, code examples)
- Dashboard (stats, charts, quick actions)
- API Keys Management
- Agent Registry
- Webhooks Management
- Search Test Interface
- Analytics Dashboard
- Settings/Profile Page

### Infrastructure
- Meilisearch: Full-text search with filtering (55ms avg)
- Redis: Webhook delivery queue with 3 retries
- MongoDB: Data persistence
- Background Tasks: Scheduled crawl runner, webhook processor

## Pricing Strategy
- **Currently**: FREE for everyone, unlimited usage
- **Future**: Add paid tiers once we have users

## Prioritized Backlog

### P0 (Critical) - DONE
- [x] Core API endpoints
- [x] Authentication flow
- [x] Dashboard UI
- [x] Meilisearch integration
- [x] Web crawler
- [x] Redis webhook queue
- [x] Scheduled crawling
- [x] Bulk crawl endpoint
- [x] API docs page

### P1 (High Priority)
- [ ] Webhook delivery logs in dashboard
- [ ] Content source management UI
- [ ] Search result ranking improvements
- [ ] Crawl history and versioning

### P2 (Medium Priority)
- [ ] Team/Organization support
- [ ] Export functionality
- [ ] Advanced filters in search
- [ ] Custom crawl rules per domain

### P3 (On Hold)
- [ ] Stripe billing (add later when ready for paid tiers)

## Next Tasks
1. Add webhook delivery logs to dashboard
2. Build content source management UI
3. Implement crawl history tracking
