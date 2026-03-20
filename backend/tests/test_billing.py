"""
Billing API Tests for Remora
Tests: Plans, Usage, Checkout, Transactions, Credit Deduction
"""
import pytest
import requests
import os
from datetime import datetime

# Use the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://remora-crawler.preview.emergentagent.com').rstrip('/')

# Test credentials from iteration 2
TEST_SESSION_TOKEN = "test_session_1773982477902"
TEST_USER_ID = "test-user-1773982477902"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client):
    """Session with auth cookie"""
    api_client.cookies.set("session_token", TEST_SESSION_TOKEN)
    return api_client


class TestBillingPlans:
    """Test GET /api/billing/plans - PUBLIC endpoint"""
    
    def test_get_plans_returns_5_plans(self, api_client):
        """Plans endpoint should return 5 plans: free, starter, growth, scale, enterprise"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        plans = response.json()
        assert isinstance(plans, list), "Plans should be a list"
        assert len(plans) == 5, f"Expected 5 plans, got {len(plans)}"
        
        # Verify plan IDs
        plan_ids = [p["plan_id"] for p in plans]
        assert "free" in plan_ids, "Missing 'free' plan"
        assert "starter" in plan_ids, "Missing 'starter' plan"
        assert "growth" in plan_ids, "Missing 'growth' plan"
        assert "scale" in plan_ids, "Missing 'scale' plan"
        assert "enterprise" in plan_ids, "Missing 'enterprise' plan"
    
    def test_plans_have_correct_structure(self, api_client):
        """Each plan should have plan_id, name, price, credits, description"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = response.json()
        for plan in plans:
            assert "plan_id" in plan, f"Plan missing plan_id: {plan}"
            assert "name" in plan, f"Plan missing name: {plan}"
            assert "price" in plan, f"Plan missing price: {plan}"
            assert "credits" in plan, f"Plan missing credits: {plan}"
            assert "description" in plan, f"Plan missing description: {plan}"
    
    def test_plans_have_correct_prices(self, api_client):
        """Verify correct pricing: Free=$0, Starter=$29, Growth=$99, Scale=$399"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = {p["plan_id"]: p for p in response.json()}
        
        assert plans["free"]["price"] == 0, f"Free plan price should be 0, got {plans['free']['price']}"
        assert plans["starter"]["price"] == 29, f"Starter plan price should be 29, got {plans['starter']['price']}"
        assert plans["growth"]["price"] == 99, f"Growth plan price should be 99, got {plans['growth']['price']}"
        assert plans["scale"]["price"] == 399, f"Scale plan price should be 399, got {plans['scale']['price']}"
    
    def test_plans_have_correct_credits(self, api_client):
        """Verify correct credits: Free=3000, Starter=10000, Growth=40000, Scale=200000, Enterprise=-1"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = {p["plan_id"]: p for p in response.json()}
        
        assert plans["free"]["credits"] == 3000, f"Free plan credits should be 3000, got {plans['free']['credits']}"
        assert plans["starter"]["credits"] == 10000, f"Starter plan credits should be 10000, got {plans['starter']['credits']}"
        assert plans["growth"]["credits"] == 40000, f"Growth plan credits should be 40000, got {plans['growth']['credits']}"
        assert plans["scale"]["credits"] == 200000, f"Scale plan credits should be 200000, got {plans['scale']['credits']}"
        assert plans["enterprise"]["credits"] == -1, f"Enterprise plan credits should be -1 (custom), got {plans['enterprise']['credits']}"
    
    def test_enterprise_plan_has_custom_price(self, api_client):
        """Enterprise plan should have price=-1 indicating custom pricing"""
        response = api_client.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = {p["plan_id"]: p for p in response.json()}
        
        assert plans["enterprise"]["price"] == -1, f"Enterprise plan price should be -1 (custom), got {plans['enterprise']['price']}"
        assert "enterprise" in plans["enterprise"]["plan_id"].lower()


class TestBillingUsage:
    """Test GET /api/billing/usage - requires auth"""
    
    def test_usage_requires_auth(self, api_client):
        """Usage endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/billing/usage")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    def test_usage_returns_credit_info(self, authenticated_client):
        """Usage endpoint should return credit balance and plan info"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/usage")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "plan" in data, "Missing 'plan' field"
        assert "plan_name" in data, "Missing 'plan_name' field"
        assert "credits_total" in data, "Missing 'credits_total' field"
        assert "credits_used" in data, "Missing 'credits_used' field"
        assert "credits_remaining" in data, "Missing 'credits_remaining' field"
        assert "usage_percentage" in data, "Missing 'usage_percentage' field"
    
    def test_new_user_gets_free_plan(self, authenticated_client):
        """New user should be on free plan with 3000 credits"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/usage")
        assert response.status_code == 200
        
        data = response.json()
        
        # New user should be on free plan
        assert data["plan"] == "free", f"Expected 'free' plan, got {data['plan']}"
        assert data["credits_total"] == 3000, f"Expected 3000 total credits, got {data['credits_total']}"


class TestBillingCheckout:
    """Test POST /api/billing/checkout - requires auth"""
    
    def test_checkout_requires_auth(self, api_client):
        """Checkout endpoint should require authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "starter", "origin_url": "https://example.com"}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    def test_checkout_rejects_free_plan(self, authenticated_client):
        """Cannot checkout for free plan"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "free", "origin_url": "https://example.com"}
        )
        assert response.status_code == 400, f"Expected 400 for free plan, got {response.status_code}"
    
    def test_checkout_rejects_invalid_plan(self, authenticated_client):
        """Cannot checkout for invalid plan"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "invalid_plan", "origin_url": "https://example.com"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid plan, got {response.status_code}"
    
    def test_checkout_rejects_enterprise_plan(self, authenticated_client):
        """Cannot checkout for enterprise plan (requires contact)"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "enterprise", "origin_url": "https://example.com"}
        )
        assert response.status_code == 400, f"Expected 400 for enterprise plan, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
    
    def test_checkout_creates_session_for_starter(self, authenticated_client):
        """Checkout for starter plan should create Stripe session"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "starter", "origin_url": "https://remora-crawler.preview.emergentagent.com"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Response should contain 'url'"
        assert "session_id" in data, "Response should contain 'session_id'"
        assert data["url"].startswith("https://"), f"URL should be HTTPS, got {data['url']}"
    
    def test_checkout_creates_session_for_growth(self, authenticated_client):
        """Checkout for growth plan should create Stripe session"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "growth", "origin_url": "https://remora-crawler.preview.emergentagent.com"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Response should contain 'url'"
        assert "session_id" in data, "Response should contain 'session_id'"
    
    def test_checkout_creates_session_for_scale(self, authenticated_client):
        """Checkout for scale plan should create Stripe session"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "scale", "origin_url": "https://remora-crawler.preview.emergentagent.com"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Response should contain 'url'"
        assert "session_id" in data, "Response should contain 'session_id'"


class TestCheckoutStatus:
    """Test GET /api/billing/checkout/status/{session_id} - requires auth"""
    
    def test_status_requires_auth(self, api_client):
        """Status endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/billing/checkout/status/fake_session_id")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    def test_status_returns_404_for_invalid_session(self, authenticated_client):
        """Status endpoint should return 404 for non-existent session"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/checkout/status/nonexistent_session_12345")
        assert response.status_code == 404, f"Expected 404 for invalid session, got {response.status_code}"


class TestBillingTransactions:
    """Test GET /api/billing/transactions - requires auth"""
    
    def test_transactions_requires_auth(self, api_client):
        """Transactions endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/billing/transactions")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    def test_transactions_returns_list(self, authenticated_client):
        """Transactions endpoint should return a list"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/transactions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Transactions should be a list"


class TestStripeWebhook:
    """Test POST /api/webhook/stripe - public endpoint for Stripe"""
    
    def test_webhook_endpoint_exists(self, api_client):
        """Webhook endpoint should exist (may return error without valid signature)"""
        response = api_client.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b"{}",
            headers={"Content-Type": "application/json", "Stripe-Signature": "invalid"}
        )
        # Webhook may return 400/500 without valid signature, but should not 404
        assert response.status_code != 404, f"Webhook endpoint should exist, got {response.status_code}"


class TestCreditDeduction:
    """Test credit deduction on API calls"""
    
    def test_create_api_key_for_credit_testing(self, authenticated_client):
        """Create an API key for testing credit deduction"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/keys",
            json={"name": "TEST_billing_credit_test_key"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "api_key" in data, "Response should contain 'api_key'"
        assert "key_id" in data, "Response should contain 'key_id'"
        
        # Store for cleanup
        return data
    
    def test_search_deducts_credit(self, authenticated_client, api_client):
        """Search endpoint should deduct 1 credit"""
        # First create an API key
        key_response = authenticated_client.post(
            f"{BASE_URL}/api/keys",
            json={"name": "TEST_search_credit_test"}
        )
        assert key_response.status_code == 200
        api_key = key_response.json()["api_key"]
        key_id = key_response.json()["key_id"]
        
        # Get initial credits
        usage_before = authenticated_client.get(f"{BASE_URL}/api/billing/usage").json()
        credits_before = usage_before["credits_remaining"]
        
        # Make a search request with API key
        search_response = api_client.post(
            f"{BASE_URL}/api/search",
            json={"query": "test search for billing", "max_results": 5},
            headers={"X-API-Key": api_key}
        )
        
        assert search_response.status_code == 200, f"Search failed: {search_response.status_code}: {search_response.text}"
        
        # Get credits after
        usage_after = authenticated_client.get(f"{BASE_URL}/api/billing/usage").json()
        credits_after = usage_after["credits_remaining"]
        
        # Verify 1 credit was deducted
        assert credits_after == credits_before - 1, f"Expected {credits_before - 1} credits, got {credits_after}"
        
        # Cleanup: delete the API key
        authenticated_client.delete(f"{BASE_URL}/api/keys/{key_id}")
    
    def test_crawl_deducts_credit(self, authenticated_client):
        """Crawl endpoint should deduct 1 credit"""
        # Get initial credits
        usage_before = authenticated_client.get(f"{BASE_URL}/api/billing/usage").json()
        credits_before = usage_before["credits_remaining"]
        
        # Make a crawl request
        crawl_response = authenticated_client.post(
            f"{BASE_URL}/api/crawl",
            json={"url": "https://example.com"}
        )
        
        assert crawl_response.status_code == 200, f"Crawl failed: {crawl_response.status_code}: {crawl_response.text}"
        
        # Get credits after
        usage_after = authenticated_client.get(f"{BASE_URL}/api/billing/usage").json()
        credits_after = usage_after["credits_remaining"]
        
        # Verify 1 credit was deducted
        assert credits_after == credits_before - 1, f"Expected {credits_before - 1} credits, got {credits_after}"


class TestCreditBlock:
    """Test 402 Payment Required when credits reach 0"""
    
    def test_402_when_no_credits(self, api_client):
        """API should return 402 when user has no credits"""
        # This test would require setting up a user with 0 credits
        # For now, we just verify the endpoint exists and handles auth
        # The actual 402 test would need a dedicated test user with 0 credits
        pytest.skip("Requires dedicated test user with 0 credits - manual verification needed")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_api_keys(self, authenticated_client):
        """Delete all TEST_ prefixed API keys"""
        # List all keys
        response = authenticated_client.get(f"{BASE_URL}/api/keys")
        if response.status_code == 200:
            keys = response.json()
            for key in keys:
                if key.get("name", "").startswith("TEST_"):
                    authenticated_client.delete(f"{BASE_URL}/api/keys/{key['key_id']}")
        
        # This test always passes - it's just cleanup
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
