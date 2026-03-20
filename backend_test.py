#!/usr/bin/env python3
"""
Comprehensive backend API testing for Remora Search Engine
Tests all CRUD operations, authentication, and core functionality
"""

import requests
import sys
import json
import time
from datetime import datetime

class RemoraAPITester:
    def __init__(self, base_url="https://agent-index-pro.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_token = None
        self.api_key = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Store created resources for cleanup
        self.created_keys = []
        self.created_agents = []
        self.created_webhooks = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            self.failed_tests.append({"name": name, "details": details})
            print(f"❌ {name} - {details}")
        
        if details and success:
            print(f"   {details}")

    def make_request(self, method, endpoint, expected_status=200, json_data=None, headers=None, auth_required=True):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Default headers
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        
        # Add authentication
        if auth_required and self.session_token:
            request_headers['Authorization'] = f'Bearer {self.session_token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers)
            elif method == 'POST':
                response = requests.post(url, json=json_data, headers=request_headers)
            elif method == 'PUT':
                response = requests.put(url, json=json_data, headers=request_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            success = response.status_code == expected_status
            
            try:
                data = response.json()
            except:
                data = {"status_code": response.status_code, "text": response.text[:200]}
            
            return success, data
        
        except Exception as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test basic health endpoint"""
        success, data = self.make_request('GET', '/health', auth_required=False)
        self.log_test(
            "API Health Check", 
            success and data.get('status') == 'healthy',
            f"Status: {data.get('status', 'unknown')}, DB: {data.get('database', 'unknown')}, Meilisearch: {data.get('meilisearch', 'unknown')}"
        )
        return success

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, data = self.make_request('GET', '/', auth_required=False)
        self.log_test(
            "Root API Endpoint",
            success and 'Remora API' in data.get('message', ''),
            f"Message: {data.get('message', '')}, Version: {data.get('version', '')}"
        )
        return success

    def test_sample_data_seeding(self):
        """Test sample data seeding endpoint"""
        success, data = self.make_request('POST', '/seed', auth_required=False)
        self.log_test(
            "Sample Data Seeding",
            success,
            data.get('message', str(data))
        )
        return success

    def create_test_user_session(self):
        """Create test user and session for authentication testing"""
        try:
            import pymongo
            from datetime import datetime, timedelta, timezone
            import uuid
            
            # Connect to MongoDB
            client = pymongo.MongoClient("mongodb://localhost:27017")
            db = client['test_database']
            
            # Create test user
            user_id = f"test-user-{int(time.time())}"
            session_token = f"test_session_{int(time.time())}"
            
            user_data = {
                "user_id": user_id,
                "email": f"test.user.{int(time.time())}@example.com",
                "name": "Test User",
                "picture": "https://via.placeholder.com/150",
                "tier": "free",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            session_data = {
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            db.users.insert_one(user_data)
            db.user_sessions.insert_one(session_data)
            
            self.session_token = session_token
            self.user_data = user_data
            
            print(f"✅ Created test user and session")
            print(f"   User ID: {user_id}")
            print(f"   Session Token: {session_token[:20]}...")
            
            client.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create test user: {e}")
            return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        if not self.session_token:
            if not self.create_test_user_session():
                self.log_test("Auth Me", False, "Failed to create test session")
                return False
        
        success, data = self.make_request('GET', '/auth/me')
        self.log_test(
            "Auth Me Endpoint",
            success and data.get('user_id') is not None,
            f"User: {data.get('name', 'Unknown')} ({data.get('email', 'no-email')})"
        )
        return success

    def test_api_keys_crud(self):
        """Test API Keys CRUD operations"""
        # Create API key
        key_data = {"name": "Test API Key"}
        success, data = self.make_request('POST', '/keys', json_data=key_data, expected_status=201)
        
        if success and 'api_key' in data:
            self.api_key = data['api_key']
            key_id = data['key_id']
            self.created_keys.append(key_id)
            self.log_test("Create API Key", True, f"Created key: {data.get('name')} ({data.get('prefix')})")
        else:
            self.log_test("Create API Key", False, f"Failed to create key: {data}")
            return False
        
        # List API keys
        success, data = self.make_request('GET', '/keys')
        self.log_test(
            "List API Keys", 
            success and isinstance(data, list),
            f"Found {len(data) if isinstance(data, list) else 0} keys"
        )
        
        # Test search with API key
        self.test_search_with_api_key()
        
        return True

    def test_search_with_api_key(self):
        """Test search API with API key authentication"""
        if not self.api_key:
            self.log_test("Search API Test", False, "No API key available")
            return False
        
        query_data = {
            "query": "python async",
            "intent": "documentation",
            "max_results": 5
        }
        
        headers = {"X-API-Key": self.api_key}
        success, data = self.make_request(
            'POST', '/search', 
            json_data=query_data, 
            headers=headers, 
            auth_required=False
        )
        
        self.log_test(
            "Search API with API Key",
            success and 'results' in data,
            f"Found {data.get('total', 0)} results in {data.get('processing_time_ms', 0)}ms"
        )
        return success

    def test_agents_crud(self):
        """Test Agent Registry CRUD operations"""
        # Create agent
        agent_data = {
            "name": "Test Agent",
            "description": "Test agent for API testing",
            "capabilities": ["search", "summarize"],
            "endpoint_url": "https://example.com/webhook",
            "auth_type": "api_key"
        }
        
        success, data = self.make_request('POST', '/agents', json_data=agent_data, expected_status=201)
        
        if success and 'agent_id' in data:
            agent_id = data['agent_id']
            self.created_agents.append(agent_id)
            self.log_test("Create Agent", True, f"Created agent: {data.get('name')}")
            
            # Update agent
            update_data = {"description": "Updated test agent"}
            success, data = self.make_request('PUT', f'/agents/{agent_id}', json_data=update_data)
            self.log_test("Update Agent", success, "Updated agent description")
            
        else:
            self.log_test("Create Agent", False, f"Failed: {data}")
            return False
        
        # List agents
        success, data = self.make_request('GET', '/agents')
        self.log_test(
            "List Agents",
            success and isinstance(data, list),
            f"Found {len(data) if isinstance(data, list) else 0} agents"
        )
        
        return True

    def test_webhooks_crud(self):
        """Test Webhooks CRUD operations"""
        # Create webhook
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["search.complete", "content.updated"]
        }
        
        success, data = self.make_request('POST', '/webhooks', json_data=webhook_data, expected_status=201)
        
        if success and 'webhook_id' in data:
            webhook_id = data['webhook_id']
            self.created_webhooks.append(webhook_id)
            self.log_test("Create Webhook", True, f"Created webhook: {data.get('name')}")
            
            # Update webhook
            update_data = {"events": ["search.complete"]}
            success, data = self.make_request('PUT', f'/webhooks/{webhook_id}', json_data=update_data)
            self.log_test("Update Webhook", success, "Updated webhook events")
            
        else:
            self.log_test("Create Webhook", False, f"Failed: {data}")
            return False
        
        # List webhooks
        success, data = self.make_request('GET', '/webhooks')
        self.log_test(
            "List Webhooks",
            success and isinstance(data, list),
            f"Found {len(data) if isinstance(data, list) else 0} webhooks"
        )
        
        return True

    def test_usage_stats(self):
        """Test usage statistics endpoints"""
        # Get usage stats
        success, data = self.make_request('GET', '/usage/stats')
        self.log_test(
            "Usage Statistics",
            success and 'today' in data,
            f"Today: {data.get('today', 0)}, Total: {data.get('total', 0)}"
        )
        
        # Get recent usage
        success, data = self.make_request('GET', '/usage/recent')
        self.log_test(
            "Recent Usage",
            success and isinstance(data, list),
            f"Found {len(data) if isinstance(data, list) else 0} recent records"
        )
        
        return success

    def test_content_management(self):
        """Test content management endpoints"""
        # List content
        success, data = self.make_request('GET', '/content')
        self.log_test(
            "List Content",
            success and isinstance(data, list),
            f"Found {len(data) if isinstance(data, list) else 0} content items"
        )
        
        return success

    def cleanup(self):
        """Clean up created test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete created API keys
        for key_id in self.created_keys:
            success, _ = self.make_request('DELETE', f'/keys/{key_id}')
            if success:
                print(f"   Deleted API key: {key_id}")
        
        # Delete created agents
        for agent_id in self.created_agents:
            success, _ = self.make_request('DELETE', f'/agents/{agent_id}')
            if success:
                print(f"   Deleted agent: {agent_id}")
        
        # Delete created webhooks
        for webhook_id in self.created_webhooks:
            success, _ = self.make_request('DELETE', f'/webhooks/{webhook_id}')
            if success:
                print(f"   Deleted webhook: {webhook_id}")

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Remora API Backend Tests")
        print("=" * 50)
        
        # Basic connectivity tests
        self.test_root_endpoint()
        self.test_health_check()
        self.test_sample_data_seeding()
        
        # Authentication tests
        self.test_auth_me()
        
        # Core functionality tests
        if self.session_token:  # Only run if auth successful
            self.test_api_keys_crud()
            self.test_agents_crud()
            self.test_webhooks_crud()
            self.test_usage_stats()
            self.test_content_management()
        
        # Cleanup
        self.cleanup()
        
        # Print results
        print("\n" + "=" * 50)
        print(f"📊 TEST RESULTS: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"   • {test['name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = RemoraAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())