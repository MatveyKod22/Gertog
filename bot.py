import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8221038281:AAH3huhO3zbg-56NBb-MyzfH5g_XPrA82js"  # замените на реальный токен

CHANNEL_ID = -1003934387840
ADMIN_CHAT_ID = 6068810451

user_links = {}
logging.basicConfig(level=logging.INFO)

async def create_one_time_link(context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            expire_date=None
        )
        return invite_link.invite_link
    except Exception as e:
        return f"❌ Ошибка: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "✅ Официальный бот VPN **Gertog**\n\n"
        "💰 **250 звёзд** (подарком, комиссия включена)\n"
        "👇 Нажми «Оплатить»"
    )
    keyboard = [[InlineKeyboardButton("💸 Оплатить 250 звёзд", callback_data="pay")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def pay_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "🪄 **Как оплатить:**\n\n"
        "1. Открой Telegram Stars\n"
        "2. Отправь **подарок** на 250 звёзд\n"
        "3. Получатель: `@mefytron`\n"
        "4. Нажми «✅ Я отправил»\n\n"
        "⭐ Комиссия уже в подарке!"
    )
    keyboard = [[InlineKeyboardButton("✅ Я отправил", callback_data="submitted")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def submitted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    await query.edit_message_text("📨 Заявка отправлена. Ждите подтверждения от @mefytron")
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🔔 Пользователь @{user.username or user.first_name} (ID: {user.id}) оплатил!\n\nВведи:\n/setup @{user.username or user.first_name}"
    )

async def setup_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
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
        if link.startswith("❌"):
            await update.message.reply_text(link)
            return
        user_links[user_id] = link
        try:
            await context.bot.send_message(
                user_id,
                f"✅ Оплата подтверждена, @{username}!\n\n🔗 Ваша персональная ссылка (только для вас, 1 вход):\n{link}\n\n⬆️ Нажмите и присоединяйтесь"
            )
            await update.message.reply_text(f"✅ Ссылка отправлена @{username}\n\n🔗 {link}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}\nОтправьте ссылку вручную:\n{link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Пользователь @{username} не найден")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup_access))
    app.add_handler(CallbackQueryHandler(pay_button, pattern="^pay$"))
    app.add_handler(CallbackQueryHandler(submitted, pattern="^submitted$"))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()