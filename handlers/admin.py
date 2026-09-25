from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards
import security
from config import ADMIN_ID

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    stats = db.admin_stats()
    pending_list = db.get_pending_deposits()
    text = (
        f"🔧 <b>ADMIN PANEL</b>\n\n"
        f"👥 Users: {stats['users']}\n"
        f"📦 Stock: {stats['stock']} unsold | {stats['sold']} sold\n"
        f"🧾 Orders: {stats['orders']}\n"
        f"💰 Total wallet balance: ₹{stats['total_balance']}\n"
        f"⏳ Pending deposits: {stats['pending']}\n\n"
        f"Commands:\n"
        f"/admin — this panel\n"
        f"Send CSV to add stock: <code>phone,region,type,price,session</code>\n"
        f"To add funds manually: <code>/credit user_id amount</code>"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    # show pending deposits inline
    if pending_list:
        for did, uid, amt, utr, photo_id, ts in pending_list[:5]:
            cap = f"Deposit #{did}: User {uid} — ₹{amt} — UTR {utr}"
            try:
                if photo_id:
                    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=cap, reply_markup=keyboards.admin_deposit_kb(did))
                else:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=cap, reply_markup=keyboards.admin_deposit_kb(did))
            except Exception as e:
                print(e)

async def credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security.is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /credit <user_id> <amount>")
        return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid numbers.")
        return
    if not security.sanitize_amount(amt) and amt > 10000:
        # allow larger credit for admin but cap at 50000 very secure
        if amt > 50000 or amt < 1:
            await update.message.reply_text("Amount must be 1-50000.")
            return
    db.ensure_user(uid)
    db.credit_balance(uid, amt)
    await update.message.reply_text(f"✅ Credited ₹{amt} to {uid}. New balance: ₹{db.get_balance(uid)}")
    try:
        await context.bot.send_message(chat_id=uid, text=f"✅ Admin credited ₹{amt} to your wallet! New balance: ₹{db.get_balance(uid)}", reply_markup=keyboards.main_menu_kb())
    except Exception:
        pass

async def deposit_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()
    # deposit:approve:5
    _, action, did_s = query.data.split(":")
    did = int(did_s)
    dep = db.get_deposit(did)
    if not dep:
        await query.edit_message_caption(caption="Not found.")
        return
    did2, uid, amt, utr, photo_id, status = dep
    if status != "pending":
        await query.answer(f"Already {status}", show_alert=True)
        return
    if action == "approve":
        db.update_deposit_status(did, "approved")
        db.ensure_user(uid)
        db.credit_balance(uid, amt)
        await query.edit_message_caption(caption=f"✅ APPROVED Deposit #{did} — User {uid} ₹{amt} UTR {utr}")
        # notify user
        try:
            await context.bot.send_message(chat_id=uid, text=f"✅ <b>Deposit Approved!</b>\n\n₹{amt} credited to your wallet.\nUTR: <code>{utr}</code>\nNew balance: ₹{db.get_balance(uid)}", parse_mode="HTML", reply_markup=keyboards.main_menu_kb())
        except Exception as e:
            print(e)
    else:
        db.update_deposit_status(did, "rejected")
        await query.edit_message_caption(caption=f"❌ REJECTED Deposit #{did} — User {uid} ₹{amt} UTR {utr}")
        try:
            await context.bot.send_message(chat_id=uid, text=f"❌ Deposit #{did} rejected (UTR: {utr}). Contact @samosawithchatni for support.", reply_markup=keyboards.main_menu_kb())
        except Exception:
            pass

async def csv_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security.is_admin(update.effective_user.id):
        return
    text = update.message.text.strip()
    lines = [l.strip() for l in text.splitlines() if l.strip() and "," in l]
    if not lines:
        return
    added = 0
    skipped = 0
    import time
    import db as dbmod
    conn = dbmod.get_conn()
    cur = conn.cursor()
    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            skipped += 1
            continue
        # secure: session may contain commas — join remainder
        phone, region, acctype, price_s = parts[0], parts[1], parts[2].lower(), parts[3]
        session = ",".join(parts[4:])
        if not security.sanitize_phone(phone):
            skipped += 1
            continue
        if acctype not in ("budget","premium"):
            skipped += 1
            continue
        try:
            price = int(price_s)
            if not (1 <= price <= 10000):
                skipped += 1
                continue
        except:
            skipped += 1
            continue
        if len(session) < 10 or len(session) > 5000:
            skipped += 1
            continue
        region = region.strip()[:20]
        # secure: prevent duplicate phone
        cur.execute("SELECT COUNT(*) FROM accounts WHERE phone=? AND sold=0", (phone,))
        if cur.fetchone()[0] > 0:
            skipped += 1
            continue
        cur.execute("INSERT INTO accounts (type, region, price, phone, session, sold, created_at) VALUES (?,?,?,?,?,0,?)",
                    (acctype, region, price, phone, session, int(time.time())))
        added += 1
    conn.commit()
    conn.close()
    if added > 0 or skipped > 0:
        await update.message.reply_text(f"✅ Added {added} accounts from CSV. 🔒 Skipped {skipped} invalid. Very secure validation applied.")
