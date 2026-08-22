# 🇩🇿 Algeria Europe Volunteer Hunter V3

V3 adds:
- normalized opportunity records
- Algeria eligibility
- deadline/status scoring
- rule-based Match Score
- dashboard (Flask)
- Telegram alerts
- multi-source adapter structure

The AI layer is intentionally separated: `analyzer.py` exposes a stable interface,
so an LLM provider can be added later without changing the crawler/database.

Run:
1. `pip install -r requirements.txt`
2. copy `.env.example` to `.env`
3. set `DISCOVERY_URL` to a public ESC listing/search page
4. `python main.py`
5. `python dashboard.py` then open http://127.0.0.1:5000

This project only reads public pages and does not bypass authentication, CAPTCHA,
robots restrictions, or other access controls.
