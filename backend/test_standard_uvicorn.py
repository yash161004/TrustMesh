import subprocess
import time
import urllib.request

p = subprocess.Popen(
    [".\\.venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8015"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(10)
p.terminate()
p.wait()
stdout, stderr = p.communicate()
print("STDOUT:\n", stdout)
print("STDERR:\n", stderr)
