import urllib.request
import urllib.error
import json

base_url = "http://127.0.0.1:8000/api/v1/metrics"
endpoints = ["/sessions-per-org", "/tactics-frequency", "/average-trust"]

def run_tests(token, title):
    print(f"\n{'='*40}")
    print(f"RUNNING AS: {title}")
    print(f"{'='*40}")
    headers = {"Authorization": f"Bearer {token}"}
    for ep in endpoints:
        url = base_url + ep
        print(f"\n--- {ep} ---")
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                print(f"HTTP {response.getcode()}")
                print(json.dumps(data, indent=2))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}")
            try:
                err_data = json.loads(e.read().decode())
                print(json.dumps(err_data, indent=2))
            except:
                print(e.read().decode())
        except Exception as e:
            print(f"Error: {e}")

print("Testing with Admin Token:")
run_tests("test_admin_token", "ADMIN USER (owner-user-id)")

print("\nTesting with Standard Token:")
run_tests("test_user_token", "STANDARD USER (other-user-id)")
