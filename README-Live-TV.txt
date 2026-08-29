REEL + LIVE TV API
==================

This version adds a small local API between Reel.html and the BINTV public event
listing. Reel no longer tries to scrape BINTV directly from a file:// page.

EASIEST (macOS)
---------------
1. Keep these files together:
   - Reel.html
   - live_tv_api.py
   - requirements-live-tv.txt
   - start-reel.command
2. Double-click start-reel.command.
3. It creates a Python environment, installs the dependencies, installs a Chromium
   runtime for the browser-rendered fallback, starts the API, and opens Reel at:
   http://127.0.0.1:8787/
4. Leave the Terminal window open while using Reel.

MANUAL
------
If you already have the environment set up:
  python3 live_tv_api.py
Then open http://127.0.0.1:8787/

API ENDPOINTS
-------------
GET /api/health
GET /api/live-games
GET /api/live-games?refresh=1

The event list is cached for 2 minutes. Refresh in Reel forces a fresh discovery.
The API first tries a normal HTTP fetch and then uses Playwright/Chromium so
JavaScript-rendered event cards can be discovered when the normal HTML does not
contain them.

IMPORTANT
---------
The detector only uses event/provider URLs that are exposed by the public listing.
It does not require Reel to bypass a provider's player protections. Manual embed
URLs and direct HLS URLs that you already have continue to work in Reel.

If BINTV changes its page structure, edit extract_from_html() in live_tv_api.py.
