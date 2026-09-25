from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db
from config import SUPPORT_URL

def main_menu_kb(user_id=None):
    # Image 1 layout — hardcore legal row added, nothing revealed
    kb = [
        [InlineKeyboardButton("🛒 Purchase Tg Account", callback_data="menu:store")],
        [InlineKeyboardButton("💵 Add Funds", callback_data="wallet:add"),
         InlineKeyboardButton("🧾 View Wallet", callback_data="wallet:view")],
        [InlineKeyboardButton("📦 Order History", callback_data="orders:history:0")],
        [InlineKeyboardButton("👨‍💼 Contact Support", url=SUPPORT_URL)],
        [InlineKeyboardButton("📄 Privacy", callback_data="legal:privacy"),
         InlineKeyboardButton("📜 Terms", callback_data="legal:terms")],
        [InlineKeyboardButton("🍪 Cookie", callback_data="legal:cookie"),
         InlineKeyboardButton("💸 Refund", callback_data="legal:refund")],
    ]
    return InlineKeyboardMarkup(kb)

def legal_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Privacy", callback_data="legal:privacy"),
         InlineKeyboardButton("📜 Terms", callback_data="legal:terms")],
        [InlineKeyboardButton("🍪 Cookie", callback_data="legal:cookie"),
         InlineKeyboardButton("💸 Refund", callback_data="legal:refund")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu:main")],
    ])

def store_menu_kb():
    # Image 2 — secure disclosure
    kb = [
        [InlineKeyboardButton("⚡ Budget Accounts", callback_data="store:budget")],
        [InlineKeyboardButton("💎 Premium Quality", callback_data="store:premium")],
        [InlineKeyboardButton("🏠 Return to Menu", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(kb)

DEMO_FOOTER = ""  # removed — empty mode

def region_menu_kb(acctype):
    # Image 3 — 6 regions grid
    kb = [
        [InlineKeyboardButton("🇮🇳 India", callback_data=f"region:IN:{acctype}"),
         InlineKeyboardButton("🇺🇸 USA", callback_data=f"region:USA:{acctype}")],
        [InlineKeyboardButton("🇮🇩 Indonesia", callback_data=f"region:Indonesia:{acctype}"),
         InlineKeyboardButton("🇲🇲 Myanmar", callback_data=f"region:Myanmar:{acctype}")],
        [InlineKeyboardButton("🇧🇩 Bangladesh", callback_data=f"region:Bangladesh:{acctype}"),
         InlineKeyboardButton("🇻🇳 Vietnam", callback_data=f"region:Vietnam:{acctype}")],
        [InlineKeyboardButton("🌐 Random", callback_data=f"region:RANDOM:{acctype}")],
        [InlineKeyboardButton("🔍 Search All Countries", callback_data=f"region:SEARCH:{acctype}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:store")],
    ]
    return InlineKeyboardMarkup(kb)

def search_regions_kb(acctype, regions, page=0, per_page=6):
    # shows distinct regions with stock + search prompt
    # regions: list of region names
    kb = []
    start = page * per_page
    chunk = regions[start:start+per_page]
    for r in chunk:
        flag = db.flag_for(r)
        cnt = db.count_stock(acctype, r)
        kb.append([InlineKeyboardButton(f"{flag} {r} ({cnt})", callback_data=f"region:{r}:{acctype}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"search:{acctype}:{page-1}"))
    if start + per_page < len(regions):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"search:{acctype}:{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔍 Search by keyword (send name)", callback_data=f"searchkw:{acctype}")])
    kb.append([InlineKeyboardButton("⬅️ Back", callback_data=f"store:{acctype}")])
    return InlineKeyboardMarkup(kb)

def listing_kb(acctype, region, rows, page, total):
    # rows: list of (id, region, price, phone) — each row is a buy button (signed)
    import security as sec
    kb = []
    for row in rows:
        aid, r, price = row[0], row[1], row[2]
        flag = db.flag_for(r)
        label_region = r if r != "RANDOM" else region
        short = label_region
        if label_region == "IN":
            short = "IN"
        elif label_region == "USA":
            short = "US"
        signed = sec.sign_callback(f"buy:{aid}")
        kb.append([InlineKeyboardButton(f"{flag} ₹{price} {short}", callback_data=signed)])
    # pagination + actions
    per_page = 6
    has_next = (page + 1) * per_page < total
    has_prev = page > 0
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"list:{region}:{acctype}:{page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{region}:{acctype}:{page+1}"))
    if nav_row:
        kb.append(nav_row)
    kb.append([
        InlineKeyboardButton("🔄 Refresh", callback_data=f"list:{region}:{acctype}:{page}:refresh"),
        InlineKeyboardButton("➡️ Menu", callback_data="menu:main")
    ])
    return InlineKeyboardMarkup(kb)

def buy_confirm_kb(aid):
    import security as sec
    signed = sec.sign_callback(f"buy_confirm:{aid}")
    kb = [
        [InlineKeyboardButton("✅ Confirm Buy", callback_data=signed)],
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(kb)

def wallet_kb():
    kb = [
        [InlineKeyboardButton("💵 Add Funds", callback_data="wallet:add")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(kb)

def orders_kb(page, total, has_next, has_prev):
    kb = []
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"orders:history:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"orders:history:{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🏠 Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(kb)

def admin_deposit_kb(deposit_id):
    kb = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"deposit:approve:{deposit_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"deposit:reject:{deposit_id}")],
    ]
    return InlineKeyboardMarkup(kb)
