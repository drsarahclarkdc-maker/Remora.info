"""
Comprehensive E2E Tests for Remora API - All Router Endpoints
Tests all 12 router modules after refactoring from monolithic server.py
"""
import pytest
import requests
import os
from datetime import datetime

# Use the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://remora-crawler.preview.emergentagent.com').rstrip('/')

# Test credentials - freshly created
TEST_SESSION_TOKEN = "test_session_1774043284255"
TEST_USER_ID = "test-user-1774043284255"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client):
    """Session with auth header (Bearer token)"""
    api_client.headers.update({"Authorization": f"Bearer {TEST_SESSION_TOKEN}"})
    return api_client


# ==================== MISC ROUTES (server.py) ====================

class TestMiscRoutes:
    """Test routes kept in server.py: /, /health, /seed"""
    
    def test_root_returns_api_docs(self, api_client):
        """GET /api/ should return API documentation"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "Remora API"
        assert "endpoints" in data
        assert "search" in data["endpoints"]
    
    def test_health_check(self, api_client):
        """GET /api/health should return healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    def test_seed_sample_data(self, api_client):
        """POST /api/seed should seed sample content"""
        response = api_client.post(f"{BASE_URL}/api/seed")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Seeded" in data["message"]


# ==================== AUTH ROUTER ====================

class TestAuthRouter:
    """Test /api/auth/* endpoints"""
    
    def test_auth_me_requires_auth(self, api_client):
        """GET /api/auth/me should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
    
    def test_auth_me_returns_user(self, authenticated_client):
        """GET /api/auth/me should return current user"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
    
    def test_auth_logout(self, authenticated_client):
        """POST /api/auth/logout should clear session"""
        response = authenticated_client.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Logged out" in data["message"]


# ==================== KEYS ROUTER ====================

class TestKeysRouter:
    """Test /api/keys/* endpoints"""
    
    def test_list_keys_requires_auth(self, api_client):
        """GET /api/keys should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/keys")
        assert response.status_code == 401
    
    def test_list_keys(self, authenticated_client):
        """GET /api/keys should return list of API keys"""
        response = authenticated_client.get(f"{BASE_URL}/api/keys")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_and_delete_key(self, authenticated_client):
        """POST /api/keys should create API key, DELETE should revoke it"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/keys",
            json={"name": "TEST_router_test_key"}
        )
        assert create_response.status_code == 200
        data = create_response.json()
        assert "key_id" in data
        assert "api_key" in data
        assert data["api_key"].startswith("rmr_")
        
        key_id = data["key_id"]
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/keys/{key_id}")
        assert delete_response.status_code == 200
        assert "revoked" in delete_response.json().get("message", "").lower()


# ==================== AGENTS ROUTER ====================

class TestAgentsRouter:
    """Test /api/agents/* endpoints"""
    
    def test_list_agents_requires_auth(self, api_client):
        """GET /api/agents should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 401
    
    def test_list_agents(self, authenticated_client):
        """GET /api/agents should return list of agents"""
        response = authenticated_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_agent_crud(self, authenticated_client):
        """Test full CRUD for agents"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/agents",
            json={
                "name": "TEST_Agent",
                "description": "Test agent for E2E testing",
                "capabilities": ["search", "crawl"]
            }
        )
        assert create_response.status_code == 200
        agent = create_response.json()
        assert "agent_id" in agent
        assert agent["name"] == "TEST_Agent"
        
        agent_id = agent["agent_id"]
        
        # Update
        update_response = authenticated_client.put(
            f"{BASE_URL}/api/agents/{agent_id}",
            json={"name": "TEST_Agent_Updated", "description": "Updated description"}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "TEST_Agent_Updated"
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/agents/{agent_id}")
        assert delete_response.status_code == 200


# ==================== WEBHOOKS ROUTER ====================

class TestWebhooksRouter:
    """Test /api/webhooks/* endpoints"""
    
    def test_list_webhooks_requires_auth(self, api_client):
        """GET /api/webhooks should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/webhooks")
        assert response.status_code == 401
    
    def test_list_webhooks(self, authenticated_client):
        """GET /api/webhooks should return list of webhooks"""
        response = authenticated_client.get(f"{BASE_URL}/api/webhooks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_webhook_crud(self, authenticated_client):
        """Test full CRUD for webhooks"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/webhooks",
            json={
                "name": "TEST_Webhook",
                "url": "https://example.com/webhook",
                "events": ["content.new", "search.complete"]
            }
        )
        assert create_response.status_code == 200
        webhook = create_response.json()
        assert "webhook_id" in webhook
        assert webhook["name"] == "TEST_Webhook"
        
        webhook_id = webhook["webhook_id"]
        
        # Update
        update_response = authenticated_client.put(
            f"{BASE_URL}/api/webhooks/{webhook_id}",
            json={"name": "TEST_Webhook_Updated"}
        )
        assert update_response.status_code == 200
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/webhooks/{webhook_id}")
        assert delete_response.status_code == 200
    
    def test_webhook_deliveries(self, authenticated_client):
        """GET /api/webhooks/deliveries should return delivery logs"""
        response = authenticated_client.get(f"{BASE_URL}/api/webhooks/deliveries")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_webhook_delivery_stats(self, authenticated_client):
        """GET /api/webhooks/deliveries/stats should return stats"""
        response = authenticated_client.get(f"{BASE_URL}/api/webhooks/deliveries/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "success" in data
        assert "failed" in data
        assert "success_rate" in data


# ==================== SEARCH ROUTER ====================

class TestSearchRouter:
    """Test /api/search endpoint"""
    
    def test_search_requires_api_key(self, api_client):
        """POST /api/search should require API key"""
        response = api_client.post(
            f"{BASE_URL}/api/search",
            json={"query": "test", "max_results": 5}
        )
        assert response.status_code == 401
    
    def test_search_with_api_key(self, authenticated_client, api_client):
        """POST /api/search should work with valid API key"""
        # First seed data
        api_client.post(f"{BASE_URL}/api/seed")
        
        # Create API key
        key_response = authenticated_client.post(
            f"{BASE_URL}/api/keys",
            json={"name": "TEST_search_key"}
        )
        assert key_response.status_code == 200
        api_key = key_response.json()["api_key"]
        key_id = key_response.json()["key_id"]
        
        # Search
        search_response = api_client.post(
            f"{BASE_URL}/api/search",
            json={"query": "python async", "max_results": 5},
            headers={"X-API-Key": api_key}
        )
        assert search_response.status_code == 200
        data = search_response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert "processing_time_ms" in data
        
        # Cleanup
        authenticated_client.delete(f"{BASE_URL}/api/keys/{key_id}")


# ==================== CRAWL ROUTER ====================

class TestCrawlRouter:
    """Test /api/crawl/* and /api/content/* endpoints"""
    
    def test_list_content_requires_auth(self, api_client):
        """GET /api/content should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/content")
        assert response.status_code == 401
    
    def test_list_content(self, authenticated_client):
        """GET /api/content should return list of crawled content"""
        response = authenticated_client.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_crawl_jobs(self, authenticated_client):
        """GET /api/crawl/jobs should return list of crawl jobs"""
        response = authenticated_client.get(f"{BASE_URL}/api/crawl/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_scheduled_crawls(self, authenticated_client):
        """GET /api/crawl/schedule should return list of scheduled crawls"""
        response = authenticated_client.get(f"{BASE_URL}/api/crawl/schedule")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_crawl_history(self, authenticated_client):
        """GET /api/crawl/history should return crawl history"""
        response = authenticated_client.get(f"{BASE_URL}/api/crawl/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_crawl_history_stats(self, authenticated_client):
        """GET /api/crawl/history/stats should return stats (path conflict test)"""
        response = authenticated_client.get(f"{BASE_URL}/api/crawl/history/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_crawls" in data
        assert "successful" in data
        assert "failed" in data
        assert "success_rate" in data


# ==================== SOURCES ROUTER ====================

class TestSourcesRouter:
    """Test /api/sources/* endpoints"""
    
    def test_list_sources_requires_auth(self, api_client):
        """GET /api/sources should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/sources")
        assert response.status_code == 401
    
    def test_list_sources(self, authenticated_client):
        """GET /api/sources should return list of content sources"""
        response = authenticated_client.get(f"{BASE_URL}/api/sources")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== ANALYTICS ROUTER ====================

class TestAnalyticsRouter:
    """Test /api/usage/* endpoints"""
    
    def test_usage_stats_requires_auth(self, api_client):
        """GET /api/usage/stats should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/usage/stats")
        assert response.status_code == 401
    
    def test_usage_stats(self, authenticated_client):
        """GET /api/usage/stats should return usage statistics"""
        response = authenticated_client.get(f"{BASE_URL}/api/usage/stats")
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "this_week" in data
        assert "this_month" in data
        assert "total" in data
    
    def test_recent_usage(self, authenticated_client):
        """GET /api/usage/recent should return recent usage records"""
        response = authenticated_client.get(f"{BASE_URL}/api/usage/recent")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== RULES ROUTER ====================

class TestRulesRouter:
    """Test /api/rules/* endpoints"""
    
    def test_list_rules_requires_auth(self, api_client):
        """GET /api/rules should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/rules")
        assert response.status_code == 401
    
    def test_list_rules(self, authenticated_client):
        """GET /api/rules should return list of crawl rules"""
        response = authenticated_client.get(f"{BASE_URL}/api/rules")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_rule_crud(self, authenticated_client):
        """Test full CRUD for crawl rules"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/rules",
            json={
                "domain": "test-domain-unique-123.com",
                "name": "TEST_Rule",
                "title_selector": "h1",
                "content_selector": "article"
            }
        )
        assert create_response.status_code == 200
        rule = create_response.json()
        assert "rule_id" in rule
        
        rule_id = rule["rule_id"]
        
        # Get
        get_response = authenticated_client.get(f"{BASE_URL}/api/rules/{rule_id}")
        assert get_response.status_code == 200
        
        # Update
        update_response = authenticated_client.put(
            f"{BASE_URL}/api/rules/{rule_id}",
            json={"name": "TEST_Rule_Updated"}
        )
        assert update_response.status_code == 200
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/rules/{rule_id}")
        assert delete_response.status_code == 200
    
    def test_duplicate_domain_rule_rejected(self, authenticated_client):
        """POST /api/rules should reject duplicate domain"""
        # Create first rule
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/rules",
            json={
                "domain": "duplicate-test-domain.com",
                "name": "TEST_First_Rule"
            }
        )
        assert create_response.status_code == 200
        rule_id = create_response.json()["rule_id"]
        
        # Try to create duplicate
        duplicate_response = authenticated_client.post(
            f"{BASE_URL}/api/rules",
            json={
                "domain": "duplicate-test-domain.com",
                "name": "TEST_Duplicate_Rule"
            }
        )
        assert duplicate_response.status_code == 400
        
        # Cleanup
        authenticated_client.delete(f"{BASE_URL}/api/rules/{rule_id}")


# ==================== RANKING ROUTER ====================

class TestRankingRouter:
    """Test /api/ranking/* endpoints"""
    
    def test_list_ranking_requires_auth(self, api_client):
        """GET /api/ranking should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/ranking")
        assert response.status_code == 401
    
    def test_list_ranking(self, authenticated_client):
        """GET /api/ranking should return list of ranking configs"""
        response = authenticated_client.get(f"{BASE_URL}/api/ranking")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_ranking_crud(self, authenticated_client):
        """Test full CRUD for ranking configs"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/ranking",
            json={
                "name": "TEST_Ranking_Config",
                "title_weight": 2.5,
                "boosted_domains": ["example.com"]
            }
        )
        assert create_response.status_code == 200
        config = create_response.json()
        assert "config_id" in config
        
        config_id = config["config_id"]
        
        # Get
        get_response = authenticated_client.get(f"{BASE_URL}/api/ranking/{config_id}")
        assert get_response.status_code == 200
        
        # Update
        update_response = authenticated_client.put(
            f"{BASE_URL}/api/ranking/{config_id}",
            json={"name": "TEST_Ranking_Config_Updated", "title_weight": 3.0}
        )
        assert update_response.status_code == 200
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/ranking/{config_id}")
        assert delete_response.status_code == 200


# ==================== ORGS ROUTER ====================

class TestOrgsRouter:
    """Test /api/orgs/* endpoints"""
    
    def test_list_orgs_requires_auth(self, api_client):
        """GET /api/orgs should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/orgs")
        assert response.status_code == 401
    
    def test_list_orgs(self, authenticated_client):
        """GET /api/orgs should return list of organizations"""
        response = authenticated_client.get(f"{BASE_URL}/api/orgs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_pending_invites_path_conflict(self, authenticated_client):
        """GET /api/orgs/invites/pending should work (path conflict test)"""
        response = authenticated_client.get(f"{BASE_URL}/api/orgs/invites/pending")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_org_crud(self, authenticated_client):
        """Test full CRUD for organizations"""
        # Create
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/orgs",
            json={"name": "TEST_Organization"}
        )
        assert create_response.status_code == 200
        org = create_response.json()
        assert "org_id" in org
        assert "slug" in org
        assert org["role"] == "owner"
        
        org_id = org["org_id"]
        
        # Get
        get_response = authenticated_client.get(f"{BASE_URL}/api/orgs/{org_id}")
        assert get_response.status_code == 200
        
        # List members
        members_response = authenticated_client.get(f"{BASE_URL}/api/orgs/{org_id}/members")
        assert members_response.status_code == 200
        members = members_response.json()
        assert isinstance(members, list)
        assert len(members) >= 1  # At least the owner
        
        # Delete
        delete_response = authenticated_client.delete(f"{BASE_URL}/api/orgs/{org_id}")
        assert delete_response.status_code == 200


# ==================== BILLING ROUTER ====================

class TestBillingRouter:
    """Test /api/billing/* endpoints"""
    
    def test_billing_plans_public(self, api_client):
        """GET /api/billing/plans should be public"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 5
        plan_ids = [p["plan_id"] for p in plans]
        assert "free" in plan_ids
        assert "enterprise" in plan_ids
    
    def test_billing_usage_requires_auth(self, api_client):
        """GET /api/billing/usage should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/billing/usage")
        assert response.status_code == 401
    
    def test_billing_usage(self, authenticated_client):
        """GET /api/billing/usage should return credit balance"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/usage")
        assert response.status_code == 200
        data = response.json()
        assert "plan" in data
        assert "credits_remaining" in data
        assert "credits_used" in data
    
    def test_billing_transactions(self, authenticated_client):
        """GET /api/billing/transactions should return transaction list"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/transactions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== CLEANUP ====================

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, authenticated_client):
        """Delete all TEST_ prefixed data"""
        # Cleanup API keys
        keys_response = authenticated_client.get(f"{BASE_URL}/api/keys")
        if keys_response.status_code == 200:
            for key in keys_response.json():
                if key.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/keys/{key['key_id']}")
        
        # Cleanup agents
        agents_response = authenticated_client.get(f"{BASE_URL}/api/agents")
        if agents_response.status_code == 200:
            for agent in agents_response.json():
                if agent.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/agents/{agent['agent_id']}")
        
        # Cleanup webhooks
        webhooks_response = authenticated_client.get(f"{BASE_URL}/api/webhooks")
        if webhooks_response.status_code == 200:
            for webhook in webhooks_response.json():
                if webhook.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/webhooks/{webhook['webhook_id']}")
        
        # Cleanup rules
        rules_response = authenticated_client.get(f"{BASE_URL}/api/rules")
        if rules_response.status_code == 200:
            for rule in rules_response.json():
                if rule.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/rules/{rule['rule_id']}")
        
        # Cleanup ranking configs
        ranking_response = authenticated_client.get(f"{BASE_URL}/api/ranking")
        if ranking_response.status_code == 200:
            for config in ranking_response.json():
                if config.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/ranking/{config['config_id']}")
        
        # Cleanup orgs
        orgs_response = authenticated_client.get(f"{BASE_URL}/api/orgs")
        if orgs_response.status_code == 200:
            for org in orgs_response.json():
                if org.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/orgs/{org['org_id']}")
        
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
