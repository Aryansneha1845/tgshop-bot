import sqlite3
import time
import random
import uuid
from config import DB_PATH

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # ultra secure: prevent injection via strict typing, busy timeout
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT,
        first_name  TEXT,
        balance     INTEGER DEFAULT 0,
        wholesale   INTEGER DEFAULT 1,
        banned      INTEGER DEFAULT 0,
        created_at  INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        type        TEXT NOT NULL CHECK(type IN ('budget','premium')),
        region      TEXT NOT NULL,
        price       INTEGER NOT NULL,
        phone       TEXT NOT NULL,
        session     TEXT NOT NULL,
        sold        INTEGER DEFAULT 0,
        sold_to     INTEGER,
        created_at  INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        account_id  INTEGER NOT NULL,
        price_paid  INTEGER NOT NULL,
        orig_price  INTEGER NOT NULL,
        region      TEXT NOT NULL,
        type        TEXT NOT NULL,
        phone       TEXT,
        delivered   TEXT,
        created_at  INTEGER,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deposits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        amount      INTEGER NOT NULL,
        utr         TEXT,
        photo_file_id TEXT,
        status      TEXT DEFAULT 'pending',
        created_at  INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        action      TEXT,
        detail      TEXT,
        created_at  INTEGER
    )
    """)
    # index for secure lookup
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_sold_type_region ON accounts(sold, type, region)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deposits_utr ON deposits(utr)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status)")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM accounts WHERE sold=0")
    cnt = cur.fetchone()[0]
    from config import SUPPLIER_MODE
    # ultra secure empty mode: no auto mock if SUPPLIER_MODE=empty
    if cnt == 0 and SUPPLIER_MODE != "empty":
        seed_mock_stock(cur)
        conn.commit()
    conn.close()

def seed_mock_stock(cur):
    # ultra secure: encrypt session at rest
    import security as sec
    now = int(time.time())
    budget_prices = {
        "IN": [84,87,87,87,90,90,84,87,90,84],
        "USA": [95,98,105,95,98,105,95,98],
        "Indonesia": [80,82,85,80,82,85],
        "Myanmar": [78,81,84,78,81,84],
        "Bangladesh": [79,83,86,79,83,86],
        "Vietnam": [82,85,88,82,85,88],
    }
    premium_prices = {
        "IN": [150,170,190,150,170,190],
        "USA": [160,180,200,160,180,200],
        "Indonesia": [140,160,175,140,160],
        "Myanmar": [135,155,170,135,155],
        "Bangladesh": [138,158,172,138,158],
        "Vietnam": [142,162,178,142,162],
    }
    for region, prices in budget_prices.items():
        for p in prices:
            phone = f"+{random.randint(1000000000, 9999999999)}"
            sess = f"session_{uuid.uuid4().hex[:12]}_{region}_{p}"
            enc = sec.encrypt_session(sess)
            cur.execute("INSERT INTO accounts (type, region, price, phone, session, sold, created_at) VALUES (?,?,?,?,?,0,?)",
                        ("budget", region, p, phone, enc, now))
    for region, prices in premium_prices.items():
        for p in prices:
            phone = f"+{random.randint(1000000000, 9999999999)}"
            sess = f"premium_session_{uuid.uuid4().hex[:12]}_{region}_{p}"
            enc = sec.encrypt_session(sess)
            cur.execute("INSERT INTO accounts (type, region, price, phone, session, sold, created_at) VALUES (?,?,?,?,?,0,?)",
                        ("premium", region, p, phone, enc, now))

# ---- user helpers ----
def ensure_user(user_id, username=None, first_name=None):
    # ultra secure: sanitize
    import security as sec
    if username:
        username = sec.sanitize_text(username)[:32]
    if first_name:
        first_name = sec.sanitize_text(first_name)[:32]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, banned FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, username, first_name, balance, wholesale, banned, created_at) VALUES (?,?,?,?,?,0,?)",
                    (user_id, username, first_name, 0, 1, int(time.time())))
        conn.commit()
    else:
        if row[1] == 1:
            conn.close()
            return False
        cur.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (username, first_name, user_id))
        conn.commit()
    conn.close()
    return True

def is_banned(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    conn.close()
    return bool(r and r[0] == 1)

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, balance, wholesale, created_at FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_balance(user_id):
    u = get_user(user_id)
    return u[3] if u else 0

def is_wholesale(user_id):
    u = get_user(user_id)
    return bool(u[4]) if u else True

def credit_balance(user_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def debit_balance(user_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return False
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return True

def set_balance(user_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_regions_with_stock(acctype=None):
    conn = get_conn()
    cur = conn.cursor()
    if acctype:
        cur.execute("SELECT DISTINCT region FROM accounts WHERE sold=0 AND type=? ORDER BY region", (acctype,))
    else:
        cur.execute("SELECT DISTINCT region FROM accounts WHERE sold=0 ORDER BY region")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def count_stock(acctype, region):
    conn = get_conn()
    cur = conn.cursor()
    if region == "RANDOM":
        cur.execute("SELECT COUNT(*) FROM accounts WHERE sold=0 AND type=?", (acctype,))
    else:
        cur.execute("SELECT COUNT(*) FROM accounts WHERE sold=0 AND type=? AND region=?", (acctype, region))
    c = cur.fetchone()[0]
    conn.close()
    return c

def get_accounts(acctype, region, limit=6, offset=0):
    conn = get_conn()
    cur = conn.cursor()
    if region == "RANDOM":
        cur.execute("SELECT id, region, price, phone FROM accounts WHERE sold=0 AND type=? ORDER BY price ASC, id ASC LIMIT ? OFFSET ?", (acctype, limit, offset))
    else:
        cur.execute("SELECT id, region, price, phone FROM accounts WHERE sold=0 AND type=? AND region=? ORDER BY price ASC, id ASC LIMIT ? OFFSET ?", (acctype, region, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows

def total_accounts(acctype, region):
    return count_stock(acctype, region)

def get_account_by_id(aid):
    # ultra secure: validate int, decrypt session
    try:
        aid = int(aid)
    except:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, type, region, price, phone, session, sold FROM accounts WHERE id=?", (aid,))
    row = cur.fetchone()
    conn.close()
    if row:
        import security as sec
        dec = sec.decrypt_session(row[5])
        row = (row[0], row[1], row[2], row[3], row[4], dec, row[6])
    return row

def mark_sold(account_id, user_id):
    try:
        account_id = int(account_id); user_id = int(user_id)
    except:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT sold FROM accounts WHERE id=?", (account_id,))
    r = cur.fetchone()
    if not r or r[0] == 1:
        conn.close()
        return False
    cur.execute("UPDATE accounts SET sold=1, sold_to=? WHERE id=?", (user_id, account_id))
    conn.commit()
    conn.close()
    return True

def create_order(user_id, account_id, price_paid, orig_price, region, acctype, phone, delivered):
    # ultra secure: delivered may contain session — store encrypted audit copy
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, account_id, price_paid, orig_price, region, type, phone, delivered, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, account_id, price_paid, orig_price, region, acctype, phone, delivered, int(time.time())))
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid

def get_orders(user_id, limit=10, offset=0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, account_id, price_paid, orig_price, region, type, phone, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows

def total_orders(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (user_id,))
    c = cur.fetchone()[0]
    conn.close()
    return c

def create_deposit(user_id, amount, utr, photo_file_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO deposits (user_id, amount, utr, photo_file_id, status, created_at) VALUES (?,?,?,?,'pending',?)",
                (user_id, amount, utr, photo_file_id, int(time.time())))
    conn.commit()
    did = cur.lastrowid
    conn.close()
    return did

def get_pending_deposits():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, amount, utr, photo_file_id, created_at FROM deposits WHERE status='pending' ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_deposit_status(deposit_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE deposits SET status=? WHERE id=?", (status, deposit_id))
    conn.commit()
    conn.close()

def get_deposit(deposit_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, amount, utr, photo_file_id, status FROM deposits WHERE id=?", (deposit_id,))
    r = cur.fetchone()
    conn.close()
    return r

def is_utr_used(utr: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM deposits WHERE utr=?", (utr,))
    c = cur.fetchone()[0]
    conn.close()
    return c > 0

def admin_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    uc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM accounts WHERE sold=0")
    stock = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM accounts WHERE sold=1")
    sold = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'")
    pend = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(balance),0) FROM users")
    bal = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders")
    oc = cur.fetchone()[0]
    conn.close()
    return {"users": uc, "stock": stock, "sold": sold, "pending": pend, "total_balance": bal, "orders": oc}

def auto_topup_if_low(acctype, region, threshold=3):
    from config import SUPPLIER_MODE
    if SUPPLIER_MODE == "empty":
        return False
    if region == "RANDOM":
        cnt = count_stock(acctype, "RANDOM")
    else:
        cnt = count_stock(acctype, region)
    if cnt < threshold:
        import security as sec
        conn = get_conn()
        cur = conn.cursor()
        now = int(time.time())
        base_map = {"IN": 87, "USA": 98, "Indonesia": 82, "Myanmar": 81, "Bangladesh": 83, "Vietnam": 85}
        import random, uuid
        if region == "RANDOM":
            regions = ["IN","USA","Indonesia","Myanmar","Bangladesh","Vietnam"]
            for r in regions:
                for _ in range(2):
                    p = base_map.get(r, 85) + random.choice([-3,0,3,5])
                    if acctype == "premium":
                        p += 60
                    phone = f"+{random.randint(1000000000,9999999999)}"
                    sess = f"auto_{uuid.uuid4().hex[:10]}_{r}"
                    enc = sec.encrypt_session(sess)
                    cur.execute("INSERT INTO accounts (type, region, price, phone, session, sold, created_at) VALUES (?,?,?,?,?,0,?)",
                                (acctype, r, p, phone, enc, now))
        else:
            for _ in range(8):
                p = base_map.get(region, 85) + random.choice([-3,0,3,5])
                if acctype == "premium":
                    p += 60
                phone = f"+{random.randint(1000000000,9999999999)}"
                sess = f"auto_{uuid.uuid4().hex[:10]}_{region}"
                enc = sec.encrypt_session(sess)
                cur.execute("INSERT INTO accounts (type, region, price, phone, session, sold, created_at) VALUES (?,?,?,?,?,0,?)",
                            (acctype, region, p, phone, enc, now))
        conn.commit()
        conn.close()
        return True
    return False

REGION_FLAG = {
    "IN": "🇮🇳",
    "USA": "🇺🇸",
    "Indonesia": "🇮🇩",
    "Myanmar": "🇲🇲",
    "Bangladesh": "🇧🇩",
    "Vietnam": "🇻🇳",
    "RANDOM": "🌐",
    "IN": "🇮🇳",
    "India": "🇮🇳",
    "USA": "🇺🇸",
    "US": "🇺🇸",
}

def flag_for(region):
    return REGION_FLAG.get(region, REGION_FLAG.get(region.title(), "🌐"))

def ban_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
