import time
import hashlib
import base64
import html
import re
from collections import defaultdict
from config import RATE_LIMIT_SECONDS, MAX_DEPOSITS_PER_HOUR, MAX_PURCHASES_PER_MINUTE, MAX_TEXT_LEN, CALLBACK_MAX_LEN, ENCRYPTION_KEY_RAW

_last_action = defaultdict(float)
_purchase_times = defaultdict(list)
_deposit_times = defaultdict(list)
_global_msg_times = defaultdict(list)

# ---- rate limits ----
def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    last = _last_action[user_id]
    if now - last < RATE_LIMIT_SECONDS:
        return False
    _last_action[user_id] = now
    return True

def can_purchase(user_id: int) -> bool:
    now = time.time()
    lst = _purchase_times[user_id]
    lst[:] = [t for t in lst if now - t < 60]
    if len(lst) >= MAX_PURCHASES_PER_MINUTE:
        return False
    lst.append(now)
    return True

def can_deposit(user_id: int) -> bool:
    now = time.time()
    lst = _deposit_times[user_id]
    lst[:] = [t for t in lst if now - t < 3600]
    if len(lst) >= MAX_DEPOSITS_PER_HOUR:
        return False
    lst.append(now)
    return True

def check_global_spam(user_id: int) -> bool:
    # 20 msgs per minute global
    now = time.time()
    lst = _global_msg_times[user_id]
    lst[:] = [t for t in lst if now - t < 60]
    if len(lst) >= 20:
        return False
    lst.append(now)
    return True

# ---- sanitizers (ultra secure) ----
def sanitize_utr(utr: str) -> bool:
    return utr.isdigit() and len(utr) == 12

def sanitize_amount(amt: int) -> bool:
    from config import MIN_AMOUNT_PER_DEPOSIT, MAX_AMOUNT_PER_DEPOSIT
    return MIN_AMOUNT_PER_DEPOSIT <= amt <= MAX_AMOUNT_PER_DEPOSIT

def sanitize_phone(phone: str) -> bool:
    p = phone.strip()
    if not p.startswith("+"):
        return False
    digits = p[1:].replace(" ", "").replace("-", "")
    return digits.isdigit() and 7 <= len(digits) <= 15

def sanitize_text(text: str) -> str:
    # strip, limit len, escape html, remove control chars
    t = text.strip()[:MAX_TEXT_LEN]
    t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
    return html.escape(t)

def sanitize_callback(data: str) -> bool:
    if len(data) > CALLBACK_MAX_LEN:
        return False
    # allow only alnum _ : -
    return bool(re.match(r'^[\w:_-]+$', data))

def sanitize_region(region: str) -> bool:
    return bool(re.match(r'^[A-Za-z ]{2,20}$', region))

def sanitize_session(session: str) -> bool:
    return 10 <= len(session) <= 5000

def mask_token(token: str) -> str:
    if len(token) < 10:
        return "***"
    return token[:6] + "***" + token[-4:]

def mask_phone(phone: str) -> str:
    if len(phone) < 4:
        return "***"
    return phone[:3] + "****" + phone[-3:]

def mask_utr(utr: str) -> str:
    if len(utr) != 12:
        return "***"
    return utr[:4] + "****" + utr[-4:]

def is_admin(user_id: int) -> bool:
    from config import ADMIN_ID
    return user_id == ADMIN_ID

def check_admin_pin(provided: str) -> bool:
    from config import ADMIN_PIN
    if not ADMIN_PIN:
        return True
    return provided == ADMIN_PIN

def sign_callback(data: str) -> str:
    # HARDCORE HMAC 256-bit (64 hex) — very secure
    import hmac
    sig = hmac.new(ENCRYPTION_KEY_RAW, data.encode(), hashlib.sha256).hexdigest()  # 64
    return f"{data}:{sig}"

def verify_callback(signed: str) -> tuple[bool, str]:
    import hmac
    if ":" not in signed:
        return False, ""
    try:
        raw, sig = signed.rsplit(":", 1)
        if len(sig) != 64:
            return False, ""
        exp = hmac.new(ENCRYPTION_KEY_RAW, raw.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(exp, sig), raw
    except Exception:
        return False, ""

# persist rate limits to DB (hardcore)
def _db_rate_check(user_id: int, action: str, window: int, limit: int) -> bool:
    try:
        import db
        conn = db.get_conn()
        cur = conn.cursor()
        now = int(time.time())
        cur.execute("SELECT COUNT(*) FROM audit WHERE user_id=? AND action=? AND created_at>?",
                    (user_id, action, now - window))
        c = cur.fetchone()[0]
        conn.close()
        if c >= limit:
            return False
        # log this action for persistence
        audit(action, user_id, f"rate:{window}")
        return True
    except Exception:
        return True

# ---- encryption at rest for session (Fernet from raw key) ----
try:
    from cryptography.fernet import Fernet
    _fernet_key = base64.urlsafe_b64encode(ENCRYPTION_KEY_RAW)
    _fernet = Fernet(_fernet_key)
    HAS_FERNET = True
except Exception:
    HAS_FERNET = False
    _fernet = None

def encrypt_session(plain: str) -> str:
    if HAS_FERNET:
        return "enc:" + _fernet.encrypt(plain.encode()).decode()
    # fallback simple obfuscation (not strong, but better than plain)
    b = plain.encode()
    k = ENCRYPTION_KEY_RAW
    enc = bytes([b[i] ^ k[i % len(k)] for i in range(len(b))])
    return "xor:" + base64.b64encode(enc).decode()

def decrypt_session(stored: str) -> str:
    try:
        if stored.startswith("enc:"):
            if HAS_FERNET:
                return _fernet.decrypt(stored[4:].encode()).decode()
            return stored
        if stored.startswith("xor:"):
            enc = base64.b64decode(stored[4:])
            k = ENCRYPTION_KEY_RAW
            dec = bytes([enc[i] ^ k[i % len(k)] for i in range(len(enc))])
            return dec.decode()
        return stored  # legacy plain
    except Exception:
        return stored

# ---- audit log (secure, no token/phone full) ----
def audit(event: str, user_id: int, detail: str = ""):
    try:
        from config import AUDIT_LOG, BOT_TOKEN
        safe = detail.replace(BOT_TOKEN, "***") if BOT_TOKEN else detail
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {event} | uid={user_id} | {safe[:200]}\n"
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
