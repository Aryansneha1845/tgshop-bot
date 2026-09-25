from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards
import datetime

PER_PAGE = 10

def fmt_time(ts):
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%d/%m %H:%M")
    except:
        return ""

async def orders_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # data: orders:history:0  or orders:history:1
    parts = query.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 0
    uid = query.from_user.id
    total = db.total_orders(uid)
    if total == 0:
        await query.edit_message_text(
            "📦 <b>Order History</b>\n\nNo orders yet.\nTap 🛒 Purchase Tg Account to buy your first account!",
            parse_mode="HTML",
            reply_markup=keyboards.main_menu_kb()
        )
        return
    rows = db.get_orders(uid, limit=PER_PAGE, offset=page*PER_PAGE)
    total_pages = (total + PER_PAGE - 1)//PER_PAGE
    text = f"📦 <b>Order History — Last 10</b>\nPage {page+1}/{total_pages} (Total: {total})\n\n"
    for oid, aid, paid, orig, region, acctype, phone, ts in rows:
        flag = db.flag_for(region)
        saved = orig - paid
        saved_str = f" (-₹{saved})" if saved > 0 else ""
        text += (
            f"#{oid} {flag} <b>{region}</b> {acctype.title()} — "
            f"₹{paid}{saved_str} <i>(orig ₹{orig})</i>\n"
            f"   📞 <code>{phone}</code> • {fmt_time(ts)}\n"
        )
    has_next = (page+1)*PER_PAGE < total
    has_prev = page > 0
    kb = keyboards.orders_kb(page, total, has_next, has_prev)
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
