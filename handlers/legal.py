from telegram import Update
from telegram.ext import ContextTypes
import db
import security
import time

BUSINESS = "ARYAN SANTOSH SINGH"
UPI_MASKED = "alphajip1***"
SUPPORT = "@samosawithchatni"
DPO = "@samosawithchatni"

def _mask_utr_for_display(utr: str) -> str:
    return security.mask_utr(utr) if utr and len(utr)==12 else "***"

PRIVACY_TEXT = f"""🔒 <b>Privacy Policy — TG STOCK BOT (@TgStockHubBOT)</b>

<b>Business:</b> {BUSINESS} | Support {SUPPORT} | DPO {DPO}
<b>DPDP Act 2023 & IT Act 2000 — Data Fiduciary Disclosure</b>

<b>What we collect (minimum only):</b>
• Telegram user_id, username, first_name (for account mapping)
• Balance & order count (for wholesale 5+ rule)
• Deposits: 12-digit UTR (masked as {UPI_MASKED} in logs) + screenshot file_id (Telegram stored, not raw image)
• Orders: phone (masked in logs) + encrypted session (Fernet enc:)
• No location, no contacts, no analytics cookies.

<b>Purpose:</b> Deliver Telegram accounts you pay for, verify UPI, prevent fraud (dedupe UTR).

<b>Retention:</b> Deposits pending → approved/rejected 24h; orders delivered → auto-delete message 5 min (job_queue), DB delivered retained 30 days then purged; audit.log 30 days. No permanent reuse.

<b>Your rights (DPDP):</b> Access, correction, erasure, grievance — use /privacy → Delete my data. Contact DPO {DPO}.

<b>Security:</b> Sessions encrypted at rest (Fernet, key derived from ADMIN_ID, not logged), HMAC 64 callbacks, 12-digit UTR dedupe, rate limits, banned, .env never committed, audit masked.

<b>Consent:</b> /start requires I Agree (logged). No consent = no data stored.

<i>Nothing sensitive is revealed in logs or GitHub — tokens/UTR/phone masked.</i>
"""

TERMS_TEXT = f"""📜 <b>Terms & Conditions — TG STOCK BOT</b>

<b>Business:</b> {BUSINESS} | UPI {UPI_MASKED} | Support {SUPPORT}

1. You must be 18+. Real permanent accounts only — stock empty until admin adds via secure CSV.
2. Price = cost + margin. <b>Rule: 5+ accounts → 10% OFF, below 5 → full pay.</b> Wholesale after 5 taken.
3. Add Funds: ₹50-₹10000, 12-digit UTR exactly, screenshot optional but OCR verified. Duplicate UTR rejected.
4. ALL SALES FINAL — no free permanent reuse. Refund only if undelivered per Refund Policy.
5. No bots, flood, or callback tampering (HMAC 64, rate 2s/5-per-min/20-per-min, banned). Violation = ban.
6. Accounts are permanent StringSession — source supplier panel. Not investment.
7. UPI for payouts only. You declare tax.
8. We may update terms — continued use = acceptance. Support {SUPPORT}.
"""

COOKIE_TEXT = """🍪 <b>Cookie Policy — TG STOCK BOT</b>

This bot has <b>no cookies</b> (no WebApp, no website analytics, no third-party iframes). Telegram stores message/file_ids per its policy.

If we add analytics (e.g., Plausible) later, we will show opt-in banner (necessary vs analytics) and list here. No tracking until you consent.

Third-party embeds: none (only first-party qr_navi.jpg & welcome.png Pillow-generated).
"""

REFUND_TEXT = f"""💸 <b>Refund Policy — TG STOCK BOT</b>

<b>Business:</b> {BUSINESS} | Support {SUPPORT}

• Stock empty → real accounts added manually. Delivery: StringSession + phone, auto-delete 5 min.
• <b>Eligible:</b> Not delivered within 30 min of approved payment, or duplicate charge (UTR dedupe fail).
• <b>Not eligible:</b> Delivered permanent session (even if you change mind), ALL SALES FINAL per Terms.
• Process: Contact {SUPPORT} with UTR (12-digit) + order ID (last 10) — review 24h, refund to same UPI if approved.
• DPDP: refunds logged masked in audit.log, no raw UTR/phone revealed.

<i>Rule respected: 5+ wholesale 10% OFF, else full pay — refund amount follows paid final_price.</i>
"""

CONSENT_TEXT = """✅ <b>Consent Required</b>

To use TG STOCK BOT you must agree to Privacy, Terms, Cookie & Refund.

Tap I Agree to consent (logged with timestamp, DPDP). No consent = no data stored.

You can withdraw via /privacy → Delete my data.
"""

async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PRIVACY_TEXT, parse_mode="HTML")

async def terms_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TERMS_TEXT, parse_mode="HTML")

async def cookie_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COOKIE_TEXT, parse_mode="HTML")

async def refund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(REFUND_TEXT, parse_mode="HTML")

async def delete_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    # hardcore: mask, audit, then anonymize
    security.audit("delete_request", uid, "user requested erasure")
    # anonymize: clear username/first_name, keep balance/orders for audit but mark
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cur = conn.cursor()
    cur.execute("UPDATE users SET username='deleted', first_name='deleted' WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Your username/first_name anonymized. Orders retained 30 days per law then purged. For full erasure contact DPO @samosawithchatni", parse_mode="HTML")
    security.audit("delete_done", uid, "anonymized")

# consent keyboard
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
def consent_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I Agree (Privacy•Terms•Cookie•Refund)", callback_data="consent:agree")],
        [InlineKeyboardButton("❌ I Disagree", callback_data="consent:disagree")],
        [InlineKeyboardButton("📄 Privacy", callback_data="legal:privacy"), InlineKeyboardButton("📜 Terms", callback_data="legal:terms")],
        [InlineKeyboardButton("🍪 Cookie", callback_data="legal:cookie"), InlineKeyboardButton("💸 Refund", callback_data="legal:refund")],
    ])

async def legal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "legal:privacy":
        await q.message.reply_text(PRIVACY_TEXT, parse_mode="HTML")
    elif data == "legal:terms":
        await q.message.reply_text(TERMS_TEXT, parse_mode="HTML")
    elif data == "legal:cookie":
        await q.message.reply_text(COOKIE_TEXT, parse_mode="HTML")
    elif data == "legal:refund":
        await q.message.reply_text(REFUND_TEXT, parse_mode="HTML")

async def consent_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    if q.data == "consent:agree":
        context.user_data["consented"] = True
        context.user_data["consent_ts"] = int(time.time())
        security.audit("consent_agree", uid, "DPDP")
        await q.edit_message_text("✅ Consent logged. Welcome — real permanent only.", reply_markup=None)
        # trigger start flow
        from handlers.start import welcome_text
        import keyboards
        import db as dbmod
        text = welcome_text(uid)
        try:
            from utils.welcome_image import generate_welcome_image
            u = dbmod.get_user(uid)
            bal = u[3] if u else 0
            wholesale = dbmod.is_wholesale(uid)
            fname = u[2] if u and u[2] else q.from_user.first_name
            tmp_path = f"assets/welcome_{uid}.png"
            generate_welcome_image(fname or "Anonymous", bal, wholesale, tmp_path)
            await q.message.reply_photo(photo=open(tmp_path,"rb"), caption=text, reply_markup=keyboards.main_menu_kb(uid), parse_mode="HTML")
            import os
            try: os.remove(tmp_path)
            except: pass
        except Exception as e:
            import keyboards
            await q.message.reply_text(text, reply_markup=keyboards.main_menu_kb(uid), parse_mode="HTML")
    else:
        security.audit("consent_disagree", uid, "")
        await q.edit_message_text("You must agree to use this bot. Send /start to try again.")
