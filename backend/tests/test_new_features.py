"""
Backend API Tests for New Features:
- Crawl Rules CRUD (/api/rules)
- Search Ranking Configs (/api/ranking)
- Organizations & Teams (/api/orgs)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_1773982477902"
USER_ID = "test-user-1773982477902"

@pytest.fixture(scope="module")
def api_client():
    """Session with authentication via cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestHealthAndAuth:
    """Basic health and auth verification"""

    def test_health_endpoint(self, api_client):
        """Health endpoint should return healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ Health endpoint working")

    def test_auth_me(self, api_client):
        """Auth endpoint should return current user"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["user_id"] == USER_ID
        print(f"✅ Auth working for user: {data['user_id']}")


class TestCrawlRulesCRUD:
    """Crawl Rules CRUD API Tests - /api/rules"""

    def test_list_rules_empty(self, api_client):
        """GET /api/rules - should return empty list initially"""
        response = api_client.get(f"{BASE_URL}/api/rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List rules returned {len(data)} rules")

    def test_create_rule(self, api_client):
        """POST /api/rules - create a crawl rule"""
        payload = {
            "domain": f"TEST_example_{int(time.time())}.com",
            "name": "TEST Example Crawl Rule",
            "title_selector": "h1.title",
            "content_selector": "article.main-content",
            "follow_links": True,
            "max_depth": 2,
            "delay_ms": 500,
            "max_pages": 50
        }
        response = api_client.post(f"{BASE_URL}/api/rules", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response data
        assert "rule_id" in data
        assert data["domain"] == payload["domain"]
        assert data["name"] == payload["name"]
        assert data["title_selector"] == payload["title_selector"]
        assert data["follow_links"] == payload["follow_links"]
        assert data["user_id"] == USER_ID
        
        print(f"✅ Created rule: {data['rule_id']}")
        
        # Store for later tests
        TestCrawlRulesCRUD.created_rule_id = data["rule_id"]
        TestCrawlRulesCRUD.created_rule_domain = payload["domain"]

    def test_get_rule(self, api_client):
        """GET /api/rules/{rule_id} - verify rule persisted"""
        rule_id = getattr(TestCrawlRulesCRUD, 'created_rule_id', None)
        if not rule_id:
            pytest.skip("No rule created to test")
        
        response = api_client.get(f"{BASE_URL}/api/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["rule_id"] == rule_id
        assert data["name"] == "TEST Example Crawl Rule"
        print(f"✅ GET rule verified: {rule_id}")

    def test_update_rule(self, api_client):
        """PUT /api/rules/{rule_id} - update a crawl rule"""
        rule_id = getattr(TestCrawlRulesCRUD, 'created_rule_id', None)
        if not rule_id:
            pytest.skip("No rule created to test")
        
        update_payload = {
            "name": "TEST Updated Rule Name",
            "max_depth": 3,
            "delay_ms": 1000
        }
        response = api_client.put(f"{BASE_URL}/api/rules/{rule_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["name"] == "TEST Updated Rule Name"
        assert data["max_depth"] == 3
        print(f"✅ Updated rule: {rule_id}")
        
        # Verify with GET
        get_response = api_client.get(f"{BASE_URL}/api/rules/{rule_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["name"] == "TEST Updated Rule Name"
        print("✅ Update persisted correctly")

    def test_delete_rule(self, api_client):
        """DELETE /api/rules/{rule_id} - delete a crawl rule"""
        rule_id = getattr(TestCrawlRulesCRUD, 'created_rule_id', None)
        if not rule_id:
            pytest.skip("No rule created to test")
        
        response = api_client.delete(f"{BASE_URL}/api/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✅ Deleted rule: {rule_id}")
        
        # Verify deletion with GET
        get_response = api_client.get(f"{BASE_URL}/api/rules/{rule_id}")
        assert get_response.status_code == 404
        print("✅ Rule deletion verified (404 on GET)")


class TestSearchRankingCRUD:
    """Search Ranking Configuration CRUD API Tests - /api/ranking"""

    def test_list_ranking_empty(self, api_client):
        """GET /api/ranking - should return list"""
        response = api_client.get(f"{BASE_URL}/api/ranking")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List ranking configs returned {len(data)} configs")

    def test_create_ranking_config(self, api_client):
        """POST /api/ranking - create a ranking configuration"""
        payload = {
            "name": f"TEST Ranking Config {int(time.time())}",
            "title_weight": 2.5,
            "description_weight": 1.5,
            "content_weight": 1.0,
            "recency_boost": True,
            "recency_decay_days": 30,
            "boosted_domains": ["docs.python.org", "mdn.mozilla.org"],
            "penalized_domains": [],
            "domain_boost_factor": 1.5,
            "preferred_types": ["documentation", "tutorial"],
            "type_boost_factor": 1.3,
            "is_default": False
        }
        response = api_client.post(f"{BASE_URL}/api/ranking", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response data
        assert "config_id" in data
        assert data["name"] == payload["name"]
        assert data["title_weight"] == payload["title_weight"]
        assert data["recency_boost"] == payload["recency_boost"]
        assert data["user_id"] == USER_ID
        
        print(f"✅ Created ranking config: {data['config_id']}")
        TestSearchRankingCRUD.created_config_id = data["config_id"]

    def test_get_ranking_config(self, api_client):
        """GET /api/ranking/{config_id} - verify config persisted"""
        config_id = getattr(TestSearchRankingCRUD, 'created_config_id', None)
        if not config_id:
            pytest.skip("No config created to test")
        
        response = api_client.get(f"{BASE_URL}/api/ranking/{config_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["config_id"] == config_id
        assert data["title_weight"] == 2.5
        print(f"✅ GET ranking config verified: {config_id}")

    def test_update_ranking_config(self, api_client):
        """PUT /api/ranking/{config_id} - update a ranking configuration"""
        config_id = getattr(TestSearchRankingCRUD, 'created_config_id', None)
        if not config_id:
            pytest.skip("No config created to test")
        
        update_payload = {
            "name": "TEST Updated Ranking Config",
            "title_weight": 3.0,
            "description_weight": 2.0,
            "content_weight": 1.5,
            "recency_boost": False,
            "recency_decay_days": 60,
            "boosted_domains": ["docs.python.org"],
            "penalized_domains": ["spam.com"],
            "domain_boost_factor": 2.0,
            "preferred_types": ["api"],
            "type_boost_factor": 1.5,
            "is_default": False
        }
        response = api_client.put(f"{BASE_URL}/api/ranking/{config_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["name"] == "TEST Updated Ranking Config"
        assert data["title_weight"] == 3.0
        print(f"✅ Updated ranking config: {config_id}")
        
        # Verify with GET
        get_response = api_client.get(f"{BASE_URL}/api/ranking/{config_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["name"] == "TEST Updated Ranking Config"
        print("✅ Ranking config update persisted correctly")

    def test_delete_ranking_config(self, api_client):
        """DELETE /api/ranking/{config_id} - delete a ranking configuration"""
        config_id = getattr(TestSearchRankingCRUD, 'created_config_id', None)
        if not config_id:
            pytest.skip("No config created to test")
        
        response = api_client.delete(f"{BASE_URL}/api/ranking/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✅ Deleted ranking config: {config_id}")
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/ranking/{config_id}")
        assert get_response.status_code == 404
        print("✅ Ranking config deletion verified")


class TestOrganizationsCRUD:
    """Organizations & Teams API Tests - /api/orgs"""

    def test_list_orgs_empty(self, api_client):
        """GET /api/orgs - should return list"""
        response = api_client.get(f"{BASE_URL}/api/orgs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List organizations returned {len(data)} orgs")

    def test_pending_invites_route(self, api_client):
        """GET /api/orgs/invites/pending - CRITICAL: static route must work before /{org_id}"""
        response = api_client.get(f"{BASE_URL}/api/orgs/invites/pending")
        # This should NOT return 403 "Not a member" or 404 "Organization not found"
        # It should return 200 with an array (empty or with invites)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Pending invites route working correctly, returned {len(data)} invites")

    def test_create_organization(self, api_client):
        """POST /api/orgs - create an organization"""
        payload = {
            "name": f"TEST Org {int(time.time())}"
        }
        response = api_client.post(f"{BASE_URL}/api/orgs", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response data
        assert "org_id" in data
        assert "slug" in data
        assert data["name"] == payload["name"]
        assert data["owner_id"] == USER_ID
        assert data["role"] == "owner"
        
        print(f"✅ Created organization: {data['org_id']} (slug: {data['slug']})")
        TestOrganizationsCRUD.created_org_id = data["org_id"]

    def test_get_organization(self, api_client):
        """GET /api/orgs/{org_id} - verify org persisted"""
        org_id = getattr(TestOrganizationsCRUD, 'created_org_id', None)
        if not org_id:
            pytest.skip("No org created to test")
        
        response = api_client.get(f"{BASE_URL}/api/orgs/{org_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["org_id"] == org_id
        assert data["role"] == "owner"
        print(f"✅ GET org verified: {org_id}")

    def test_list_org_members(self, api_client):
        """GET /api/orgs/{org_id}/members - list org members"""
        org_id = getattr(TestOrganizationsCRUD, 'created_org_id', None)
        if not org_id:
            pytest.skip("No org created to test")
        
        response = api_client.get(f"{BASE_URL}/api/orgs/{org_id}/members")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1  # Owner should be a member
        
        # Verify owner is in members
        owner_found = any(m.get("user_id") == USER_ID and m.get("role") == "owner" for m in data)
        assert owner_found, "Owner should be in members list"
        print(f"✅ List org members returned {len(data)} members")

    def test_invite_member(self, api_client):
        """POST /api/orgs/{org_id}/invite - invite a member"""
        org_id = getattr(TestOrganizationsCRUD, 'created_org_id', None)
        if not org_id:
            pytest.skip("No org created to test")
        
        payload = {
            "email": f"invited_{int(time.time())}@example.com",
            "role": "member"
        }
        response = api_client.post(f"{BASE_URL}/api/orgs/{org_id}/invite", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "invite_id" in data
        assert data["email"] == payload["email"]
        assert data["role"] == payload["role"]
        print(f"✅ Invited member: {data['invite_id']}")

    def test_delete_organization(self, api_client):
        """DELETE /api/orgs/{org_id} - delete org (owner only)"""
        org_id = getattr(TestOrganizationsCRUD, 'created_org_id', None)
        if not org_id:
            pytest.skip("No org created to test")
        
        response = api_client.delete(f"{BASE_URL}/api/orgs/{org_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✅ Deleted organization: {org_id}")
        
        # Verify deletion - should return 403 (not a member) or 404 (not found)
        get_response = api_client.get(f"{BASE_URL}/api/orgs/{org_id}")
        assert get_response.status_code in [403, 404]
        print("✅ Organization deletion verified")


class TestEdgeCases:
    """Edge case tests for the new features"""

    def test_duplicate_domain_rule(self, api_client):
        """POST /api/rules - duplicate domain should fail"""
        domain = f"TEST_duplicate_{int(time.time())}.com"
        payload = {
            "domain": domain,
            "name": "TEST First Rule"
        }
        # Create first rule
        response1 = api_client.post(f"{BASE_URL}/api/rules", json=payload)
        assert response1.status_code == 200
        rule_id = response1.json()["rule_id"]
        
        # Try to create duplicate
        payload["name"] = "TEST Duplicate Rule"
        response2 = api_client.post(f"{BASE_URL}/api/rules", json=payload)
        assert response2.status_code == 400
        print("✅ Duplicate domain correctly rejected")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/rules/{rule_id}")

    def test_default_ranking_config(self, api_client):
        """Setting a config as default should unset other defaults"""
        # Create first config as default
        payload1 = {
            "name": f"TEST Default Config 1 {int(time.time())}",
            "title_weight": 2.0,
            "description_weight": 1.5,
            "content_weight": 1.0,
            "recency_boost": True,
            "recency_decay_days": 30,
            "boosted_domains": [],
            "penalized_domains": [],
            "domain_boost_factor": 1.5,
            "preferred_types": [],
            "type_boost_factor": 1.3,
            "is_default": True
        }
        response1 = api_client.post(f"{BASE_URL}/api/ranking", json=payload1)
        assert response1.status_code == 200
        config1_id = response1.json()["config_id"]
        assert response1.json()["is_default"] == True
        
        # Create second config as default
        payload2 = payload1.copy()
        payload2["name"] = f"TEST Default Config 2 {int(time.time())}"
        response2 = api_client.post(f"{BASE_URL}/api/ranking", json=payload2)
        assert response2.status_code == 200
        config2_id = response2.json()["config_id"]
        
        # Verify first config is no longer default
        get_response = api_client.get(f"{BASE_URL}/api/ranking/{config1_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_default"] == False
        print("✅ Default ranking config logic working correctly")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/ranking/{config1_id}")
        api_client.delete(f"{BASE_URL}/api/ranking/{config2_id}")

    def test_non_owner_cannot_delete_org(self, api_client):
        """Non-owner should not be able to delete organization"""
        # This test would require a second user, skipping for now
        print("⚠️ Non-owner delete test skipped (requires second user)")
        pytest.skip("Requires second user for this test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
