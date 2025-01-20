import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import aiohttp
import asyncio
from token import get_token


BOT_TOKEN = ""
CHANNEL_ID = ""
GIGACHAT_API_URL = ""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Получаем токен для ГигаЧат
auth_token = ""
current_token = get_token(auth_token)  # Получаем токен для ГигаЧат
print(f"Полученный токен: {current_token}")  # Выводим токен для проверки


# Клавиатура для подписанных пользователей
def subscribed_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти на маркетплейс", url="")],
            [InlineKeyboardButton(text="Перейти на сайт", url="")],
            [InlineKeyboardButton(text="Перейти на вк", url="")],
            [InlineKeyboardButton(text="Частые вопросы", callback_data="faq_menu")]
        ]
    )


# Клавиатура для неподписанных пользователей
def unsubscribed_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="")]
        ]
    )


# Проверка подписки на канал
async def check_subscription(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHANNEL_ID, "user_id": user_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                result = await response.json()

                if result.get("ok"):
                    status = result["result"]["status"]
                    return status in ["member", "administrator", "creator"]
                else:
                    print(f"Ошибка API Telegram: {result.get('description')}")
                    return False
    except Exception as e:
        print(f"Ошибка при обращении к API Telegram: {e}")
        return False


# Функция для отправки вопросов в ГигаЧат
def ask_gigachat(question):
    global current_token  # Используем глобальную переменную токен
    headers = {
        "Authorization": f"Bearer {current_token}",  # Используем токен из get_token
        "Content-Type": "application/json"  # Используем правильный Content-Type
    }

    # Формируем payload для отправки в GigaChat API
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "user", "content": question}
        ],
        "stream": False,
        "repetition_penalty": 1
    }

    try:
        # Отправка запроса с правильным контентом
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=data,
                                 verify=False)  # Используем json вместо data
        response.raise_for_status()  # Проверка на успешный статус
        return response.json().get("choices", [{}])[0].get("message", {}).get("content",
                                                                              "Извините, я не смог обработать ваш вопрос.")
    except requests.RequestException as e:
        print(f"Ошибка при обращении к ГигаЧат: {e}")
        return "Произошла ошибка при обработке вашего вопроса."


def faq_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Как выбрать продукт?", callback_data="faq_product")],
            [InlineKeyboardButton(text="Как использовать товар?", callback_data="faq_usage")],
            [InlineKeyboardButton(text="Связаться с менеджером", callback_data="faq_contact")],
            [InlineKeyboardButton(text="Консультант", callback_data="consultant")]  # Кнопка консультанта
        ]
    )


@dp.callback_query(F.data == "faq_menu")
async def faq_menu_handler(callback_query: CallbackQuery):
    await callback_query.message.answer(
        "Выберите интересующий вас вопрос:",
        reply_markup=faq_keyboard()
    )
    await callback_query.answer()  # Закрыть уведомление о нажатии


@dp.callback_query(F.data.in_({"faq_product", "faq_usage", "faq_contact", "consultant"}))
async def faq_callback_handler(callback_query: CallbackQuery):
    data = callback_query.data

    if data == "faq_product":
        await callback_query.message.answer("Чтобы выбрать продукт, ознакомьтесь с нашим каталогом: https://ozon.ru")
    elif data == "faq_usage":
        await callback_query.message.answer("Инструкция по использованию доступна на сайте производителя.")
    elif data == "faq_contact":
        await callback_query.message.answer(
            "Связаться с менеджером вы можете по электронной почте support@example.com.")
    elif data == "consultant":
        await callback_query.message.answer("Связано с консультантом: отправьте свой вопрос, и мы его передадим!")
        # Ожидаем следующий вопрос от пользователя
        await callback_query.answer()

    await callback_query.answer()  # Закрыть уведомление о нажатии


# Стартовое сообщение
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or "Пользователь"

    print(f"Проверяем подписку для user_id={user_id}")

    is_subscribed = await check_subscription(user_id)

    if is_subscribed:
        await message.answer(
            f"Привет, {user_name}! Добро пожаловать в наш бот. Чем могу помочь?",
            reply_markup=subscribed_keyboard(),  # Клавиатура для подписанных пользователей
        )
    else:
        await message.answer(
            "Для работы с ботом необходимо подписаться на наш канал. "
            "Пожалуйста, подпишитесь и нажмите /start снова.",
            reply_markup=unsubscribed_keyboard(),  # Клавиатура для неподписанных пользователей
        )


# Обработка пользовательских вопросов через ГигаЧат
@dp.message()
async def user_question_handler(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or "Пользователь"

    # Добавляем задержку перед запросом к ГигаЧату
    await asyncio.sleep(2)  # Задержка в 2 секунды

    response = ask_gigachat(message.text)  # Отправка вопроса в ГигаЧат
    await message.answer(response)  # Отправка ответа пользователю

    print(f"[Вопрос]: от {user_name} ({user_id}): {message.text}")
    print(f"[Ответ ГигаЧата]: {response}")


# Логирование сообщений
@dp.message()
async def log_message(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or "Пользователь"
    print(f"[ЛОГ]: user_id={user_id}, username={user_name}, message={message.text}")


# Запуск бота с использованием polling
async def main():
    print("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
