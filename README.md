# TG Shop Bot — Telegram Account Store (@TgStockHubBOT)

Secure 24/7 store for Telegram accounts. Empty stock — real permanent only.

- Stack: `python-telegram-bot 22.7` + `python-dotenv` + `cryptography Fernet` + `SQLite WAL`
- UPI: `alphajip1@naviaxis` (ARYAN SANTOSH SINGH) with QR `assets/qr_navi.jpg`
- Admin: `6131512280`
- Security: HMAC signed callbacks, Fernet session encryption, 12-digit UTR dedupe, rate limits (2s/5-per-min/3-per-hour/20-per-min), audit.log, banned, QR OCR, auto-delete 5min

## Run locally
```powershell
cd tgshop_bot
pip install -r requirements.txt
# create .env from .env.example
python main.py
```

## Env (.env) — NEVER commit real token
```
BOT_TOKEN=PUT_YOUR_TOKEN_HERE_FROM_BOTFATHER
ADMIN_ID=6131512280
SUPPORT_USERNAME=samosawithchatni
UPI_ID=alphajip1@naviaxis
UPI_NAME=ARYAN SANTOSH SINGH
WHOLESALE_DISCOUNT=0.10
SUPPLIER_MODE=empty
ADMIN_PIN=SET_6_DIGIT_PIN
```

## Deploy to Render (24/7)
- Push to GitHub, connect Render → New → Blueprint → `render.yaml` (Docker worker).
- Set env vars in Render dashboard: `BOT_TOKEN`, `ADMIN_ID`, etc.
- No web port needed (polling). Worker stays alive.

## Stock
Currently empty (`SUPPLIER_MODE=empty`). Add real permanent accounts via admin CSV:
```
+919999999999,IN,budget,84,real_StringSession_here
```
Send as message to admin. Bot confirms `✅ Added`.

## Commands
`/start` `/admin` `/credit <uid> <amt>` `/cancel`
