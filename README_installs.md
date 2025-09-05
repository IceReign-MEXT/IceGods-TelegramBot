# IceGods - Quick run (Termux)

1. Create virtual env and activate
$ python3 -m venv venv
$ source venv/bin/activate

2. Install dependencies
$ pip install python-telegram-bot==20.3 python-dotenv requests

3. Prepare environment
$ cp .env.sample .env
# Edit .env with your BOT_TOKEN and SOL_USDC_ADDRESS and SAFE_SOL_WALLET (do NOT commit .env)

4. Initialize DB (optional)
$ sqlite3 icegods.db < db_migration.sql

5. Run the bot:
$ python bot_plans.py

6. Run payment monitor (in another shell or as a background job)
$ python payment_monitor.py
