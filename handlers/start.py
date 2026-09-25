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
    name = fname if fname and fname.strip().lower() != "anonymous" else "Anonymous"
    wholesale_str = "✅ Wholesale Enabled 10% OFF" if wholesale else "❌ Wholesale Disabled"
    return (
        f"👋 Welcome, {name} ji! to TG STOCK BOT\n\n"
        f"💳 Balance: ₹{bal:.2f}\n"
        f"💎 Bot Status: {wholesale_str}\n\n"
        f"🔒 Real permanent accounts only — tap 🛒 Purchase Tg Account to browse.\n"
        f"Support @samosawithchatni • UPI alphajip1@naviaxis"
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
    # generate welcome PNG
    try:
        from utils.welcome_image import generate_welcome_image
        u = db.get_user(user.id)
        bal = u[3] if u else 0
        wholesale = bool(u[4]) if u else True
        fname = u[2] if u and u[2] else user.first_name
        tmp_path = f"assets/welcome_{user.id}.png"
        generate_welcome_image(fname or "Anonymous", bal, wholesale, tmp_path)
        await update.message.reply_photo(photo=open(tmp_path, "rb"), caption=text, reply_markup=keyboards.main_menu_kb(user.id), parse_mode="HTML")
        try:
            import os
            os.remove(tmp_path)
        except: pass
        return
    except Exception as e:
        security.audit("welcome_img_fail", user.id, str(e)[:100])
    await update.message.reply_text(text, reply_markup=keyboards.main_menu_kb(user.id))

async def menu_main_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    db.ensure_user(uid, query.from_user.username, query.from_user.first_name)
    text = welcome_text(uid)
    # try to edit as photo if original was photo, else text
    try:
        from utils.welcome_image import generate_welcome_image
        u = db.get_user(uid)
        bal = u[3] if u else 0
        wholesale = bool(u[4]) if u else True
        fname = u[2] if u and u[2] else query.from_user.first_name
        tmp_path = f"assets/welcome_{uid}.png"
        generate_welcome_image(fname or "Anonymous", bal, wholesale, tmp_path)
        # delete old message and send new photo (edit_message_media requires file)
        try:
            await query.message.delete()
        except: pass
        await query.message.reply_photo(photo=open(tmp_path, "rb"), caption=text, reply_markup=keyboards.main_menu_kb(uid), parse_mode="HTML")
        try:
            import os
            os.remove(tmp_path)
        except: pass
        return
    except Exception as e:
        security.audit("menu_img_fail", uid, str(e)[:100])
    try:
        await query.edit_message_text(text, reply_markup=keyboards.main_menu_kb(uid))
    except Exception:
        await query.message.reply_text(text, reply_markup=keyboards.main_menu_kb(uid))
