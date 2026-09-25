from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards
import security
from config import UPI_ID, UPI_NAME, ADMIN_ID

WAITING_AMOUNT, WAITING_UTR, WAITING_PHOTO = range(3)

async def wallet_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    u = db.get_user(uid)
    bal = u[3] if u else 0
    cnt = db.total_orders(uid)
    wholesale = "✅ 10% OFF (5+)" if db.is_wholesale(uid) else f"❌ Locked — {5-cnt} more for 10% OFF"
    text = (
        f"🧾 <b>Your Wallet</b>\n\n"
        f"💳 Balance: <b>₹{bal:.2f}</b>\n"
        f"📦 Taken: {cnt}/5\n"
        f"💎 Status: {wholesale}\n\n"
        f"Tap 💵 Add Funds to add money via UPI (manual verification).\n"
        f"<i>Privacy: UTR masked, 30-day retention. See 📄 Privacy.</i>"
    )
    await query.edit_message_text(text, reply_markup=keyboards.wallet_kb(), parse_mode="HTML")

async def add_funds_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # hardcore: require consent before funds (DPDP)
    if not context.user_data.get("consented"):
        from handlers.legal import CONSENT_TEXT, consent_kb
        await query.message.reply_text(CONSENT_TEXT, reply_markup=consent_kb(), parse_mode="HTML")
        return -1
    await query.message.reply_text(
        f"💵 <b>Add Funds — UPI Manual</b>\n\n"
        f"Send the amount you want to add (min ₹50).\n"
        f"Example: <code>500</code>\n\n"
        f"Type /cancel to abort.\n"
        f"<i>By adding funds you agree to Privacy, Terms & Refund — see 📄 Privacy in menu.</i>",
        parse_mode="HTML"
    )
    context.user_data["wallet_state"] = WAITING_AMOUNT
    return WAITING_AMOUNT

# Conversation handlers (also usable as message handlers)
async def wallet_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security.check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⏳ Too fast. Wait 2s.")
        return WAITING_AMOUNT
    if not security.can_deposit(update.effective_user.id):
        await update.message.reply_text("❌ Too many deposits this hour (max 3). Try later or contact @samosawithchatni.")
        return WAITING_AMOUNT
    txt = update.message.text.strip()
    if txt.startswith("/"):
        await update.message.reply_text("Cancelled.", reply_markup=keyboards.main_menu_kb())
        context.user_data.pop("wallet_state", None)
        return -1
    try:
        amt = int(txt.replace("₹","").replace(",","").strip())
    except ValueError:
        await update.message.reply_text("❌ Send a valid number, e.g. 500. Try again or /cancel")
        return WAITING_AMOUNT
    if not security.sanitize_amount(amt):
        await update.message.reply_text("❌ Amount must be ₹50-₹10000. Try again or /cancel")
        return WAITING_AMOUNT
    context.user_data["pending_amount"] = amt
    # ultra secure: send QR for alphajip1@naviaxis
    qr_path = "assets/qr_navi.jpg"
    caption = (
        f"✅ Amount: <b>₹{amt}</b>\n\n"
        f"Pay via any UPI app — scan QR or use ID:\n"
        f"UPI ID: <code>{UPI_ID}</code>\n"
        f"Name: {UPI_NAME}\n\n"
        f"URI: <code>upi://pay?pa={UPI_ID}&pn={UPI_NAME.replace(' ','%20')}&am={amt}&cu=INR</code>\n\n"
        f"After paying, send your <b>UTR / Transaction ID / Reference No.</b> (12 digits).\n"
        f"Then send a <b>screenshot</b> of payment.\n\n"
        f"First, send UTR as text."
    )
    try:
        import os
        if os.path.exists(qr_path):
            await update.message.reply_photo(photo=open(qr_path, "rb"), caption=caption, parse_mode="HTML")
        else:
            await update.message.reply_text(caption, parse_mode="HTML")
    except Exception:
        await update.message.reply_text(caption, parse_mode="HTML")
    context.user_data["wallet_state"] = WAITING_UTR
    return WAITING_UTR

async def wallet_utr_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip().replace(" ", "")
    if txt.startswith("/"):
        await update.message.reply_text("Cancelled.", reply_markup=keyboards.main_menu_kb())
        context.user_data.pop("wallet_state", None)
        context.user_data.pop("pending_amount", None)
        return -1
    if not security.sanitize_utr(txt):
        await update.message.reply_text("❌ Invalid UTR. Send exactly <b>12 digits</b> (e.g. <code>123456789012</code>).\nType /cancel to abort.", parse_mode="HTML")
        return WAITING_UTR
    # secure: prevent duplicate UTR
    if db.is_utr_used(txt):
        await update.message.reply_text("❌ This UTR already submitted. Use a new transaction or contact support.", parse_mode="HTML")
        return WAITING_UTR
    context.user_data["pending_utr"] = txt
    await update.message.reply_text(
        f"✅ UTR saved: <code>{txt}</code>\n\n"
        f"Now send a <b>screenshot</b> of the payment as a photo.\n"
        f"If you can't send photo, type <code>skip</code> to submit without it.\n"
        f"Type /cancel to abort.",
        parse_mode="HTML"
    )
    context.user_data["wallet_state"] = WAITING_PHOTO
    return WAITING_PHOTO

async def wallet_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # can be photo or text "skip" — ultra secure + OCR
    photo_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        # ultra secure: OCR verify UTR in screenshot if possible (non-blocking)
        utr = context.user_data.get("pending_utr", "")
        if utr and photo_id:
            try:
                # lazy OCR — try EasyOCR, fallback to no-check
                import asyncio
                from pathlib import Path
                f = await context.bot.get_file(photo_id)
                tmp = Path(f"./tmp_ocr_{utr}.jpg")
                await f.download_to_drive(tmp)
                # try EasyOCR (if .EasyOCR cached)
                try:
                    import easyocr
                    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                    res = reader.readtext(str(tmp), detail=0)
                    text = " ".join(res)
                    digits = "".join(c for c in text if c.isdigit())
                    # if UTR not found in screenshot, warn but still accept (admin will verify)
                    if utr not in text and utr not in digits:
                        await update.message.reply_text(f"⚠️ UTR <code>{utr}</code> not detected in screenshot text. Ensure screenshot is clear. Admin will manually verify.", parse_mode="HTML")
                        security.audit("ocr_mismatch", update.effective_user.id, f"utr={security.mask_utr(utr)} ocr_digits={digits[:20]}")
                    else:
                        security.audit("ocr_match", update.effective_user.id, f"utr={security.mask_utr(utr)}")
                except Exception as e:
                    security.audit("ocr_skip", update.effective_user.id, f"easyocr fail {e}"[:100])
                try:
                    tmp.unlink(missing_ok=True)
                except: pass
            except Exception as e:
                security.audit("ocr_error", update.effective_user.id, str(e)[:100])
    elif update.message.text and update.message.text.strip().lower() == "skip":
        photo_id = None
        security.audit("deposit_skip_photo", update.effective_user.id, f"utr={security.mask_utr(context.user_data.get('pending_utr',''))}")
    elif update.message.text and update.message.text.strip().startswith("/"):
        await update.message.reply_text("Cancelled.", reply_markup=keyboards.main_menu_kb())
        context.user_data.pop("wallet_state", None)
        context.user_data.pop("pending_amount", None)
        context.user_data.pop("pending_utr", None)
        return -1
    else:
        await update.message.reply_text("Please send a photo screenshot or type `skip` to submit without photo.", parse_mode="HTML")
        return WAITING_PHOTO

    amt = context.user_data.get("pending_amount")
    utr = context.user_data.get("pending_utr")
    uid = update.effective_user.id
    if not amt or not utr:
        await update.message.reply_text("Session expired. Please tap 💵 Add Funds again.", reply_markup=keyboards.main_menu_kb())
        context.user_data.clear()
        return -1

    # ultra secure: audit
    security.audit("deposit_submit", uid, f"amt={amt} utr={security.mask_utr(utr)} photo={'yes' if photo_id else 'no'}")
    did = db.create_deposit(uid, amt, utr, photo_id)
    username = update.effective_user.username or "no_username"
    fname = update.effective_user.first_name or "Anonymous"
    await update.message.reply_text(
        f"✅ <b>Deposit Submitted!</b>\n\n"
        f"Amount: ₹{amt}\nUTR: <code>{utr}</code>\nID: #{did}\n\n"
        f"Admin will verify within 1-2 hours. You’ll be notified on approval.\n"
        f"Check 🧾 View Wallet for balance.",
        parse_mode="HTML",
        reply_markup=keyboards.main_menu_kb()
    )
    # notify admin
    try:
        caption = f"💰 NEW DEPOSIT #{did}\nUser: {uid} (@{username} / {fname})\nAmount: ₹{amt}\nUTR: {utr}"
        kb = keyboards.admin_deposit_kb(did)
        if photo_id:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=kb)
    except Exception as e:
        print(f"[WARN] admin notify failed: {e}")

    context.user_data.pop("wallet_state", None)
    context.user_data.pop("pending_amount", None)
    context.user_data.pop("pending_utr", None)
    return -1

async def wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=keyboards.main_menu_kb())
    context.user_data.pop("wallet_state", None)
    context.user_data.pop("pending_amount", None)
    context.user_data.pop("pending_utr", None)
    return -1

# fallback for direct text handler when not in conversation — start amount flow if user sends number while awaiting?
async def wallet_text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("wallet_state")
    if state == WAITING_AMOUNT:
        return await wallet_amount_received(update, context)
    if state == WAITING_UTR:
        return await wallet_utr_received(update, context)
    if state == WAITING_PHOTO:
        return await wallet_photo_received(update, context)
