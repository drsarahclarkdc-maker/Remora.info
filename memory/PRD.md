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

## What's Been Implemented (Jan 2026)

### Backend (FastAPI + MongoDB + Meilisearch + Redis)
- `/api/auth/*` - Session management with Emergent OAuth
- `/api/keys` - API Key CRUD (create, list, revoke)
- `/api/agents` - Agent Registry CRUD
- `/api/webhooks` - Webhook subscription management with Redis queue
- `/api/search` - Agent Query API with Meilisearch
- `/api/crawl` - Web crawler endpoint (extracts title, description, content, structured data)
- `/api/usage/*` - Analytics (tracking only, no limits)
- `/api/content` - Crawled content listing
- `/api/seed` - Sample data seeding

### Frontend (React + Tailwind + Shadcn)
- Landing Page (hero, features, single free pricing)
- Dashboard (stats, charts, quick actions)
- API Keys Management
- Agent Registry
- Webhooks Management
- Search Test Interface
- Analytics Dashboard
- Settings/Profile Page

### Infrastructure
- Meilisearch: Full-text search with filtering
- Redis: Webhook delivery queue with retries
- MongoDB: Data persistence

## Pricing Strategy
- **Currently**: FREE for everyone, unlimited usage
- **Future**: Add paid tiers once we have users and understand usage patterns

## Prioritized Backlog

### P0 (Critical) - DONE
- [x] Core API endpoints
- [x] Authentication flow
- [x] Dashboard UI
- [x] Meilisearch integration
- [x] Web crawler
- [x] Redis webhook queue

### P1 (High Priority)
- [ ] Scheduled crawling (cron jobs for content freshness)
- [ ] Bulk crawl endpoint
- [ ] Search result ranking improvements
- [ ] API documentation page (Swagger/ReDoc)

### P2 (Medium Priority)
- [ ] Team/Organization support
- [ ] Content source management UI
- [ ] Webhook delivery logs in dashboard
- [ ] Export functionality

### P3 (On Hold)
- [ ] Stripe billing (add later when ready for paid tiers)

## Next Tasks
1. Add scheduled crawling for content freshness
2. Build bulk crawl endpoint for batch URL processing
3. Add API docs page with interactive examples
