import os
import logging
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = -1003934387840
ADMIN_CHAT_ID = 6068810451

# Файл для хранения товаров
PRODUCTS_FILE = "products.json"

# Загрузка товаров
def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

products = load_products()

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
    
    # Если есть картинка
    if product.get("photo_file_id"):
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=product["photo_file_id"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
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

# ========== КОМАНДЫ ДЛЯ АДМИНА ==========
async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not products:
        await update.message.reply_text("📭 Товаров нет.")
        return
    
    text = "📋 **Все товары:**\n\n"
    for pid, pdata in products.items():
        text += f"🆔 `{pid}`\n"
        text += f"   {pdata.get('emoji', '💰')} *{pdata['name']}*\n"
        text += f"   💰 Цена: {pdata['price']}⭐\n"
        if pdata.get("has_image"):
            text += f"   🖼️ Есть картинка\n"
        text += "\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def create_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: `/tovar create 250 Название товара`", parse_mode="Markdown")
        return
    
    try:
        price = int(context.args[0])
        name = " ".join(context.args[1:])
        
        import time
        product_id = str(int(time.time()))
        
        products[product_id] = {
            "name": name,
            "price": price,
            "emoji": "🔒",
            "has_image": False,
            "description": "Доступ к приватному каналу с VPN настройками."
        }
        save_products(products)
        
        await update.message.reply_text(
            f"✅ **Товар создан!**\n\n"
            f"🆔 ID: `{product_id}`\n"
            f"💰 Цена: {price}⭐\n"
            f"📦 Название: {name}\n\n"
            f"➕ Добавить картинку: `/tovar image {product_id}`\n"
            f"✏️ Редактировать: `/tovar edit {product_id}`",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("❌ Ошибка. Цена должна быть числом.")

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: `/tovar delete ID_или_название`")
        return
    
    identifier = context.args[0]
    
    found_id = None
    for pid, pdata in products.items():
        if pid == identifier or pdata["name"].lower() == identifier.lower():
            found_id = pid
            break
    
    if not found_id:
        await update.message.reply_text("❌ Товар не найден")
        return
    
    name = products[found_id]["name"]
    del products[found_id]
    save_products(products)
    await update.message.reply_text(f"✅ Товар «{name}» удалён")

async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: `/tovar edit ID_или_название`")
        return
    
    identifier = context.args[0]
    
    found_id = None
    for pid, pdata in products.items():
        if pid == identifier or pdata["name"].lower() == identifier.lower():
            found_id = pid
            break
    
    if not found_id:
        await update.message.reply_text("❌ Товар не найден")
        return
    
    context.user_data["editing_product"] = found_id
    
    keyboard = [
        [InlineKeyboardButton("💰 Изменить цену", callback_data="edit_price")],
        [InlineKeyboardButton("📝 Изменить название", callback_data="edit_name")],
        [InlineKeyboardButton("😀 Изменить эмодзи", callback_data="edit_emoji")],
        [InlineKeyboardButton("📝 Изменить описание", callback_data="edit_desc")],
        [InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")]
    ]
    await update.message.reply_text(
        f"✏️ **Редактирование товара**\n\n"
        f"Товар: {products[found_id]['name']}\n\n"
        f"Что хотите изменить?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def add_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: `/tovar image ID_или_название`")
        return
    
    identifier = context.args[0]
    
    found_id = None
    for pid, pdata in products.items():
        if pid == identifier or pdata["name"].lower() == identifier.lower():
            found_id = pid
            break
    
    if not found_id:
        await update.message.reply_text("❌ Товар не найден")
        return
    
    context.user_data["pending_image"] = found_id
    await update.message.reply_text(f"🖼️ Отправьте фото для товара «{products[found_id]['name']}»")

async def setup_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав. Только @mefytron")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: `/setup @username`\n\nПример: `/setup @gavnaed`")
        return
    
    username = context.args[0].strip()
    if username.startswith('@'):
        username = username[1:]
    
    await update.message.reply_text(f"🔍 Ищу пользователя @{username}...")
    
    try:
        user_chat = await context.bot.get_chat(f"@{username}")
        user_id = user_chat.id
        
        link = await create_one_time_link(context)
        
        if not link:
            await update.message.reply_text("❌ Ошибка: бот не админ канала")
            return
        
        try:
            await context.bot.send_message(
                user_id,
                f"✅ Доступ активирован, @{username}!\n\n🔗 Ваша ссылка:\n{link}"
            )
            await update.message.reply_text(f"✅ Ссылка отправлена @{username}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}\n\nСсылка: {link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Пользователь @{username} не найден")

# ========== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ==========
async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if "editing_product" not in context.user_data:
        await query.edit_message_text("❌ Сессия редактирования истекла")
        return
    
    product_id = context.user_data["editing_product"]
    action = query.data
    
    if action == "edit_cancel":
        del context.user_data["editing_product"]
        await query.edit_message_text("❌ Редактирование отменено")
        return
    
    elif action == "edit_price":
        context.user_data["edit_field"] = "price"
        await query.edit_message_text("💰 Введите новую цену (число):")
    
    elif action == "edit_name":
        context.user_data["edit_field"] = "name"
        await query.edit_message_text("📝 Введите новое название товара:")
    
    elif action == "edit_emoji":
        context.user_data["edit_field"] = "emoji"
        await query.edit_message_text("😀 Введите новый эмодзи для товара (например, 🚀, 💎, 🔥):")
    
    elif action == "edit_desc":
        context.user_data["edit_field"] = "description"
        await query.edit_message_text("📝 Введите новое описание товара:")

async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    
    if "editing_product" not in context.user_data or "edit_field" not in context.user_data:
        return
    
    product_id = context.user_data["editing_product"]
    field = context.user_data["edit_field"]
    text = update.message.text
    
    if field == "price":
        try:
            new_price = int(text)
            old_price = products[product_id]["price"]
            products[product_id]["price"] = new_price
            save_products(products)
            await update.message.reply_text(f"✅ Цена изменена с {old_price}⭐ на {new_price}⭐")
        except:
            await update.message.reply_text("❌ Ошибка. Цена должна быть числом.")
    
    elif field == "name":
        old_name = products[product_id]["name"]
        products[product_id]["name"] = text
        save_products(products)
        await update.message.reply_text(f"✅ Название изменено с «{old_name}» на «{text}»")
    
    elif field == "emoji":
        products[product_id]["emoji"] = text
        save_products(products)
        await update.message.reply_text(f"✅ Эмодзи изменён на {text}")
    
    elif field == "description":
        products[product_id]["description"] = text
        save_products(products)
        await update.message.reply_text(f"✅ Описание изменено")
    
    del context.user_data["edit_field"]
    del context.user_data["editing_product"]

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    
    if "pending_image" not in context.user_data:
        return
    
    product_id = context.user_data["pending_image"]
    photo = update.message.photo[-1]
    
    products[product_id]["photo_file_id"] = photo.file_id
    products[product_id]["has_image"] = True
    save_products(products)
    
    del context.user_data["pending_image"]
    await update.message.reply_text(f"✅ Картинка добавлена товару «{products[product_id]['name']}»")

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Пользовательские команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^show_products$"))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    
    # Админ-команды
    app.add_handler(CommandHandler("spisok", admin_list))
    app.add_handler(CommandHandler("setup", setup_access))
    app.add_handler(CommandHandler("tovar", create_product))
    app.add_handler(CommandHandler("tovar", delete_product))
    app.add_handler(CommandHandler("tovar", edit_product))
    app.add_handler(CommandHandler("tovar", add_image))
    
    # Обработчики
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CallbackQueryHandler(edit_callback, pattern="^edit_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input))
    
    print("🤖 Бот запущен! Товаров загружено:", len(products))
    app.run_polling()

if __name__ == "__main__":
    main()