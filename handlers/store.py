from telegram import Update
from telegram.ext import ContextTypes
import keyboards

STORE_TEXT = (
    "📦 <b>Telegram Accounts Store</b>\n\n"
    "1️⃣ <b>Budget Accounts</b> — All origins, most affordable\n"
    "2️⃣ <b>Premium Quality</b> — Trusted Autoreg/Personal only\n\n"
    "⚠️ <b>ALL SALES ARE FINAL. NO REFUNDS.</b>\n"
    "🔒 <i>Secure — Real permanent accounts only. Stock added manually when available.</i>"
)

async def menu_store_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(STORE_TEXT, reply_markup=keyboards.store_menu_kb(), parse_mode="HTML")
    except Exception:
        await query.message.reply_text(STORE_TEXT, reply_markup=keyboards.store_menu_kb(), parse_mode="HTML")

async def store_pick_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # store:budget or store:premium
    acctype = data.split(":")[1]
    title = "Cheap" if acctype == "budget" else "Premium"
    text = (
        f"📱 <b>TG Accounts — {title}</b>\n\n"
        f"🌍 <b>Select a Region:</b>"
    )
    try:
        await query.edit_message_text(text, reply_markup=keyboards.region_menu_kb(acctype), parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, reply_markup=keyboards.region_menu_kb(acctype), parse_mode="HTML")
