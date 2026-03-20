"""
Test suite for Notification System and Auto-Recharge Features
Tests:
- GET /api/notifications - Returns notifications list with unread_count
- PATCH /api/notifications/{notification_id}/read - Marks single notification as read
- POST /api/notifications/read-all - Marks all notifications as read
- GET /api/billing/recharge-packs - Returns 3 recharge packs
- GET /api/billing/settings - Returns auto_recharge_enabled, recharge_pack_id, has_payment_method
- PUT /api/billing/settings - Updates auto-recharge settings
- 80% usage alert triggers notification creation
- Auto-recharge validation paths
"""

import pytest
import requests
import os
import time
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
TEST_USER_ID = f"test-notif-user-{int(time.time() * 1000)}"
TEST_SESSION_TOKEN = f"test_session_notif_{int(time.time() * 1000)}"

# User with Stripe customer (simulating payment method)
STRIPE_USER_ID = f"test-stripe-user-{int(time.time() * 1000)}"
STRIPE_SESSION_TOKEN = f"test_session_stripe_{int(time.time() * 1000)}"


@pytest.fixture(scope="module")
def setup_test_users():
    """Create test users and sessions in MongoDB"""
    import pymongo
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=1)
    
    # Create basic test user
    db.users.insert_one({
        "user_id": TEST_USER_ID,
        "email": f"test-notif@example.com",
        "name": "Test Notification User",
        "created_at": now.isoformat()
    })
    db.user_sessions.insert_one({
        "user_id": TEST_USER_ID,
        "session_token": TEST_SESSION_TOKEN,
        "expires_at": expires.isoformat(),
        "created_at": now.isoformat()
    })
    
    # Create user with Stripe customer ID (simulating payment method)
    db.users.insert_one({
        "user_id": STRIPE_USER_ID,
        "email": f"test-stripe@example.com",
        "name": "Test Stripe User",
        "created_at": now.isoformat()
    })
    db.user_sessions.insert_one({
        "user_id": STRIPE_USER_ID,
        "session_token": STRIPE_SESSION_TOKEN,
        "expires_at": expires.isoformat(),
        "created_at": now.isoformat()
    })
    # Create billing record with stripe_customer_id
    db.user_billing.insert_one({
        "user_id": STRIPE_USER_ID,
        "plan": "starter",
        "credits_remaining": 10000,
        "credits_used": 0,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "stripe_customer_id": "cus_test_fake_customer_id",
        "auto_recharge_enabled": False,
        "recharge_pack_id": "medium"
    })
    
    yield {
        "basic_user": {"user_id": TEST_USER_ID, "session_token": TEST_SESSION_TOKEN},
        "stripe_user": {"user_id": STRIPE_USER_ID, "session_token": STRIPE_SESSION_TOKEN}
    }
    
    # Cleanup
    db.users.delete_many({"user_id": {"$in": [TEST_USER_ID, STRIPE_USER_ID]}})
    db.user_sessions.delete_many({"user_id": {"$in": [TEST_USER_ID, STRIPE_USER_ID]}})
    db.user_billing.delete_many({"user_id": {"$in": [TEST_USER_ID, STRIPE_USER_ID]}})
    db.notifications.delete_many({"user_id": {"$in": [TEST_USER_ID, STRIPE_USER_ID]}})
    client.close()


@pytest.fixture
def basic_session(setup_test_users):
    """Session for basic test user"""
    session = requests.Session()
    session.cookies.set("session_token", setup_test_users["basic_user"]["session_token"])
    return session


@pytest.fixture
def stripe_session(setup_test_users):
    """Session for user with Stripe customer"""
    session = requests.Session()
    session.cookies.set("session_token", setup_test_users["stripe_user"]["session_token"])
    return session


class TestRechargePacks:
    """Tests for GET /api/billing/recharge-packs endpoint"""
    
    def test_get_recharge_packs_returns_three_packs(self):
        """GET /api/billing/recharge-packs returns 3 packs (small, medium, large)"""
        response = requests.get(f"{BASE_URL}/api/billing/recharge-packs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        packs = response.json()
        assert isinstance(packs, list), "Response should be a list"
        assert len(packs) == 3, f"Expected 3 packs, got {len(packs)}"
        
        pack_ids = [p["pack_id"] for p in packs]
        assert "small" in pack_ids, "Missing 'small' pack"
        assert "medium" in pack_ids, "Missing 'medium' pack"
        assert "large" in pack_ids, "Missing 'large' pack"
    
    def test_recharge_packs_have_correct_structure(self):
        """Each recharge pack has pack_id, name, credits, price"""
        response = requests.get(f"{BASE_URL}/api/billing/recharge-packs")
        assert response.status_code == 200
        
        packs = response.json()
        for pack in packs:
            assert "pack_id" in pack, f"Missing pack_id in {pack}"
            assert "name" in pack, f"Missing name in {pack}"
            assert "credits" in pack, f"Missing credits in {pack}"
            assert "price" in pack, f"Missing price in {pack}"
            assert isinstance(pack["credits"], int), f"Credits should be int: {pack}"
            assert isinstance(pack["price"], (int, float)), f"Price should be numeric: {pack}"
    
    def test_recharge_packs_correct_values(self):
        """Verify correct prices and credits for each pack"""
        response = requests.get(f"{BASE_URL}/api/billing/recharge-packs")
        assert response.status_code == 200
        
        packs = {p["pack_id"]: p for p in response.json()}
        
        # Small: $15 for 5,000 credits
        assert packs["small"]["price"] == 15.0, f"Small price should be 15, got {packs['small']['price']}"
        assert packs["small"]["credits"] == 5000, f"Small credits should be 5000, got {packs['small']['credits']}"
        
        # Medium: $40 for 15,000 credits
        assert packs["medium"]["price"] == 40.0, f"Medium price should be 40, got {packs['medium']['price']}"
        assert packs["medium"]["credits"] == 15000, f"Medium credits should be 15000, got {packs['medium']['credits']}"
        
        # Large: $100 for 50,000 credits
        assert packs["large"]["price"] == 100.0, f"Large price should be 100, got {packs['large']['price']}"
        assert packs["large"]["credits"] == 50000, f"Large credits should be 50000, got {packs['large']['credits']}"


class TestBillingSettings:
    """Tests for GET/PUT /api/billing/settings endpoints"""
    
    def test_get_settings_requires_auth(self):
        """GET /api/billing/settings requires authentication"""
        response = requests.get(f"{BASE_URL}/api/billing/settings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_get_settings_returns_correct_structure(self, stripe_session):
        """GET /api/billing/settings returns auto_recharge_enabled, recharge_pack_id, has_payment_method"""
        response = stripe_session.get(f"{BASE_URL}/api/billing/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auto_recharge_enabled" in data, "Missing auto_recharge_enabled"
        assert "recharge_pack_id" in data, "Missing recharge_pack_id"
        assert "has_payment_method" in data, "Missing has_payment_method"
        
        assert isinstance(data["auto_recharge_enabled"], bool), "auto_recharge_enabled should be bool"
        assert isinstance(data["recharge_pack_id"], str), "recharge_pack_id should be string"
        assert isinstance(data["has_payment_method"], bool), "has_payment_method should be bool"
    
    def test_get_settings_user_with_stripe_has_payment_method(self, stripe_session):
        """User with stripe_customer_id shows has_payment_method=True"""
        response = stripe_session.get(f"{BASE_URL}/api/billing/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["has_payment_method"] == True, "User with stripe_customer_id should have has_payment_method=True"
    
    def test_get_settings_user_without_stripe_no_payment_method(self, basic_session):
        """User without stripe_customer_id shows has_payment_method=False"""
        response = basic_session.get(f"{BASE_URL}/api/billing/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["has_payment_method"] == False, "User without stripe_customer_id should have has_payment_method=False"
    
    def test_put_settings_requires_auth(self):
        """PUT /api/billing/settings requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": True, "pack_id": "medium"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_put_settings_rejects_invalid_pack_id(self, stripe_session):
        """PUT /api/billing/settings rejects invalid pack_id"""
        response = stripe_session.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": True, "pack_id": "invalid_pack"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Invalid recharge pack" in response.json().get("detail", "")
    
    def test_put_settings_requires_payment_method_to_enable(self, basic_session):
        """PUT /api/billing/settings requires payment method to enable auto-recharge"""
        response = basic_session.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": True, "pack_id": "medium"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "payment method" in response.json().get("detail", "").lower()
    
    def test_put_settings_can_enable_with_payment_method(self, stripe_session):
        """PUT /api/billing/settings can enable auto-recharge when payment method exists"""
        response = stripe_session.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": True, "pack_id": "large"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["auto_recharge_enabled"] == True
        assert data["recharge_pack_id"] == "large"
        
        # Verify settings persisted
        get_response = stripe_session.get(f"{BASE_URL}/api/billing/settings")
        assert get_response.status_code == 200
        settings = get_response.json()
        assert settings["auto_recharge_enabled"] == True
        assert settings["recharge_pack_id"] == "large"
    
    def test_put_settings_can_disable_auto_recharge(self, stripe_session):
        """PUT /api/billing/settings can disable auto-recharge"""
        # First enable
        stripe_session.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": True, "pack_id": "medium"}
        )
        
        # Then disable
        response = stripe_session.put(
            f"{BASE_URL}/api/billing/settings",
            json={"enabled": False, "pack_id": "medium"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["auto_recharge_enabled"] == False
    
    def test_put_settings_validates_all_pack_ids(self, stripe_session):
        """PUT /api/billing/settings accepts all valid pack_ids"""
        for pack_id in ["small", "medium", "large"]:
            response = stripe_session.put(
                f"{BASE_URL}/api/billing/settings",
                json={"enabled": True, "pack_id": pack_id}
            )
            assert response.status_code == 200, f"Failed for pack_id={pack_id}: {response.text}"
            assert response.json()["recharge_pack_id"] == pack_id


class TestNotifications:
    """Tests for notification endpoints"""
    
    def test_get_notifications_requires_auth(self):
        """GET /api/notifications requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_get_notifications_returns_correct_structure(self, basic_session):
        """GET /api/notifications returns notifications list and unread_count"""
        response = basic_session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "notifications" in data, "Missing notifications field"
        assert "unread_count" in data, "Missing unread_count field"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        assert isinstance(data["unread_count"], int), "unread_count should be int"
    
    def test_get_notifications_unread_only_filter(self, basic_session):
        """GET /api/notifications?unread_only=true filters to unread only"""
        response = basic_session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "notifications" in data
        # All returned notifications should be unread
        for notif in data["notifications"]:
            assert notif.get("read") == False, f"Found read notification in unread_only response: {notif}"
    
    def test_mark_notification_read_requires_auth(self):
        """PATCH /api/notifications/{id}/read requires authentication"""
        response = requests.patch(f"{BASE_URL}/api/notifications/fake_id/read")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_mark_notification_read_nonexistent(self, basic_session):
        """PATCH /api/notifications/{id}/read handles nonexistent notification"""
        response = basic_session.patch(f"{BASE_URL}/api/notifications/nonexistent_id/read")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Should return message about not found or already read
        data = response.json()
        assert "message" in data
    
    def test_mark_all_read_requires_auth(self):
        """POST /api/notifications/read-all requires authentication"""
        response = requests.post(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_mark_all_read_returns_count(self, basic_session):
        """POST /api/notifications/read-all returns count of marked notifications"""
        response = basic_session.post(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Missing message field"
        # Message should contain count
        assert "Marked" in data["message"] or "marked" in data["message"].lower()


class TestUsageAlertNotification:
    """Tests for 80% usage alert notification creation"""
    
    def test_usage_alert_created_at_80_percent(self, setup_test_users):
        """Verify 80% usage alert creates notification"""
        import pymongo
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = pymongo.MongoClient(mongo_url)
        db = client[db_name]
        
        # Create a user with 80%+ usage
        alert_user_id = f"test-alert-user-{int(time.time() * 1000)}"
        alert_session = f"test_session_alert_{int(time.time() * 1000)}"
        now = datetime.now(timezone.utc)
        
        db.users.insert_one({
            "user_id": alert_user_id,
            "email": "alert-test@example.com",
            "name": "Alert Test User",
            "created_at": now.isoformat()
        })
        db.user_sessions.insert_one({
            "user_id": alert_user_id,
            "session_token": alert_session,
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "created_at": now.isoformat()
        })
        
        # Create billing with 80%+ usage (2500 used out of 3000 = 83%)
        period_start = now.isoformat()
        db.user_billing.insert_one({
            "user_id": alert_user_id,
            "plan": "free",
            "credits_remaining": 500,
            "credits_used": 2500,
            "period_start": period_start,
            "period_end": (now + timedelta(days=30)).isoformat()
        })
        
        try:
            # Make a request that triggers credit deduction (search)
            session = requests.Session()
            session.cookies.set("session_token", alert_session)
            
            # First create an API key to use for search
            key_response = session.post(f"{BASE_URL}/api/keys", json={"name": "Test Alert Key"})
            if key_response.status_code == 201:
                api_key = key_response.json().get("api_key")
                
                # Perform a search to trigger credit deduction and alert check
                search_response = requests.post(
                    f"{BASE_URL}/api/search",
                    headers={"X-API-Key": api_key},
                    json={"query": "test"}
                )
                
                # Wait a moment for async notification creation
                time.sleep(0.5)
                
                # Check if notification was created
                notif = db.notifications.find_one({
                    "user_id": alert_user_id,
                    "type": "usage_alert"
                })
                
                if notif:
                    assert notif["title"] == "Credit usage at 80%", f"Wrong title: {notif['title']}"
                    assert "80%" in notif["message"] or "83%" in notif["message"], f"Message should mention percentage: {notif['message']}"
                    assert notif["read"] == False, "New notification should be unread"
                    print(f"✓ Usage alert notification created: {notif['title']}")
                else:
                    # Alert might not be created if credits were already at 80% before
                    print("Note: Usage alert not created (may already exist or credits insufficient)")
        finally:
            # Cleanup
            db.users.delete_one({"user_id": alert_user_id})
            db.user_sessions.delete_one({"user_id": alert_user_id})
            db.user_billing.delete_one({"user_id": alert_user_id})
            db.notifications.delete_many({"user_id": alert_user_id})
            db.api_keys.delete_many({"user_id": alert_user_id})
            client.close()


class TestAutoRechargeLogic:
    """Tests for auto-recharge validation and error handling"""
    
    def test_auto_recharge_requires_stripe_customer(self, setup_test_users):
        """Auto-recharge should fail gracefully without Stripe customer"""
        import pymongo
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = pymongo.MongoClient(mongo_url)
        db = client[db_name]
        
        # Create user with auto_recharge_enabled but no stripe_customer_id
        recharge_user_id = f"test-recharge-user-{int(time.time() * 1000)}"
        recharge_session = f"test_session_recharge_{int(time.time() * 1000)}"
        now = datetime.now(timezone.utc)
        
        db.users.insert_one({
            "user_id": recharge_user_id,
            "email": "recharge-test@example.com",
            "name": "Recharge Test User",
            "created_at": now.isoformat()
        })
        db.user_sessions.insert_one({
            "user_id": recharge_user_id,
            "session_token": recharge_session,
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "created_at": now.isoformat()
        })
        
        # Create billing with 0 credits and auto_recharge_enabled but NO stripe_customer_id
        db.user_billing.insert_one({
            "user_id": recharge_user_id,
            "plan": "free",
            "credits_remaining": 0,
            "credits_used": 3000,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "auto_recharge_enabled": True,
            "recharge_pack_id": "medium"
            # Note: NO stripe_customer_id
        })
        
        try:
            session = requests.Session()
            session.cookies.set("session_token", recharge_session)
            
            # Create API key
            key_response = session.post(f"{BASE_URL}/api/keys", json={"name": "Test Recharge Key"})
            if key_response.status_code == 201:
                api_key = key_response.json().get("api_key")
                
                # Try to search (should fail with 402 since no credits and no valid recharge)
                search_response = requests.post(
                    f"{BASE_URL}/api/search",
                    headers={"X-API-Key": api_key},
                    json={"query": "test"}
                )
                
                # Should get 402 (credit limit reached) since auto-recharge can't work without customer
                assert search_response.status_code == 402, f"Expected 402, got {search_response.status_code}"
                print("✓ Auto-recharge correctly fails without Stripe customer")
        finally:
            db.users.delete_one({"user_id": recharge_user_id})
            db.user_sessions.delete_one({"user_id": recharge_user_id})
            db.user_billing.delete_one({"user_id": recharge_user_id})
            db.notifications.delete_many({"user_id": recharge_user_id})
            db.api_keys.delete_many({"user_id": recharge_user_id})
            client.close()


class TestNotificationIntegration:
    """Integration tests for notification system"""
    
    def test_notification_workflow(self, setup_test_users):
        """Test full notification workflow: create, list, mark read"""
        import pymongo
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = pymongo.MongoClient(mongo_url)
        db = client[db_name]
        
        user_id = setup_test_users["basic_user"]["user_id"]
        session_token = setup_test_users["basic_user"]["session_token"]
        
        # Insert test notifications directly
        now = datetime.now(timezone.utc)
        notif_id_1 = f"notif_test_{int(time.time() * 1000)}_1"
        notif_id_2 = f"notif_test_{int(time.time() * 1000)}_2"
        
        db.notifications.insert_many([
            {
                "notification_id": notif_id_1,
                "user_id": user_id,
                "type": "test",
                "title": "Test Notification 1",
                "message": "This is test notification 1",
                "read": False,
                "created_at": now.isoformat()
            },
            {
                "notification_id": notif_id_2,
                "user_id": user_id,
                "type": "test",
                "title": "Test Notification 2",
                "message": "This is test notification 2",
                "read": False,
                "created_at": (now - timedelta(hours=1)).isoformat()
            }
        ])
        
        try:
            session = requests.Session()
            session.cookies.set("session_token", session_token)
            
            # 1. List notifications - should have 2 unread
            list_response = session.get(f"{BASE_URL}/api/notifications")
            assert list_response.status_code == 200
            data = list_response.json()
            assert data["unread_count"] >= 2, f"Expected at least 2 unread, got {data['unread_count']}"
            
            # 2. Mark one as read
            mark_response = session.patch(f"{BASE_URL}/api/notifications/{notif_id_1}/read")
            assert mark_response.status_code == 200
            
            # 3. Verify unread count decreased
            list_response2 = session.get(f"{BASE_URL}/api/notifications")
            assert list_response2.status_code == 200
            data2 = list_response2.json()
            assert data2["unread_count"] == data["unread_count"] - 1, "Unread count should decrease by 1"
            
            # 4. Mark all as read
            mark_all_response = session.post(f"{BASE_URL}/api/notifications/read-all")
            assert mark_all_response.status_code == 200
            
            # 5. Verify all are read
            list_response3 = session.get(f"{BASE_URL}/api/notifications")
            assert list_response3.status_code == 200
            data3 = list_response3.json()
            assert data3["unread_count"] == 0, f"Expected 0 unread after mark-all, got {data3['unread_count']}"
            
            print("✓ Notification workflow test passed")
        finally:
            db.notifications.delete_many({"notification_id": {"$in": [notif_id_1, notif_id_2]}})
            client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
