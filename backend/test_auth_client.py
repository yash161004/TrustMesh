import os
from dotenv import load_dotenv
load_dotenv()
from fastapi.testclient import TestClient
from app.main import app

def run_test():
    client = TestClient(app)
    
    print("--- Unauthenticated Request ---")
    r1 = client.get("/api/v1/sessions")
    print(f"Status: {r1.status_code}")
    print(f"Body: {r1.json()}")
    
    print("\n--- Invalid Token Request ---")
    r2 = client.get("/api/v1/sessions", headers={"Authorization": "Bearer invalidtoken"})
    print(f"Status: {r2.status_code}")
    print(f"Body: {r2.json()}")

if __name__ == "__main__":
    run_test()
