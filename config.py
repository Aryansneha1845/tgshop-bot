import os
import hashlib
from dotenv import load_dotenv

# hardcore: load .env from this file's dir regardless of cwd
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6131512280"))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "samosawithchatni")
SUPPORT_URL = os.getenv("SUPPORT_URL", f"https://t.me/{SUPPORT_USERNAME}")
UPI_ID = os.getenv("UPI_ID", "alphajip1@naviaxis")
UPI_NAME = os.getenv("UPI_NAME", "ARYAN SANTOSH SINGH")
WHOLESALE_DISCOUNT = float(os.getenv("WHOLESALE_DISCOUNT", "0.10"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in .env — set via @BotFather")
if ":" not in BOT_TOKEN or len(BOT_TOKEN) < 40:
    raise RuntimeError("BOT_TOKEN looks invalid — check @BotFather")

DB_PATH = os.path.join(os.path.dirname(__file__), "tgshop.db")

# ---- ultra secure settings ----
RATE_LIMIT_SECONDS = 2
MAX_DEPOSITS_PER_HOUR = 3
MAX_PURCHASES_PER_MINUTE = 5
MAX_AMOUNT_PER_DEPOSIT = 10000
MIN_AMOUNT_PER_DEPOSIT = 50
FLOODWAIT_BUFFER = 30
SUPPLIER_MODE = os.getenv("SUPPLIER_MODE", "mock")
LOG_TOKEN = False
# admin 2FA pin (set ADMIN_PIN in .env for extra layer, else ADMIN_ID only)
ADMIN_PIN = os.getenv("ADMIN_PIN", "")  # e.g. 6-digit
# encryption key derived from token + admin_id (never logged)
def _derive_key():
    raw = f"{BOT_TOKEN}:{ADMIN_ID}".encode()
    return hashlib.sha256(raw).digest()  # 32 bytes for Fernet base
ENCRYPTION_KEY_RAW = _derive_key()
# audit
AUDIT_LOG = os.path.join(os.path.dirname(__file__), "audit.log")
MAX_TEXT_LEN = 200  # anti-spam max input
CALLBACK_MAX_LEN = 64
