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

if not products:
    products = {
        "1": {"name": "🎮 Бравл Пасс+", "price": 350, "emoji": "🎮", "description": "Расширенный Бравл Пасс с бонусами"},
        "2": {"name": "⚡ Бравл Пасс", "price": 250, "emoji": "⚡", "description": "Стандартный Бравл Пасс"},
        "3": {"name": "👑 Про Пасс", "price": 750, "emoji": "👑", "description": "Максимальный Про Пасс"}
    }
    save_products(products)

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

# ========== СТАРТ ==========
async def start(update, context):
    user = update.effective_user
    text = f"👋 Привет, {user.first_name}!\n\n✅ **VPN Gertog**\n\n👇 Нажми кнопку:"
    keyboard = [[InlineKeyboardButton("🛍️ Меню товаров", callback_data="show_products")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ========== МЕНЮ ТОВАРОВ ==========
async def show_products(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for pid, pdata in products.items():
        keyboard.append([InlineKeyboardButton(f"{pdata['emoji']} {pdata['name']}", callback_data=f"product_{pid}")])
    
    keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "🛍️ **Наши товары:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== ОПИСАНИЕ ТОВАРА ==========
async def show_product(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    
    if product_id not in products:
        await query.answer("❌ Товар не найден")
        return
    
    product = products[product_id]
    text = f"{product['emoji']} **{product['name']}**\n\n📝 {product['description']}\n\n💰 Цена: **{product['price']} звёзд**"
    keyboard = [
        [InlineKeyboardButton(f"💸 Оплатить {product['price']} звёзд", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_products")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ========== ОПЛАТА ==========
async def buy_product(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[1]
    product = products[product_id]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.from_user.id,
            title=product["name"],
            description=product["description"],
            payload=f"product_{product_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=product["name"], amount=product["price"])],
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
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🟢 ПОКУПКА!\n👤 @{user.username or user.first_name}\n💰 {payment.total_amount}⭐"
    )
    
    link = await create_one_time_link(context)
    if link:
        await update.message.reply_text(f"✅ Оплачено! Ссылка:\n{link}")
    else:
        await update.message.reply_text("❌ Ошибка, напишите @mefytron")

# ========== АДМИН-ПАНЕЛЬ ==========
async def admin_panel(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Список товаров", callback_data="admin_list")],
        [InlineKeyboardButton("➕ Создать товар", callback_data="admin_create")],
        [InlineKeyboardButton("✏️ Редактировать товар", callback_data="admin_edit_menu")],
        [InlineKeyboardButton("🗑️ Удалить товар", callback_data="admin_delete_menu")],
        [InlineKeyboardButton("🔑 Выдать доступ", callback_data="admin_setup")],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_products")]
    ]
    await query.edit_message_text(
        "🔧 **Админ-панель**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_list(update, context):
    query = update.callback_query
    await query.answer()
    
    text = "📋 **Товары:**\n\n"
    for pid, pdata in products.items():
        text += f"🆔 `{pid}` | {pdata['name']} | {pdata['price']}⭐\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ========== СОЗДАНИЕ ТОВАРА ==========
async def admin_create_start(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "create_price"
    await query.edit_message_text(
        "💰 Введите цену товара (только число):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
    )

# ========== РЕДАКТИРОВАНИЕ ТОВАРА ==========
async def admin_edit_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for pid, pdata in products.items():
        keyboard.append([InlineKeyboardButton(f"{pdata['emoji']} {pdata['name']}", callback_data=f"edit_select_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "✏️ Выберите товар для редактирования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_select(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[2]
    context.user_data["edit_product_id"] = product_id
    
    keyboard = [
        [InlineKeyboardButton("💰 Изменить цену", callback_data="edit_price")],
        [InlineKeyboardButton("📝 Изменить название", callback_data="edit_name")],
        [InlineKeyboardButton("😀 Изменить эмодзи", callback_data="edit_emoji")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_menu")]
    ]
    await query.edit_message_text(
        f"✏️ Редактирование: {products[product_id]['name']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_price_start(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_price"
    await query.edit_message_text("💰 Введите новую цену:")

async def edit_name_start(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_name"
    await query.edit_message_text("📝 Введите новое название:")

async def edit_emoji_start(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_emoji"
    await query.edit_message_text("😀 Введите новый эмодзи (например, 🚀):")

# ========== УДАЛЕНИЕ ТОВАРА ==========
async def admin_delete_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for pid, pdata in products.items():
        keyboard.append([InlineKeyboardButton(f"❌ {pdata['emoji']} {pdata['name']}", callback_data=f"delete_confirm_{pid}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "🗑️ Выберите товар для удаления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_confirm(update, context):
    query = update.callback_query
    product_id = query.data.split("_")[2]
    name = products[product_id]["name"]
    del products[product_id]
    save_products(products)
    await query.answer(f"✅ Товар «{name}» удалён")
    await admin_delete_menu(update, context)

# ========== ВЫДАТЬ ДОСТУП ==========
async def admin_setup_start(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "setup"
    await query.edit_message_text(
        "🔑 Введите ID пользователя или @username:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
    )

# ========== ОБРАБОТЧИК ТЕКСТА ==========
async def handle_text(update, context):
    if not await is_admin(update.effective_user.id):
        return
    
    action = context.user_data.get("admin_action")
    
    if action == "create_price":
        try:
            price = int(update.message.text.strip())
            context.user_data["temp_price"] = price
            context.user_data["admin_action"] = "create_name"
            await update.message.reply_text("📝 Введите название товара (можно с эмодзи):")
        except:
            await update.message.reply_text("❌ Ошибка! Введите число:")
    
    elif action == "create_name":
        name = update.message.text.strip()
        price = context.user_data.get("temp_price")
        import time
        product_id = str(int(time.time()))
        products[product_id] = {
            "name": name,
            "price": price,
            "emoji": "🔒",
            "description": "Доступ к VPN"
        }
        save_products(products)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Товар создан! ID: `{product_id}`", parse_mode="Markdown")
        await admin_panel(update, context)
    
    elif action == "edit_price":
        try:
            new_price = int(update.message.text.strip())
            product_id = context.user_data.get("edit_product_id")
            products[product_id]["price"] = new_price
            save_products(products)
            context.user_data.clear()
            await update.message.reply_text(f"✅ Цена изменена на {new_price}⭐")
            await admin_panel(update, context)
        except:
            await update.message.reply_text("❌ Ошибка! Введите число:")
    
    elif action == "edit_name":
        new_name = update.message.text.strip()
        product_id = context.user_data.get("edit_product_id")
        products[product_id]["name"] = new_name
        save_products(products)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Название изменено на «{new_name}»")
        await admin_panel(update, context)
    
    elif action == "edit_emoji":
        new_emoji = update.message.text.strip()
        product_id = context.user_data.get("edit_product_id")
        products[product_id]["emoji"] = new_emoji
        save_products(products)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Эмодзи изменён на {new_emoji}")
        await admin_panel(update, context)
    
    elif action == "setup":
        identifier = update.message.text.strip()
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
                await update.message.reply_text(f"✅ Ссылка отправлена {identifier}")
            else:
                await update.message.reply_text("❌ Бот не админ канала")
        except Exception as e:
            await update.message.reply_text(f"❌ Пользователь не найден: {e}")
        context.user_data.clear()
        await admin_panel(update, context)

# ========== ЗАПУСК ==========
def main():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    
    # Кнопки
    app.add_handler(CallbackQueryHandler(show_products, pattern="^show_products$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    
    # Админ-панель
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_list, pattern="^admin_list$"))
    app.add_handler(CallbackQueryHandler(admin_create_start, pattern="^admin_create$"))
    app.add_handler(CallbackQueryHandler(admin_edit_menu, pattern="^admin_edit_menu$"))
    app.add_handler(CallbackQueryHandler(admin_delete_menu, pattern="^admin_delete_menu$"))
    app.add_handler(CallbackQueryHandler(admin_setup_start, pattern="^admin_setup$"))
    app.add_handler(CallbackQueryHandler(edit_select, pattern="^edit_select_"))
    app.add_handler(CallbackQueryHandler(edit_price_start, pattern="^edit_price$"))
    app.add_handler(CallbackQueryHandler(edit_name_start, pattern="^edit_name$"))
    app.add_handler(CallbackQueryHandler(edit_emoji_start, pattern="^edit_emoji$"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern="^delete_confirm_"))
    
    # Платежи
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
