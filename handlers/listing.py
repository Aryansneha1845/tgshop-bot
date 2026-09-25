from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards
import security
from config import WHOLESALE_DISCOUNT

PER_PAGE = 6

def show_listing_text(acctype, region, page=0):
    db.auto_topup_if_low(acctype, region)
    total = db.total_accounts(acctype, region)
    rows = db.get_accounts(acctype, region, limit=PER_PAGE, offset=page*PER_PAGE)
    title_type = "Cheap" if acctype == "budget" else "Premium"
    region_label = region if region != "RANDOM" else "Random"
    if region == "RANDOM":
        header = f"📱 <b>TG Accounts — {title_type} | Random</b>\n\nShowing {total} accounts. Tap to buy 👇\nPage {page+1} of {max(1, (total+PER_PAGE-1)//PER_PAGE)}"
    else:
        short = region
        header = f"📱 <b>TG Accounts — {title_type} | {short}</b>\n\nShowing {total} accounts. Tap to buy 👇\nPage {page+1} of {max(1, (total+PER_PAGE-1)//PER_PAGE)}"
    if total == 0:
        header = f"📱 <b>TG Accounts — {title_type} | {region}</b>\n\n❌ No accounts available right now.\nStock empty — admin will add real permanent accounts soon. Try 🔄 Refresh.\n\n🔒 <i>Secure: Real accounts only. No demo.</i>"
    kb = keyboards.listing_kb(acctype, region, rows, page, total)
    return header, kb

async def show_listing(query_or_update, acctype, region, page=0, edit=True):
    header, kb = show_listing_text(acctype, region, page)
    if edit and hasattr(query_or_update, 'edit_message_text'):
        try:
            await query_or_update.edit_message_text(header, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await query_or_update.message.reply_text(header, reply_markup=kb, parse_mode="HTML")
    else:
        # update is Message
        await query_or_update.reply_text(header, reply_markup=kb, parse_mode="HTML")

async def list_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # list:IN:budget:0  or list:IN:budget:0:refresh
    parts = data.split(":")
    region = parts[1]
    acctype = parts[2]
    page = int(parts[3])
    # refresh check
    await show_listing(query, acctype, region, page, edit=True)

async def buy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security.check_rate_limit(update.callback_query.from_user.id):
        await update.callback_query.answer("Too fast — wait 2s", show_alert=True)
        return
    query = update.callback_query
    # ultra secure: verify HMAC signed callback
    ok, raw = security.verify_callback(query.data)
    if not ok or not raw.startswith("buy:"):
        await query.answer("Invalid/tampered request", show_alert=True)
        security.audit("bad_buy_sig", query.from_user.id, query.data)
        return
    await query.answer()
    aid = int(raw.split(":")[1])
    acc = db.get_account_by_id(aid)
    if not acc:
        await query.answer("Account not found / already sold. Refresh.", show_alert=True)
        return
    aid2, acctype, region, price, phone, session, sold = acc
    if sold == 1:
        await query.answer("Already sold! Tap Refresh.", show_alert=True)
        return
    uid = query.from_user.id
    bal = db.get_balance(uid)
    wholesale = db.is_wholesale(uid)
    final_price = int(price * (1 - WHOLESALE_DISCOUNT)) if wholesale else price
    # check balance
    if bal < final_price:
        need = final_price - bal
        await query.edit_message_text(
            f"❌ <b>Insufficient Balance</b>\n\n"
            f"Account: {db.flag_for(region)} {region} — ₹{price}\n"
            f"Wholesale 10% OFF: <b>₹{final_price}</b>\n"
            f"Your balance: ₹{bal}\n"
            f"Need ₹{need} more.\n\n"
            f"Tap 💵 Add Funds to top up.",
            reply_markup=keyboards.wallet_kb(),
            parse_mode="HTML"
        )
        return
    # confirm screen
    discount_note = f" (Wholesale 10% OFF: ₹{price} → <b>₹{final_price}</b>)" if wholesale else ""
    text = (
        f"🛒 <b>Confirm Purchase</b>\n\n"
        f"{db.flag_for(region)} <b>{region}</b> | {acctype.title()}\n"
        f"Price: ₹{price}{discount_note}\n"
        f"Your balance after: ₹{bal - final_price}\n\n"
        f"Tap ✅ to confirm delivery."
    )
    await query.edit_message_text(text, reply_markup=keyboards.buy_confirm_kb(aid), parse_mode="HTML")

async def buy_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security.can_purchase(update.callback_query.from_user.id):
        await update.callback_query.answer("Too many purchases — wait 1 min", show_alert=True)
        return
    if not security.check_rate_limit(update.callback_query.from_user.id):
        await update.callback_query.answer("Too fast — wait 2s", show_alert=True)
        return
    query = update.callback_query
    ok, raw = security.verify_callback(query.data)
    if not ok or not raw.startswith("buy_confirm:"):
        await query.answer("Invalid/tampered", show_alert=True)
        security.audit("bad_confirm_sig", query.from_user.id, query.data)
        return
    await query.answer()
    aid = int(raw.split(":")[1])
    acc = db.get_account_by_id(aid)
    if not acc:
        await query.answer("Not found. Refresh.", show_alert=True)
        return
    aid2, acctype, region, price, phone, session, sold = acc
    if sold == 1:
        await query.edit_message_text("❌ Already sold. Please refresh list.", reply_markup=keyboards.main_menu_kb())
        return
    uid = query.from_user.id
    bal = db.get_balance(uid)
    wholesale = db.is_wholesale(uid)
    final_price = int(price * (1 - WHOLESALE_DISCOUNT)) if wholesale else price
    if bal < final_price:
        await query.edit_message_text(f"❌ Balance too low. Need ₹{final_price}, you have ₹{bal}.", reply_markup=keyboards.wallet_kb())
        return
    # atomic: debit + mark sold
    ok = db.debit_balance(uid, final_price)
    if not ok:
        await query.edit_message_text("❌ Debit failed. Try again.", reply_markup=keyboards.wallet_kb())
        return
    sold_ok = db.mark_sold(aid, uid)
    if not sold_ok:
        # refund
        db.credit_balance(uid, final_price)
        await query.edit_message_text("❌ Just got sold by someone else. Amount refunded.", reply_markup=keyboards.main_menu_kb())
        return
    delivered = f"Phone: {phone}\nSession: {session}\nRegion: {region}\nType: {acctype}"
    db.create_order(uid, aid, final_price, price, region, acctype, phone, delivered)
    security.audit("purchase", uid, f"aid={aid} price={final_price} region={region}")
    db.auto_topup_if_low(acctype, region)
    sent_msgs = []
    try:
        await query.edit_message_text(
            f"✅ <b>Purchase Successful!</b>\n\n"
            f"{db.flag_for(region)} <b>{region} {acctype.title()}</b>\n"
            f"Paid: ₹{final_price} (orig ₹{price})\n"
            f"Remaining balance: ₹{db.get_balance(uid)}\n\n"
            f"<b>Your Account:</b>\n"
            f"📞 <code>{phone}</code>\n"
            f"🔑 <code>{session}</code>\n\n"
            f"🔒 <i>Secure: Save now — messages auto-delete in 5 min. Do not share. Permanent StringSession.</i>\n"
            f"Support @samosawithchatni",
            parse_mode="HTML",
            reply_markup=keyboards.main_menu_kb(uid)
        )
        sent_msgs.append((query.message.chat_id, query.message.message_id))
    except Exception as e:
        if "Flood" in str(e) or "RetryAfter" in str(e):
            await query.message.reply_text(f"⏳ FloodWait — try after {e}. Contact support.", reply_markup=keyboards.main_menu_kb(uid))
            db.credit_balance(uid, final_price)
            db.create_order(uid, aid, 0, price, region, acctype, phone, f"FLOODWAIT refund {e}")
            return
        raise
    try:
        m = await context.bot.send_message(chat_id=uid, text=f"📋 Copyable delivery (secure, save now — deletes in 5 min):\n{delivered}")
        sent_msgs.append((m.chat_id, m.message_id))
    except Exception:
        pass
    # auto-delete job — very secure
    async def _delete_later(ctx):
        for cid, mid in sent_msgs:
            try:
                await ctx.bot.delete_message(chat_id=cid, message_id=mid)
            except Exception:
                pass
    try:
        context.job_queue.run_once(lambda ctx: _delete_later(ctx), 300, name=f"del_{uid}_{aid}")
    except Exception:
        pass
