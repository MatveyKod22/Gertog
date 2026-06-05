import os
import logging
import json
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

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

PRODUCTS_FILE = "products.json"

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

products = load_products()

# Товары по умолчанию
default_products = {
    "1": {"name": "🎮 Бравл Пасс+", "price": 350, "emoji": "🎮", "description": "Расширенный Бравл Пасс с бонусами"},
    "2": {"name": "⚡ Бравл Пасс", "price": 250, "emoji": "⚡", "description": "Стандартный Бравл Пасс"},
    "3": {"name": "👑 Про Пасс", "price": 750, "emoji": "👑", "description": "Максимальный Про Пасс"}
}

if not products:
    products = default_products
    save_products(products)
    print("✅ Созданы товары по умолчанию")

logging.basicConfig(level=logging.INFO)

# ========== ФУНКЦИИ БОТА ==========
async def create_one_time_link(context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            expire_date=None
        )
        return invite_link.invite_link
    except Exception as e:
        logging.error(f"Ошибка создания ссылки: {e}")
        return None

async def is_admin(user_id) -> bool:
    return user_id == ADMIN_CHAT_ID

# ========== КОМАНДА /START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "✅ **VPN Gertog**\n"
        "Защищённый и быстрый VPN-доступ\n\n"
        "👇 Нажмите кнопку ниже, чтобы посмотреть товары"
    )
    
    keyboard = [[InlineKeyboardButton("🛍️ Меню товаров", callback_data="show_products")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ========== ПОКАЗАТЬ ВСЕ ТОВАРЫ ==========
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not products:
        await query.edit_message_text("📭 **Товаров пока нет.**", parse_mode="Markdown")
        return
    
    keyboard = []
    for pid, pdata in products.items():
        emoji = pdata.get("emoji", "📦")
        keyboard.append([InlineKeyboardButton(f"{emoji} {pdata['name']}", callback_data=f"product_{pid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
    
    await query.edit_message_text(
        "🛍️ **Наши товары:**\n\nВыберите интересующий вас вариант:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== ПОКАЗАТЬ КОНКРЕТНЫЙ ТОВАР ==========
async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    
    if product_id not in products:
        await query.answer("❌ Товар не найден")
        return
    
    product = products[product_id]
    emoji = product.get("emoji", "📦")
    name = product['name']
    price = product['price']
    description = product.get("description", "Доступ к приватному каналу с VPN настройками.")
    
    text = (
        f"{emoji} **{name}**\n\n"
        f"📝 {description}\n\n"
        f"💰 Цена: **{price} звёзд**\n\n"
        f"⭐ Оплата через Telegram Stars\n"
        f"Нажмите «Оплатить» и подтвердите перевод."
    )
    
    keyboard = [
        [InlineKeyboardButton(f"💸 Оплатить {price} звёзд", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🔙 Назад к товарам", callback_data="show_products")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== КНОПКА НАЗАД ==========
async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "✅ **VPN Gertog**\n"
        "Защищённый и быстрый VPN-доступ\n\n"
        "👇 Нажмите кнопку ниже, чтобы посмотреть товары"
    )
    
    keyboard = [[InlineKeyboardButton("🛍️ Меню товаров", callback_data="show_products")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ========== ОПЛАТА ==========
async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    
    if product_id not in products:
        await query.answer("❌ Товар не найден")
        return
    
    product = products[product_id]
    price = product["price"]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.from_user.id,
            title=product["name"],
            description=product.get("description", "Доступ к приватному каналу с VPN настройками."),
            payload=f"product_{product_id}_{query.from_user.id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=product["name"], amount=price)],
            start_parameter=f"buy_{product_id}"
        )
        await query.answer()
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    
    # Уведомление админу
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🟢 **НОВАЯ ПОКУПКА!**\n\n"
             f"👤 Пользователь: @{user.username or user.first_name}\n"
             f"🆔 ID: `{user.id}`\n"
             f"💰 Сумма: {payment.total_amount} звёзд\n"
             f"📦 Товар: {payment.invoice_payload}",
        parse_mode="Markdown"
    )
    
    if payload.startswith("product_"):
        parts = payload.split("_")
        if len(parts) >= 2:
            product_id = parts[1]
            
            link = await create_one_time_link(context)
            if link:
                await update.message.reply_text(
                    f"✅ **Оплата подтверждена!**\n\n"
                    f"🔗 Твоя персональная ссылка:\n{link}\n\n"
                    f"⬆️ Нажми и присоединяйся.\n\n"
                    f"Спасибо за покупку! 🎉",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Ошибка создания ссылки. Напишите @mefytron.")
    
    await update.message.reply_text("✅ Спасибо за покупку!")

# ========== АДМИН-МЕНЮ ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Список товаров", callback_data="admin_list")],
        [InlineKeyboardButton("➕ Создать товар", callback_data="admin_create")],
        [InlineKeyboardButton("✏️ Редактировать товар", callback_data="admin_edit")],
        [InlineKeyboardButton("🗑️ Удалить товар", callback_data="admin_delete")],
        [InlineKeyboardButton("🔑 Выдать доступ", callback_data="admin_setup")]
    ]
    
    await update.message.reply_text(
        "🔧 **Админ-панель**\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not products:
        await query.edit_message_text("📭 Товаров нет.")
        return
    
    text = "📋 **Все товары:**\n\n"
    for pid, pdata in products.items():
        text += f"🆔 `{pid}`\n"
        text += f"   {pdata.get('emoji', '💰')} *{pdata['name']}*\n"
        text += f"   💰 Цена: {pdata['price']}⭐\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["admin_action"] = "create"
    await query.edit_message_text(
        "💰 Введите цену товара (только число):\n\nПример: `350`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]]),
        parse_mode="Markdown"
    )

async def admin_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not products:
        await query.edit_message_text("📭 Товаров нет для редактирования.")
        return
    
    keyboard = []
    for pid, pdata in products.items():
        keyboard.append([InlineKeyboardButton(f"{pdata['emoji']} {pdata['name']}", callback_data=f"edit_select_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    
    await query.edit_message_text(
        "✏️ Выберите товар для редактирования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.split("_")[2]
    context.user_data["edit_product_id"] = product_id
    
    keyboard = [
        [InlineKeyboardButton("💰 Изменить цену", callback_data="edit_price")],
        [InlineKeyboardButton("📝 Изменить название", callback_data="edit_name")],
        [InlineKeyboardButton("😀 Изменить эмодзи", callback_data="edit_emoji")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit")]
    ]
    await query.edit_message_text(
        f"✏️ Редактирование: {products[product_id]['name']}\n\nЧто хотите изменить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not products:
        await query.edit_message_text("📭 Товаров нет для удаления.")
        return
    
    keyboard = []
    for pid, pdata in products.items():
        keyboard.append([InlineKeyboardButton(f"❌ {pdata['emoji']} {pdata['name']}", callback_data=f"delete_confirm_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    
    await query.edit_message_text(
        "🗑️ Выберите товар для удаления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.split("_")[2]
    name = products[product_id]["name"]
    del products[product_id]
    save_products(products)
    await query.answer(f"✅ Товар «{name}» удалён")
    await admin_delete_start(update, context)

async def admin_setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["admin_action"] = "setup"
    await query.edit_message_text(
        "🔑 Введите ID пользователя или @username:\n\nПример: `6068810451` или `@username`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])
    )

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await admin_panel(update, context)

# ========== ОБРАБОТЧИК ТЕКСТА ДЛЯ АДМИНА ==========
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    
    action = context.user_data.get("admin_action")
    
    if action == "create":
        try:
            price = int(update.message.text.strip())
            context.user_data["temp_price"] = price
            context.user_data["admin_action"] = "create_name"
            await update.message.reply_text("📝 Введите название товара (можно с эмодзи):\n\nПример: `🔥 Бравл Пасс`", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ Ошибка! Цена должна быть числом. Попробуйте снова:")
    
    elif action == "create_name":
        name = update.message.text.strip()
        price = context.user_data.get("temp_price")
        import time
        product_id = str(int(time.time()))
        
        products[product_id] = {
            "name": name,
            "price": price,
            "emoji": "🔒",
            "description": "Доступ к приватному каналу с VPN настройками."
        }
        save_products(products)
        context.user_data.clear()
        await update.message.reply_text(f"✅ **Товар создан!**\n\n🆔 ID: `{product_id}`\n💰 Цена: {price}⭐\n📦 Название: {name}", parse_mode="Markdown")
        await admin_panel(update, context)
    
    elif action == "setup":
        identifier = update.message.text.strip()
        username = identifier
        if username.startswith('@'):
            username = username[1:]
        
        await update.message.reply_text(f"🔍 Ищу пользователя {identifier}...")
        
        try:
            if identifier.isdigit():
                user_id = int(identifier)
                user = await context.bot.get_chat(user_id)
            else:
                user = await context.bot.get_chat(f"@{username}")
                user_id = user.id
            
            link = await create_one_time_link(context)
            if link:
                await context.bot.send_message(user_id, f"✅ Доступ активирован!\n\n🔗 Ваша ссылка:\n{link}")
                await update.message.reply_text(f"✅ Ссылка отправлена пользователю {identifier}")
            else:
                await update.message.reply_text("❌ Ошибка: бот не админ канала")
        except Exception as e:
            await update.message.reply_text(f"❌ Пользователь {identifier} не найден. Ошибка: {e}")
        
        context.user_data.clear()
        await admin_panel(update, context)

# ========== ЗАПУСК ==========
def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Пользовательские команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^show_products$"))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    
    # Админ-команды и колбэки
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_list, pattern="^admin_list$"))
    app.add_handler(CallbackQueryHandler(admin_create_start, pattern="^admin_create$"))
    app.add_handler(CallbackQueryHandler(admin_edit_start, pattern="^admin_edit$"))
    app.add_handler(CallbackQueryHandler(admin_delete_start, pattern="^admin_delete$"))
    app.add_handler(CallbackQueryHandler(admin_setup_start, pattern="^admin_setup$"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"))
    app.add_handler(CallbackQueryHandler(edit_select, pattern="^edit_select_"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern="^delete_confirm_"))
    
    # Обработчики платежей
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Обработчик текста для админа
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    print("🤖 Бот запущен! Товаров загружено:", len(products))
    app.run_polling()

if __name__ == "__main__":
    main()