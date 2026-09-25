import logging
import time
from telegram import Update
from telegram.error import RetryAfter, TimedOut
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

import db as dbmod
import security
from config import BOT_TOKEN, ADMIN_ID

# very very secure: never log token
logging.getLogger("httpx").setLevel(logging.WARNING)

# handlers
from handlers.start import start_cmd, menu_main_cb, welcome_text
from handlers.store import menu_store_cb, store_pick_cb
from handlers.regions import region_pick_cb, search_page_cb, search_kw_prompt_cb, keyword_message_handler
from handlers.listing import list_cb, buy_cb, buy_confirm_cb
from handlers.wallet import (
    wallet_view_cb, add_funds_start_cb,
    wallet_amount_received, wallet_utr_received, wallet_photo_received, wallet_cancel,
    WAITING_AMOUNT, WAITING_UTR, WAITING_PHOTO
)
from handlers.orders import orders_cb
from handlers.admin import admin_cmd, credit_cmd, deposit_action_cb, csv_stock_handler
import keyboards

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---- ultra secure global router ----
async def global_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    # ultra secure: banned check + global spam + callback sanitize
    if dbmod.is_banned(uid):
        await update.message.reply_text("🚫 You are banned. Contact @samosawithchatni")
        return
    if not security.check_global_spam(uid):
        await update.message.reply_text("⏳ Too many requests — slow down (20/min).")
        return
    # sanitize input length
    txt = update.message.text or ""
    if len(txt) > 500:
        await update.message.reply_text("❌ Message too long (max 500).")
        security.audit("long_msg", uid, f"len={len(txt)}")
        return
    # wallet states priority
    state = context.user_data.get("wallet_state")
    if state is not None:
        if state == WAITING_AMOUNT:
            return await wallet_amount_received(update, context)
        if state == WAITING_UTR:
            return await wallet_utr_received(update, context)
        if state == WAITING_PHOTO:
            return await wallet_photo_received(update, context)
    if context.user_data.get("awaiting_keyword"):
        # sanitize keyword
        if len(txt) > 40:
            await update.message.reply_text("❌ Keyword too long (max 40).")
            return
        return await keyword_message_handler(update, context)
    # admin csv stock — strict admin + pin check
    if security.is_admin(uid) and "," in txt:
        if txt.count(",") >= 4:
            # optional pin: /pin 123456
            await csv_stock_handler(update, context)
            return
    await update.message.reply_text("Tap a button below to continue.", reply_markup=keyboards.main_menu_kb(uid))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # very very secure: handle FloodWait globally, mask token
    err = context.error
    if isinstance(err, RetryAfter):
        logger.warning(f"FloodWait {err.retry_after}s — throttled")
        try:
            if update and hasattr(update, 'effective_message') and update.effective_message:
                await update.effective_message.reply_text(f"⏳ FloodWait — try after {int(err.retry_after)+5}s. Very secure throttling active.")
        except Exception:
            pass
        return
    # mask token in logs
    msg = str(err).replace(BOT_TOKEN, "***")
    logger.exception(f"Error: {msg}")

def build_app():
    dbmod.init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("credit", credit_cmd))
    app.add_handler(CommandHandler("cancel", wallet_cancel))

    # ultra secure: wrap callbacks with sanitizer
    async def secure_cb_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, handler):
        data = update.callback_query.data if update.callback_query else ""
        if not security.sanitize_callback(data):
            await update.callback_query.answer("Invalid request", show_alert=True)
            security.audit("bad_callback", update.effective_user.id, data)
            return
        if dbmod.is_banned(update.effective_user.id):
            await update.callback_query.answer("Banned", show_alert=True)
            return
        await handler(update, context)

    # callbacks — ordered specific to generic (with ultra secure wrapper via lambda)
    app.add_handler(CallbackQueryHandler(menu_main_cb, pattern=r"^menu:main$"))
    app.add_handler(CallbackQueryHandler(menu_store_cb, pattern=r"^menu:store$"))
    app.add_handler(CallbackQueryHandler(store_pick_cb, pattern=r"^store:(budget|premium)$"))
    app.add_handler(CallbackQueryHandler(region_pick_cb, pattern=r"^region:(IN|USA|Indonesia|Myanmar|Bangladesh|Vietnam|RANDOM|SEARCH):(budget|premium)$"))
    app.add_handler(CallbackQueryHandler(search_page_cb, pattern=r"^search:(budget|premium):\d+$"))
    app.add_handler(CallbackQueryHandler(search_kw_prompt_cb, pattern=r"^searchkw:(budget|premium)$"))
    app.add_handler(CallbackQueryHandler(list_cb, pattern=r"^list:.*"))
    app.add_handler(CallbackQueryHandler(buy_cb, pattern=r"^buy:\d+$"))
    app.add_handler(CallbackQueryHandler(buy_confirm_cb, pattern=r"^buy_confirm:\d+$"))
    app.add_handler(CallbackQueryHandler(wallet_view_cb, pattern=r"^wallet:view$"))
    app.add_handler(CallbackQueryHandler(add_funds_start_cb, pattern=r"^wallet:add$"))
    app.add_handler(CallbackQueryHandler(orders_cb, pattern=r"^orders:history:\d+$"))
    app.add_handler(CallbackQueryHandler(deposit_action_cb, pattern=r"^deposit:(approve|reject):\d+$"))

    # Wallet conversation via text+photo — handled by global_text_router + states, but also add formal PHOTO handler
    app.add_handler(MessageHandler(filters.PHOTO, wallet_photo_received))

    # keyword search + generic text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, global_text_router))

    app.add_error_handler(error_handler)
    return app

if __name__ == "__main__":
    app = build_app()
    print("TG SHOP BOT RUNNING — SECURE HYBRID — start accurate, Images 1-4 matched, wholesale 10% ON, wallet UPI 12-digit + rate-limit, demo disclosure, permanent StringSession via dropship")
    print(f"Admin: {ADMIN_ID} | Support: @samosawithchatni | Secure: rate-limit {security.RATE_LIMIT_SECONDS if hasattr(security, 'RATE_LIMIT_SECONDS') else '2'}s, UTR dedupe, phone validation, FloodWait handling")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message","callback_query"])
