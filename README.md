# ChainPilot - Telegram Web3 Bot

Quick start:
1. Copy `.env.example` to `.env` and fill values.
2. Install deps: `pip install -r requirements.txt`.
3. Initialize DB: `python -c "from models import init_db; init_db()"`.
4. Run: `flask run --port=5000` (or use Docker).
5. Expose locally with ngrok and set Telegram webhook to `https://<ngrok>/telegram/webhook`.
