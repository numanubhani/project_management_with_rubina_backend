"""
Quick test script to verify backend connection
Run: python test_connection.py
"""
import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

BASE_URL = "http://localhost:8000/api"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health/", timeout=5)
        print(f"[OK] Health check: {response.status_code}")
        print(f"     Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Health check: Server not running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return False

def test_api_root():
    """Test API root"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"[OK] API root: {response.status_code}")
        print(f"     Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] API root: Server not running")
        return False
    except Exception as e:
        print(f"[FAIL] API root failed: {e}")
        return False

def test_swagger():
    """Test Swagger endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/schema/", timeout=5)
        print(f"[OK] Swagger schema: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Swagger: Server not running")
        return False
    except Exception as e:
        print(f"[FAIL] Swagger failed: {e}")
        return False

def test_register():
    """Test registration endpoint"""
    try:
        data = {
            "workspace_name": "Test Workspace",
            "admin_name": "Test Admin",
            "email": "test@example.com",
            "password": "test123456"
        }
        response = requests.post(f"{BASE_URL}/auth/register", json=data, timeout=5)
        print(f"[OK] Register endpoint: {response.status_code}")
        if response.status_code == 201:
            token = response.json().get('access_token', '')
            print(f"     Token received: {len(token)} chars")
            print(f"     User: {response.json().get('user', {}).get('email', 'N/A')}")
        elif response.status_code == 400:
            print(f"     Note: User may already exist (this is OK)")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Register: Server not running")
        return False
    except Exception as e:
        print(f"[FAIL] Register failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Backend Connection")
    print("=" * 50)
    print()
    
    results = []
    results.append(("Health Check", test_health()))
    results.append(("API Root", test_api_root()))
    results.append(("Swagger", test_swagger()))
    results.append(("Register Endpoint", test_register()))
    
    print()
    print("=" * 50)
    print("Results:")
    print("=" * 50)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
    
    print()
    print("Backend URL: http://localhost:8000")
    print("API Docs: http://localhost:8000/api/docs/")
    print("=" * 50)

