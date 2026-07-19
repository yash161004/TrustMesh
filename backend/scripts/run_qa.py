import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "qa.db"
PYTHON_EXE = str(BASE_DIR / ".venv" / "Scripts" / "python.exe")

DB_ENV = {
    "DATABASE_URL": f"sqlite+aiosqlite:///{DB_PATH}",
    "AUTH_ENFORCED": "false",
    "CLERK_BYPASS": "true",
    "ALLOWED_ORIGINS_RAW": "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4321",
}

class Proc:
    def __init__(self, cmd, cwd, env=None):
        self.cmd = cmd
        self.p = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdout=None, stderr=None
        )
    def stop(self):
        self.p.terminate()
        try:
            self.p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.p.kill()

def log(msg):
    print(f"[QA] {msg}")

def run_script(name: str, *args: str) -> None:
    sp = BASE_DIR / "scripts" / name
    cmd = [PYTHON_EXE, str(sp), *args]
    r = subprocess.run(
        cmd, env={**os.environ, **DB_ENV}, cwd=str(BASE_DIR),
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        log(f"Script {name} failed: {r.stderr}")
        raise Exception(f"{name} failed")

def wait_health():
    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise Exception("Backend health check failed")

async def run_axe(page, url_name):
    log(f"Running Axe-core on {url_name}...")
    await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.0/axe.min.js")
    results = await page.evaluate("axe.run()")
    violations = results.get("violations", [])
    if violations:
        log(f"Found {len(violations)} a11y violations on {url_name}!")
        for violation in results["violations"]:
            log(f"  - {violation['id']}: {violation['description']} ({len(violation['nodes'])} nodes affected)")
            for node in violation['nodes']:
                try:
                    log(f"    Node: {node['html']}")
                except UnicodeEncodeError:
                    with open("qa_node_error.txt", "w", encoding="utf-8") as f:
                        f.write(node['html'])
                    log("    Node: (written to qa_node_error.txt due to unicode)")
    else:
        log(f"No a11y violations found on {url_name}.")
    return violations

async def capture_responsive(page, url, name_prefix):
    breakpoints = [
        {"name": "mobile", "width": 375, "height": 812},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "desktop", "width": 1440, "height": 900},
    ]
    await page.goto(url, wait_until="load")
    await page.wait_for_timeout(2000)
    for bp in breakpoints:
        await page.set_viewport_size({"width": bp["width"], "height": bp["height"]})
        await page.wait_for_timeout(1000)
        file_path = f"qa_screenshots/{name_prefix}_{bp['name']}.png"
        await page.screenshot(path=file_path, full_page=True)
        log(f"Saved {file_path}")

async def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        
    be = Proc([PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
              cwd=str(BASE_DIR), env={**os.environ, **DB_ENV})
    try:
        wait_health()
        run_script("seed_demo_data.py")
        run_script("seed_ledger_entries.py")
        
        import urllib.request
        req = urllib.request.Request("http://localhost:8000/api/v1/sessions/load-demo", method="POST")
        urllib.request.urlopen(req)
        
        fe = Proc(["npm.cmd", "run", "dev", "--", "--port", "4321", "--host"],
                  cwd=str(BASE_DIR.parent / "web-astro"), env={**os.environ, **DB_ENV})
        
        time.sleep(10)
        
        # 1. Lighthouse on Landing Page
        log("Running Lighthouse on Landing Page...")
        lh_cmd = "npx lighthouse http://localhost:4321 --output json --output-path qa_lighthouse.json --chrome-flags=\"--headless\""
        subprocess.run(lh_cmd, shell=True, cwd=str(BASE_DIR.parent))
        
        if Path(str(BASE_DIR.parent / "qa_lighthouse.json")).exists():
            with open(str(BASE_DIR.parent / "qa_lighthouse.json"), 'r', encoding='utf-8') as f:
                lh_data = json.load(f)
                scores = {
                    cat: lh_data["categories"][cat]["score"] * 100 
                    for cat in lh_data["categories"] if lh_data["categories"][cat].get("score") is not None
                }
                log(f"Lighthouse Scores: {scores}")
        
        # 2. Playwright checks
        os.makedirs("qa_screenshots", exist_ok=True)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Click-through: Landing Page -> Auth -> Dashboard -> Session
            log("Testing click-through and console errors...")
            errors = []
            page.on("pageerror", lambda err: errors.append(err))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            
            await page.goto("http://localhost:4321/", wait_until="load")
            await run_axe(page, "Landing Page")
            await capture_responsive(page, "http://localhost:4321/", "landing")
            
            # Navigate to Dashboard
            await page.context.add_cookies([{
                "name": "clerk_bypass",
                "value": "true",
                "url": "http://localhost:4321"
            }])
            await page.goto("http://localhost:4321/dashboard", wait_until="load")
            await page.wait_for_timeout(3000)
            await run_axe(page, "Dashboard")
            await capture_responsive(page, "http://localhost:4321/dashboard", "dashboard")
            
            # Click into first session
            await page.goto("http://localhost:4321/dashboard", wait_until="load")
            await page.wait_for_timeout(2000)
            
            log("Clicking into first session...")
            session_links = await page.locator("a[href^='/dashboard/sessions/']").all()
            if session_links:
                session_url = await session_links[0].get_attribute("href")
                full_url = f"http://localhost:4321{session_url}"
                await page.goto(full_url, wait_until="load")
                await page.wait_for_timeout(3000)
                await run_axe(page, "Session View")
                await capture_responsive(page, full_url, "session")
            else:
                log("WARNING: Could not find any session links on dashboard!")
                
            if errors:
                log(f"Console errors found during click-through: {errors}")
            else:
                log("No console errors found during click-through!")
                
            await browser.close()
            
    finally:
        log("Shutting down...")
        try:
            fe.stop()
        except: pass
        try:
            be.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
