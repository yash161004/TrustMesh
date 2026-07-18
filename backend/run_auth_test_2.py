import subprocess
import time
import urllib.request
import urllib.error

p = subprocess.Popen([".\\.venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8008"])
time.sleep(5)
try:
    req = urllib.request.Request("http://127.0.0.1:8008/api/v1/sessions")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print("Unauthenticated Request Status:", e.code)
    
    req2 = urllib.request.Request("http://127.0.0.1:8008/api/v1/sessions")
    req2.add_header("Authorization", "Bearer invalidtoken")
    try:
        urllib.request.urlopen(req2)
    except urllib.error.HTTPError as e:
        print("Invalid Token Request Status:", e.code)
finally:
    p.terminate()
    p.wait()
