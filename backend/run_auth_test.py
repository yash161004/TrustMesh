import asyncio
import httpx
import uvicorn
from multiprocessing import Process
from app.main import app
import time
import os

def run_server():
    os.environ["AUTH_ENFORCED"] = "true" # ensure it's on for test
    uvicorn.run("app.main:app", host="127.0.0.1", port=8005, log_level="error")

if __name__ == "__main__":
    p = Process(target=run_server)
    p.start()
    time.sleep(5)
    try:
        r1 = httpx.get("http://127.0.0.1:8005/api/v1/sessions")
        print("Unauthenticated Request Status:", r1.status_code)
        
        r2 = httpx.get("http://127.0.0.1:8005/api/v1/sessions", headers={"Authorization": "Bearer invalidtoken"})
        print("Invalid Token Request Status:", r2.status_code)
    except Exception as e:
        print("Error:", e)
    finally:
        p.terminate()
        p.join()
