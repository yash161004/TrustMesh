"""
TrustMesh QA Screenshot Generator CLI

Recaptures dashboard screenshots with Playwright for verification.

Usage:
    python scripts/qa_screenshots.py
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR.parent / "docs" / "screenshots"
DB_PATH = BASE_DIR / "screenshots.db"
ASTRO_DIR = BASE_DIR.parent / "web-astro"
VENV_PY = BASE_DIR / ".venv" / "Scripts" / "python.exe"


def log(msg: str) -> None:
    print(f"[qa-screenshots] {msg}", flush=True)


class Proc:
    def __init__(self, cmd: list[str], env_kv: dict | None = None,
                 cwd: str | Path | None = None, label: str = ""):
        self.cmd = cmd
        self.env = {**os.environ, **(env_kv or {})}
        self.cwd = str(cwd) if cwd else None
        self.label = label
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        log(f"Starting {self.label}: {' '.join(self.cmd)}")
        self.proc = subprocess.Popen(
            self.cmd, env=self.env, cwd=self.cwd,
            stdout=None, stderr=None,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def stop(self) -> None:
        if self.proc is None:
            return
        log(f"Stopping {self.label} (PID={self.proc.pid})")
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def wait_health(url: str = "http://localhost:8000/api/v1/health", timeout: int = 40) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                log(f"health OK: {data}")
                return data
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"health not ready in {timeout}s")


def wait_url(url: str, timeout: int = 120) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                log(f"URL OK: {url}")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"not ready in {timeout}s: {url}")


DB_ENV = {
    "DATABASE_URL": f"sqlite+aiosqlite:///{DB_PATH}",
    "AUTH_ENFORCED": "false",
    "ALLOWED_ORIGINS_RAW":
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4321,http://127.0.0.1:4321",
    "PYTHONPATH": str(BASE_DIR),
    "CLERK_BYPASS": "true",
    "CURRENT_PHASE": "2 — Trust Engine",
}


def run_script(name: str, *args: str) -> None:
    sp = BASE_DIR / "scripts" / name
    cmd = [str(VENV_PY), str(sp), *args]
    log(f"run: {name} {' '.join(args)}")
    r = subprocess.run(
        cmd, env={**os.environ, **DB_ENV}, cwd=str(BASE_DIR),
        capture_output=True, text=True, timeout=120,
    )
    for line in r.stdout.splitlines():
        print(f"  {line}")
    if r.stderr:
        for line in r.stderr.splitlines():
            print(f"  E: {line}", file=sys.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"{name} failed (rc={r.returncode})")


def rm_db() -> None:
    for p in [DB_PATH, DB_PATH.with_suffix(".db-journal"),
              DB_PATH.with_suffix(".db-wal"),
              DB_PATH.with_suffix(".db-shm")]:
        if p.exists():
            p.unlink()
            log(f"deleted {p.name}")


async def assert_visible(page, text: str, timeout: int = 15000, msg: str = "") -> None:
    await page.wait_for_function(
        f'document.body.innerText.toLowerCase().includes({json.dumps(text.lower())})',
        timeout=timeout,
    )
    log(f"  ok {msg or text}")


async def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    for port in (8000, 4321):
        subprocess.run(
            ["powershell", "-Command",
             f"Get-Process -Id (Get-NetTCPConnection -LocalPort {port} "
             f"-ErrorAction SilentlyContinue).OwningProcess "
             f"| Stop-Process -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10,
        )

    rm_db()

    be = Proc(
        [str(VENV_PY), "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000",
         "--log-level", "warning"],
        env_kv=DB_ENV, label="backend",
    )
    be.start()
    try:
        wait_health()

        run_script("seed_demo_data.py")
        run_script("seed_ledger_entries.py")

        log("load-demo …")
        r = requests.post(
            "http://localhost:8000/api/v1/sessions/load-demo",
            timeout=30,
        )
        log(f"load-demo: {r.status_code}")
        if r.status_code != 200:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                "UPDATE negotiation_sessions SET org_id=?, user_id=? WHERE org_id IS NULL",
                ("system-org-000", "system-user-000"),
            )
            conn.commit()
            conn.close()

        r = requests.get(
            "http://localhost:8000/api/v1/sessions?limit=50",
            timeout=30,
        )
        sessions = r.json()
        if not sessions:
            raise RuntimeError("no sessions")

        manip_sid = None
        verified_sid = None

        for s in sessions:
            r2 = requests.get(
                f"http://localhost:8000/api/v1/sessions/{s['session_id']}/trust",
                timeout=30,
            )
            trust = r2.json() if r2.status_code == 200 else {}
            nv = len(trust.get("violations", []))
            
            if s.get("message_count", 0) >= 7 and nv >= 2:
                manip_sid = s["session_id"]
            elif nv > 0 and s.get("message_count", 0) < 7:
                verified_sid = s["session_id"]

        if manip_sid is None:
            manip_sid = sessions[-1]["session_id"]
        if verified_sid is None:
            verified_sid = sessions[0]["session_id"]

        fe = Proc(
            ["npm.cmd", "run", "dev", "--", "--port", "4321", "--host"],
            env_kv={**DB_ENV, "CLERK_BYPASS": "true", "ASTRO_TELEMETRY_DISABLED": "1"},
            cwd=str(ASTRO_DIR), label="frontend",
        )
        fe.start()
        wait_url("http://localhost:4321", timeout=120)

        log("=" * 60)
        log("PLAYWRIGHT starts")

        from playwright.async_api import async_playwright as apw
        async with apw() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            ctx = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()

            log("--- 01: Dashboard Overview ---")
            await page.goto("http://localhost:4321/dashboard", wait_until="load", timeout=60000)
            await assert_visible(page, "Sessions", msg="Sessions title")
            await page.wait_for_timeout(2000)
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / "01_dashboard_overview.png"),
                full_page=True,
            )

            log("--- 02: Trust Scores ---")
            await page.goto(f"http://localhost:4321/dashboard/sessions/{manip_sid}", wait_until="load")
            await page.wait_for_timeout(4000)
            trust_el = page.locator("text=Buyer Trust").locator("xpath=ancestor::div[contains(@class, 'gap-6')][1]").first
            await trust_el.screenshot(path=str(SCREENSHOTS_DIR / "02_trust_scores.png"))

            log("--- 03: Violations List ---")
            viol_el = page.locator("text=Detected Violations").locator("xpath=ancestor::div[contains(@class, 'mt-6')][1]").first
            await viol_el.scroll_into_view_if_needed()
            await viol_el.screenshot(path=str(SCREENSHOTS_DIR / "03_violations_list.png"))

            log("--- 04: Ledger Verified ---")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / "04_ledger_verified.png"),
                full_page=True
            )

            log("--- TAMPER RUNNING ---")
            run_script("tamper_ledger_demo.py", manip_sid)

            log("--- 05: Ledger Broken ---")
            await page.reload(wait_until="load")
            await page.wait_for_timeout(2000)
            await page.locator("text=Chain Broken").wait_for(timeout=10000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / "05_ledger_broken.png"),
                full_page=True
            )

            await page.close()
            await ctx.close()
            await browser.close()

        log("ALL 5 SCREENSHOTS CAPTURED OK")

    finally:
        be.stop()
        try:
            fe.stop()
        except NameError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
