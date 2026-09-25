from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards
import security

def welcome_text(user_id):
    u = db.get_user(user_id)
    if u:
        bal = u[3]
        wholesale = u[4]
        fname = u[2] or "Anonymous"
    else:
        bal = 0
        wholesale = 1
        fname = "Anonymous"
    # ensure Anonymous ji! exactly as screenshot
    name = fname if fname and fname.strip().lower() != "anonymous" else "Anonymous"
    # screenshot: 👋 Welcome, Anonymous ji!
    # Balance: ₹0.00
    # Bot Status: ✅ Wholesale Enabled
    wholesale_str = "✅ Wholesale Enabled" if wholesale else "❌ Wholesale Disabled"
    return (
        f"👋 Welcome, {name} ji!\n\n"
        f"💳 Balance: ₹{bal:.2f}\n"
        f"💎 Bot Status: {wholesale_str}"
    )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        await update.message.reply_text("🚫 Banned.")
        security.audit("start_banned", user.id, "")
        return
    if not security.check_global_spam(user.id):
        await update.message.reply_text("⏳ Slow down.")
        return
    if not db.ensure_user(user.id, user.username, user.first_name):
        await update.message.reply_text("🚫 Banned.")
        return
    security.audit("start", user.id, f"@{user.username}")
    text = welcome_text(user.id)
    await update.message.reply_text(text, reply_markup=keyboards.main_menu_kb(user.id))

async def menu_main_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    db.ensure_user(uid, query.from_user.username, query.from_user.first_name)
    text = welcome_text(uid)
    try:
        await query.edit_message_text(text, reply_markup=keyboards.main_menu_kb(uid))
    except Exception:
        await query.message.reply_text(text, reply_markup=keyboards.main_menu_kb(uid))
