from telegram import Update
from telegram.ext import ContextTypes
import db
import keyboards

async def region_pick_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # data: region:IN:budget  or region:RANDOM:budget or region:SEARCH:budget
    _, region, acctype = query.data.split(":")
    if region == "SEARCH":
        # show search list: distinct regions with stock
        regions = db.get_regions_with_stock(acctype)
        if not regions:
            await query.edit_message_text("No stock available right now. Try again later.", reply_markup=keyboards.store_menu_kb())
            return
        text = (
            f"📱 <b>TG Accounts — {'Cheap' if acctype=='budget' else 'Premium'}</b>\n\n"
            f"🔍 <b>All Available Countries:</b>\nTap a country or send keyword (e.g. IN, USA) to search."
        )
        await query.edit_message_text(text, reply_markup=keyboards.search_regions_kb(acctype, regions, page=0), parse_mode="HTML")
        # set pending search flag
        context.user_data["pending_search_type"] = acctype
        return

    # normal region -> show listing page 0
    # auto topup if low
    db.auto_topup_if_low(acctype, region)
    from handlers.listing import show_listing
    await show_listing(query, acctype, region, page=0, edit=True)

async def search_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # search:budget:1
    _, acctype, page_s = query.data.split(":")
    page = int(page_s)
    regions = db.get_regions_with_stock(acctype)
    text = (
        f"📱 <b>TG Accounts — {'Cheap' if acctype=='budget' else 'Premium'}</b>\n\n"
        f"🔍 <b>All Available Countries:</b>\nTap a country or send keyword."
    )
    try:
        await query.edit_message_text(text, reply_markup=keyboards.search_regions_kb(acctype, regions, page=page), parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, reply_markup=keyboards.search_regions_kb(acctype, regions, page=page), parse_mode="HTML")

async def search_kw_prompt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, acctype = query.data.split(":")
    context.user_data["pending_search_type"] = acctype
    context.user_data["awaiting_keyword"] = True
    await query.message.reply_text(
        f"🔍 Send a country keyword for <b>{acctype}</b> accounts (e.g. <code>IN</code>, <code>USA</code>, <code>indo</code>).\n"
        f"Or tap a country from the list above.\n"
        f"Type /cancel to cancel.",
        parse_mode="HTML"
    )

async def keyword_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # if user is in search keyword mode, treat text as search
    if not context.user_data.get("awaiting_keyword"):
        return
    acctype = context.user_data.get("pending_search_type", "budget")
    keyword = update.message.text.strip().lower()
    if keyword.startswith("/"):
        return
    regions = db.get_regions_with_stock(acctype)
    # filter regions containing keyword
    filtered = [r for r in regions if keyword in r.lower() or keyword in r.lower()[:3] or keyword == r.lower()]
    # also handle aliases
    alias_map = {"in": "IN", "india": "IN", "us": "USA", "usa": "USA", "indonesia": "Indonesia", "myanmar": "Myanmar", "bangladesh": "Bangladesh", "vietnam": "Vietnam"}
    if keyword in alias_map:
        target = alias_map[keyword]
        if target in regions:
            filtered = [target]
    if not filtered:
        await update.message.reply_text(f"No countries found for '{keyword}'. Try another keyword or tap from the list.", reply_markup=keyboards.region_menu_kb(acctype))
        context.user_data.pop("awaiting_keyword", None)
        return
    if len(filtered) == 1:
        # directly show listing for that region
        region = filtered[0]
        db.auto_topup_if_low(acctype, region)
        from handlers.listing import show_listing_text
        text, kb = show_listing_text(acctype, region, page=0)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        context.user_data.pop("awaiting_keyword", None)
        context.user_data.pop("pending_search_type", None)
        return
    # multiple matches -> show as search list
    text = f"🔍 Results for '{keyword}' — tap to view:"
    await update.message.reply_text(text, reply_markup=keyboards.search_regions_kb(acctype, filtered, page=0))
    context.user_data.pop("awaiting_keyword", None)
