import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNEL_ID = -1003934387840

# Товар: 250 звёзд
PRICE = 250
STAR_PRICE = LabeledPrice(label="VPN Gertog - 1 месяц", amount=PRICE)

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
        logging.error(f"Ошибка создания ссылки: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "✅ Официальный бот VPN **Gertog**\n\n"
        "💰 Стоимость: **250 звёзд**\n"
        "👇 Нажми «Оплатить» и подтверди перевод в Telegram"
    )
    keyboard = [[InlineKeyboardButton("💸 Оплатить 250 звёзд", callback_data="pay")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def pay_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    try:
        # Отправляем инвойс на 250 звёзд
        await context.bot.send_invoice(
            chat_id=user.id,
            title="VPN Gertog",
            description="Доступ к приватному каналу с VPN настройками. 1 месяц.",
            payload="vpn_access_" + str(user.id),
            provider_token="",  # Для звёзд оставляем пустым
            currency="XTR",  # XTR = Telegram Stars
            prices=[STAR_PRICE],
            start_parameter="vpn_gertog",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            is_flexible=False
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}\n\nПопробуйте позже.")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Проверяем, что это наш товар
    if query.invoice_payload.startswith("vpn_access_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так.")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    
    # Проверяем сумму (должна быть 250)
    if payment.total_amount == PRICE:
        # Создаём ссылку
        link = await create_one_time_link(context)
        
        if link:
            await update.message.reply_text(
                f"✅ **Оплата подтверждена!**\n\n"
                f"🔗 Твоя персональная ссылка (только для тебя, 1 вход):\n"
                f"{link}\n\n"
                f"⬆️ Нажми и присоединяйся к каналу с VPN.\n\n"
                f"Спасибо за покупку! 🎉",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании ссылки. Пожалуйста, напишите @mefytron для решения проблемы."
            )
    else:
        await update.message.reply_text(f"❌ Неправильная сумма оплаты. Свяжитесь с @mefytron.")

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Оплата отменена.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(pay_button, pattern="^pay$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("🤖 Бот запущен! Готов принимать оплату звёздами.")
    app.run_polling()

if __name__ == "__main__":
    main()