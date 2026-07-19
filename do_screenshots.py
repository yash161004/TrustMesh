import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
import requests
from playwright.async_api import async_playwright as apw

BASE_DIR = Path("d:/TrustMesh/TrustMesh/backend")
SCREENSHOTS_DIR = BASE_DIR.parent / "docs" / "screenshots"

def log(msg): print(f"[scr] {msg}", flush=True)

class Proc:
    def __init__(self, cmd, env_kv=None, cwd=None, label=""):
        self.cmd = cmd
        self.env = {**os.environ, **(env_kv or {})}
        self.cwd = str(cwd) if cwd else None
        self.label = label
        self.proc = None

    def start(self):
        log(f"Starting {self.label}: {' '.join(self.cmd)}")
        self.proc = subprocess.Popen(
            self.cmd, env=self.env, cwd=self.cwd,
            stdout=None, stderr=None, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try: self.proc.wait(5)
            except: self.proc.kill()

async def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get sessions
    r = requests.get("http://localhost:8000/api/v1/sessions?limit=50", timeout=30)
    sessions = r.json()
    manip_sid = None
    verified_sid = None
    
    for s in sessions:
        r2 = requests.get(f"http://localhost:8000/api/v1/sessions/{s['session_id']}/trust", timeout=30)
        if r2.status_code == 200:
            trust = r2.json()
            nv = len(trust.get("violations", []))
            if s.get("message_count", 0) >= 7 and nv >= 2:
                manip_sid = s["session_id"]
            elif nv > 0 and s.get("message_count", 0) < 7:
                verified_sid = s["session_id"]
                
    if not manip_sid: manip_sid = sessions[-1]["session_id"]
    if not verified_sid: verified_sid = sessions[0]["session_id"]
    log(f"verified={verified_sid} manip={manip_sid}")

    # Start Astro frontend
    DB_ENV = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{BASE_DIR}/trustmesh.db",
        "CLERK_BYPASS": "true",
        "ASTRO_TELEMETRY_DISABLED": "1"
    }
    fe = Proc(["npm.cmd", "run", "dev", "--", "--port", "4321", "--host"], env_kv=DB_ENV, cwd="d:/TrustMesh/TrustMesh/web-astro", label="frontend")
    fe.start()
    
    # Wait for frontend
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            if requests.get("http://localhost:4321", timeout=2).status_code == 200:
                log("Frontend OK")
                break
        except: pass
        time.sleep(1)
        
    async with apw() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
        page = await ctx.new_page()

        log("--- 01: Dashboard Overview ---")
        await page.goto("http://localhost:4321/dashboard", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_dashboard_overview.png"), full_page=True)

        log("--- 02 & 03: Trust Scores & Violations ---")
        await page.goto(f"http://localhost:4321/dashboard/sessions/{manip_sid}", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "02_trust_scores.png"), full_page=True)
        await page.evaluate("window.scrollTo(0, 350)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "03_violations_list.png"), full_page=True)

        log("--- 04: Ledger Verified ---")
        await page.goto(f"http://localhost:4321/dashboard/sessions/{verified_sid}", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "04_ledger_verified.png"), full_page=True)

        log("--- Tamper ---")
        os.system(f"d:/TrustMesh/TrustMesh/backend/.venv/Scripts/python.exe d:/TrustMesh/TrustMesh/backend/scripts/tamper_ledger_demo.py {manip_sid}")

        log("--- 05: Ledger Broken ---")
        await page.goto(f"http://localhost:4321/dashboard/sessions/{manip_sid}", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "05_ledger_broken.png"), full_page=True)

        await page.close()
        await ctx.close()
        await browser.close()
    
    fe.stop()
    log("ALL 5 SCREENSHOTS CAPTURED")

if __name__ == "__main__":
    asyncio.run(main())
