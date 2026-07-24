#!/usr/bin/env python3
"""
Health check script to verify ngrok is running and fetch its public URL.
Run this if your Clerk webhooks are silently failing in local development.
"""

import json
import sys
import urllib.request


def check_ngrok():
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            tunnels = data.get("tunnels", [])
            if not tunnels:
                print("⚠️  Ngrok is running, but no tunnels are active.")
                sys.exit(1)

            print("✅ Ngrok is running!")
            for t in tunnels:
                print(f"🔗 Public URL: {t['public_url']}")

            print("\n⚠️  IMPORTANT: Make sure this URL matches your Clerk Webhook Endpoint config!")
            print("If it doesn't match, webhooks will silently fail.")

    except urllib.error.URLError:
        print("❌ Ngrok API is unreachable. Is ngrok running?")
        print("Run `ngrok.cmd http 8000` (or your OS equivalent) in another terminal.")
        print("Then update your Clerk Dashboard with the new URL.")
        sys.exit(1)


if __name__ == "__main__":
    check_ngrok()
