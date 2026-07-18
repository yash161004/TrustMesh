import subprocess
import time
import urllib.request
import urllib.error

# Run fixed server
p = subprocess.Popen(
    [".\\.venv\\Scripts\\python.exe", "run_server_fixed.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("Started server. PID:", p.pid)
time.sleep(10) # wait for startup

try:
    print("--- Unauthenticated Request ---")
    req = urllib.request.Request("http://127.0.0.1:8010/api/v1/sessions")
    try:
        urllib.request.urlopen(req)
        print("Success 200")
    except urllib.error.HTTPError as e:
        print("Status:", e.code)
    except Exception as e:
        print("Exception:", e)
        
    print("--- Invalid Token Request ---")
    req2 = urllib.request.Request("http://127.0.0.1:8010/api/v1/sessions")
    req2.add_header("Authorization", "Bearer invalidtoken")
    try:
        urllib.request.urlopen(req2)
        print("Success 200")
    except urllib.error.HTTPError as e:
        print("Status:", e.code)
    except Exception as e:
        print("Exception:", e)
finally:
    p.terminate()
    p.wait()
    stdout, stderr = p.communicate()
    print("--- Uvicorn STDOUT ---")
    print(stdout)
    print("--- Uvicorn STDERR ---")
    print(stderr)
