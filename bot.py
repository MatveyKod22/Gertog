import os
import logging
import json
import asyncio
import re
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "VPN Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = -1003934387840
ADMIN_CHAT_ID = 6068810451
MANAGER_USERNAME = "mefytron"

PRODUCTS_FILE = "products.json"
user_history = {}

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

products = load_products()

# Товары по умолчанию (БЕЗ эмодзи вообще)
if not products:
    products = {
        "1": {"name": "VPN для игр с ботами", "price": 300, "display_name": "VPN для игр с ботами", "description": "Оптимизированный VPN для игр с ботами.", "auto": True},
        "2": {"name": "Бравл Пасс+", "price": 350, "display_name": "Бравл Пасс+", "description": "Расширенный Бравл Пасс с бонусами", "auto": False},
        "3": {"name": "Бравл Пасс", "price": 250, "display_name": "Бравл Пасс", "description": "Стандартный Бравл Пасс", "auto": False},
        "4": {"name": "Про Пасс", "price": 750, "display_name": "Про Пасс", "description": "Максимальный Про Пасс", "auto": False}
    }
    save_products(products)
    print("✅ Созданы товары по умолчанию (без эмодзи)")

logging.basicConfig(level=logging.INFO)

# ========== ФУНКЦИИ ==========
async def create_one_time_link(context):
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            expire_date=None
        )
        return invite_link.invite_link
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None

async def is_admin(user_id):
    return user_id == ADMIN_CHAT_ID

def save_history(user_id, message_data):
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append(message_data)
    if len(user_history[user_id]) > 10:
        user_history[user_id].pop(0)

def get_previous(user_id):
    if user_id in user_history and len(user_history[user_id]) > 1:
        user_history[user_id].pop()
        return user_history[user_id][-1]
    return None

# Функция для извлечения премиум-эмодзи из сообщения
def extract_premium_emoji(message):
    """Извлекает custom_emoji_id и форматирует текст с тегом"""
    if not message.entities:
        return message.text, None
    
    text = message.text
    result_text = ""
    last_offset = 0
    
    for entity in message.entities:
        if entity.type == "custom_emoji":
            if entity.offset > last_offset:
                result_text += text[last_offset:entity.offset]
            emoji_char = text[entity.offset:entity.offset + entity.length]
            result_text += f'<tg-emoji emoji-id="{entity.custom_emoji_id}">{emoji_char}</tg-emoji>'
            last_offset = entity.offset + entity.length
        elif entity.type == "bold":
            if entity.offset > last_offset:
                result_text += text[last_offset:entity.offset]
            result_text += f"<b>{text[entity.offset:entity.offset + entity.length]}</b>"
            last_offset = entity.offset + entity.length
        elif entity.type == "italic":
            if entity.offset > last_offset:
                result_text += text[last_offset:entity.offset]
            result_text += f"<i>{text[entity.offset:entity.offset + entity.length]}</i>"
            last_offset = entity.offset + entity.length
    
    if last_offset < len(text):
        result_text += text[last_offset:]
    
    return result_text, True

# Функция для очистки HTML-тегов
def clean_html(text):
    clean = re.sub(r'<tg-emoji[^>]*>([^<]+)</tg-emoji>', r'\1', text)
    clean = re.sub(r'<[^>]+>', '', clean)
    return clean

# ========== СТАРТ ==========
async def start(update, context):
    user = update.effective_user
    text = f"👋 Привет, {user.first_name}!\n\n✅ <b>VPN Gertog</b>\n\n👇 Нажми кнопку:"
    keyboard = [[InlineKeyboardButton("🛍️ Меню товаров", callback_data="show_products")]]
    
    if await is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🔧 Админ-панель", callback_data="admin_panel")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# ========== МЕНЮ ТОВАРОВ ==========
async def show_products(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for pid, pdata in products.items():
        display_name = pdata.get('display_name', pdata['name'])
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"product_{pid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
    
    await query.edit_message_text(
        "🛍️ <b>Наши товары:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ========== ОПИСАНИЕ ТОВАРА ==========
async def show_product(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    
    if product_id not in products:
        await query.answer("❌ Товар не найден")
        return
    
    product = products[product_id]
    display_name = product.get('display_name', product['name'])
    
    text = f"{display_name}\n\n📝 {product['description']}\n\n💰 Цена: <b>{product['price']} звёзд</b>"
    keyboard = [
        [InlineKeyboardButton(f"💸 Оплатить {product['price']} звёзд", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_products")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def back_to_start(update, context):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# ========== ОПЛАТА ==========
async def buy_product(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    product = products[product_id]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.from_user.id,
            title=clean_html(product.get('display_name', product['name'])),
            description=product["description"],
            payload=f"product_{product_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=clean_html(product.get('display_name', product['name'])), amount=product["price"])],
            start_parameter=f"buy_{product_id}"
        )
        await query.answer()
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")

async def pre_checkout(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update, context):
    user = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    product_id = payload.split("_")[1]
    product = products.get(product_id, {})
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🟢 ПОКУПКА!\n👤 @{user.username or user.first_name}\n💰 {payment.total_amount}⭐\n📦 {product.get('name', 'Неизвестно')}"
    )
    
    if product.get("auto", True):
        link = await create_one_time_link(context)
        if link:
            await update.message.reply_text(f"✅ Оплата подтверждена!\n\n🔗 Ваша ссылка:\n{link}")
        else:
            await update.message.reply_text(f"❌ Ошибка. Свяжитесь с @{MANAGER_USERNAME}")
    else:
        await update.message.reply_text(
            f"✅ Оплата успешно оформлена!\n\n"
            f"🎮 Для активации «{product.get('name', 'доступа')}» "
            f"перейдите к менеджеру: @{MANAGER_USERNAME}"
        )

# ========== АДМИН-ПАНЕЛЬ ==========
async def admin_panel(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📋 Список товаров", callback_data="admin_list")],
        [InlineKeyboardButton("➕ Создать товар", callback_data="admin_create")],
        [InlineKeyboardButton("✏️ Редактировать товар", callback_data="admin_edit_menu")],
        [InlineKeyboardButton("🗑️ Удалить товар", callback_data="admin_delete_menu")],
        [InlineKeyboardButton("🔑 Выдать доступ", callback_data="admin_setup")],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_products")]
    ]
    await query.edit_message_text("🔧 <b>Админ-панель</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def admin_list(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    text = "📋 <b>Товары:</b>\n\n"
    for pid, pdata in products.items():
        auto_text = "✅ авто" if pdata.get("auto", True) else "👤 ручная"
        clean_name = clean_html(pdata.get('display_name', pdata['name']))
        text += f"🆔 <code>{pid}</code> | {clean_name} | {pdata['price']}⭐ | {auto_text}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def admin_create_start(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    context.user_data["admin_action"] = "create_price"
    await query.edit_message_text(
        "💰 Введите цену товара:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
    )

async def admin_edit_menu(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    keyboard = []
    for pid, pdata in products.items():
        clean_name = clean_html(pdata.get('display_name', pdata['name']))
        keyboard.append([InlineKeyboardButton(clean_name, callback_data=f"edit_select_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text("✏️ Выберите товар:", reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_select(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    product_id = query.data.split("_")[2]
    context.user_data["edit_product_id"] = product_id
    product = products[product_id]
    
    keyboard = [
        [InlineKeyboardButton("💰 Изменить цену", callback_data="edit_price")],
        [InlineKeyboardButton("📝 Изменить название", callback_data="edit_name")],
        [InlineKeyboardButton("🔄 Изменить тип", callback_data="edit_activation")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_menu")]
    ]
    await query.edit_message_text(
        f"✏️ Редактирование: {product['name']}\nТип: {'авто' if product.get('auto', True) else 'ручная'}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_price_start(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    context.user_data["admin_action"] = "edit_price"
    await query.edit_message_text("💰 Введите новую цену:")

async def edit_name_start(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    context.user_data["admin_action"] = "edit_name"
    await query.edit_message_text("📝 Отправьте новое название (можно с премиум-эмодзи):")

async def edit_activation_start(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    product_id = context.user_data.get("edit_product_id")
    current = products[product_id].get("auto", True)
    
    keyboard = [
        [InlineKeyboardButton("✅ Автоматическая", callback_data="edit_activation_auto")],
        [InlineKeyboardButton("👤 Ручная", callback_data="edit_activation_manual")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_menu")]
    ]
    await query.edit_message_text(
        f"Тип активации: {'авто' if current else 'ручная'}\nВыберите новый:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_activation_confirm(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    activation_type = query.data.split("_")[2]
    product_id = context.user_data.get("edit_product_id")
    products[product_id]["auto"] = (activation_type == "auto")
    save_products(products)
    await query.answer("✅ Тип изменён!")
    await admin_edit_menu(update, context)

async def admin_delete_menu(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    keyboard = []
    for pid, pdata in products.items():
        clean_name = clean_html(pdata.get('display_name', pdata['name']))
        keyboard.append([InlineKeyboardButton(f"❌ {clean_name}", callback_data=f"delete_confirm_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text("🗑️ Выберите товар для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_confirm(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    product_id = query.data.split("_")[2]
    name = products[product_id]["name"]
    del products[product_id]
    save_products(products)
    await query.answer(f"✅ Товар «{name}» удалён")
    await admin_delete_menu(update, context)

async def admin_setup_start(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    context.user_data["admin_action"] = "setup"
    await query.edit_message_text("🔑 Введите ID или @username:")

# ========== ОБРАБОТЧИК ТЕКСТА ==========
async def handle_text(update, context):
    user_id = update.effective_user.id
    message = update.message
    
    if not await is_admin(user_id):
        return
    
    action = context.user_data.get("admin_action")
    
    if action == "create_price":
        try:
            price = int(message.text.strip())
            context.user_data["temp_price"] = price
            
            keyboard = [
                [InlineKeyboardButton("✅ Автоматическая", callback_data="create_type_auto")],
                [InlineKeyboardButton("👤 Ручная", callback_data="create_type_manual")],
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]
            ]
            await message.reply_text(
                "Выберите тип активации:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data["admin_action"] = "select_type"
        except:
            await message.reply_text("❌ Ошибка! Введите число:")
    
    elif action == "edit_price":
        try:
            new_price = int(message.text.strip())
            product_id = context.user_data.get("edit_product_id")
            products[product_id]["price"] = new_price
            save_products(products)
            context.user_data.clear()
            await message.reply_text(f"✅ Цена изменена на {new_price}⭐")
            await admin_panel(update, context)
        except:
            await message.reply_text("❌ Ошибка! Введите число:")
    
    elif action == "edit_name":
        display_name, has_emoji = extract_premium_emoji(message)
        clean_name = clean_html(display_name)
        
        product_id = context.user_data.get("edit_product_id")
        products[product_id]["display_name"] = display_name
        products[product_id]["name"] = clean_name
        save_products(products)
        context.user_data.clear()
        await message.reply_text(f"✅ Название изменено на: {display_name}", parse_mode=ParseMode.HTML)
        await admin_panel(update, context)
    
    elif action == "setup":
        identifier = message.text.strip()
        username = identifier.lstrip('@')
        try:
            if identifier.isdigit():
                user_id = int(identifier)
                user = await context.bot.get_chat(user_id)
            else:
                user = await context.bot.get_chat(f"@{username}")
                user_id = user.id
            
            link = await create_one_time_link(context)
            if link:
                await context.bot.send_message(user_id, f"✅ Доступ активирован!\n🔗 {link}")
                await message.reply_text(f"✅ Ссылка отправлена {identifier}")
            else:
                await message.reply_text("❌ Бот не админ канала")
        except Exception as e:
            await message.reply_text(f"❌ Ошибка: {e}")
        context.user_data.clear()
        await admin_panel(update, context)

async def create_activation_type(update, context):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа", show_alert=True)
        return
    
    activation_type = query.data.split("_")[2]
    context.user_data["temp_auto"] = (activation_type == "auto")
    context.user_data["admin_action"] = "create_name"
    
    await query.edit_message_text(
        "📝 Отправьте название товара (можно с премиум-эмодзи):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
    )

# ========== ЗАПУСК ==========
def main():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^show_products$"))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_list, pattern="^admin_list$"))
    app.add_handler(CallbackQueryHandler(admin_create_start, pattern="^admin_create$"))
    app.add_handler(CallbackQueryHandler(admin_edit_menu, pattern="^admin_edit_menu$"))
    app.add_handler(CallbackQueryHandler(admin_delete_menu, pattern="^admin_delete_menu$"))
    app.add_handler(CallbackQueryHandler(admin_setup_start, pattern="^admin_setup$"))
    app.add_handler(CallbackQueryHandler(edit_select, pattern="^edit_select_"))
    app.add_handler(CallbackQueryHandler(edit_price_start, pattern="^edit_price$"))
    app.add_handler(CallbackQueryHandler(edit_name_start, pattern="^edit_name$"))
    app.add_handler(CallbackQueryHandler(edit_activation_start, pattern="^edit_activation$"))
    app.add_handler(CallbackQueryHandler(edit_activation_confirm, pattern="^edit_activation_"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern="^delete_confirm_"))
    app.add_handler(CallbackQueryHandler(create_activation_type, pattern="^create_type_"))
    
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен! Товаров:", len(products))
    app.run_polling()

if __name__ == "__main__":
    main()
