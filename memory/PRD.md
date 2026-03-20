# Remora.info - PRD

## Original Problem Statement
Build an API-first search engine for AI agents called remora.info with:
- Agent Query API — accepts structured JSON queries, returns JSON results
- Translation Layer — crawls human websites (HTML), extracts structured data, serves as JSON to agents
- Agent Registry — agents can register capabilities, endpoints, auth info
- API Key Auth — no cookies, just API keys for agent identity
- Webhook Subscriptions — agents subscribe to result updates
- Rate Limiting — tiered (free/pro/enterprise)

## User Personas
1. **AI Developer** - Needs structured data access for their AI agents
2. **Bot Creator** - Wants to connect agents to world knowledge
3. **Automation Engineer** - Requires reliable API with rate limiting

## Core Requirements (Static)
- [x] Agent Query API with JSON in/out
- [x] Translation Layer (crawled content with structured data)
- [x] Agent Registry with capabilities
- [x] API Key Authentication (X-API-Key header)
- [x] Webhook Subscriptions (event-based)
- [x] Rate Limiting Tiers (Free: 100/day, Pro: 10K/day, Enterprise: unlimited)
- [x] Full Dashboard with analytics
- [x] Emergent Google Social Login

## What's Been Implemented (Jan 2026)

### Backend (FastAPI + MongoDB)
- `/api/auth/*` - Session management with Emergent OAuth
- `/api/keys` - API Key CRUD (create, list, revoke)
- `/api/agents` - Agent Registry CRUD
- `/api/webhooks` - Webhook subscription management
- `/api/search` - Agent Query API with API key auth
- `/api/usage/*` - Analytics and rate limiting
- `/api/content` - Crawled content listing
- `/api/seed` - Sample data seeding
- MongoDB text search (Meilisearch fallback)

### Frontend (React + Tailwind + Shadcn)
- Landing Page (hero, features, pricing)
- Dashboard (stats, charts, quick actions)
- API Keys Management
- Agent Registry
- Webhooks Management
- Search Test Interface
- Analytics Dashboard
- Settings/Profile Page

## Prioritized Backlog

### P0 (Critical) - Done
- [x] Core API endpoints
- [x] Authentication flow
- [x] Dashboard UI

### P1 (High Priority)
- [ ] Meilisearch integration (currently using MongoDB text search)
- [ ] Actual website crawling functionality
- [ ] Webhook delivery system
- [ ] Email notifications for rate limit warnings

### P2 (Medium Priority)
- [ ] API documentation page (Swagger/ReDoc)
- [ ] Team/Organization support
- [ ] Custom rate limits per API key
- [ ] Billing integration (Stripe)

### P3 (Low Priority)
- [ ] CLI tool for API access
- [ ] SDK packages (Python, Node.js)
- [ ] Advanced analytics (latency percentiles, error rates)

## Next Tasks
1. Deploy Meilisearch for better search performance
2. Implement actual web crawler with structured data extraction
3. Build webhook delivery queue (Redis-based)
4. Add Stripe billing for Pro/Enterprise tiers
