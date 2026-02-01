from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Таро", callback_data="tarot_menu"),
            InlineKeyboardButton(text="⭐ Гороскоп", callback_data="horoscope_menu")
        ],
        [
            InlineKeyboardButton(text="💕 Совместимость", callback_data="compatibility"),
            InlineKeyboardButton(text="🌙 Лунный день", callback_data="moon_day")
        ],
        [
            InlineKeyboardButton(text="🔮 Астро-функции", callback_data="astro_features")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⭐ Подписка", callback_data="subscription")
        ],
        [
            InlineKeyboardButton(text="👥 Пригласить друга", callback_data="referral_program")
        ]
    ])


def get_tarot_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎴 Карта дня", callback_data="tarot_one")],
        [InlineKeyboardButton(text="🔮 3 карты", callback_data="tarot_three")],
        [InlineKeyboardButton(text="💕 На отношения", callback_data="tarot_love")],
        [InlineKeyboardButton(text="💼 На карьеру", callback_data="tarot_career")],
        [InlineKeyboardButton(text="❓ Да/Нет", callback_data="tarot_yesno")],
        [InlineKeyboardButton(text="🏛️ Кельтский крест", callback_data="tarot_celtic")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    from config import config
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 {config.SUBSCRIPTION_PRICE}₽", callback_data="pay_subscription")],
        [InlineKeyboardButton(text=f"⭐ {config.SUBSCRIPTION_STARS} Stars", callback_data="stars_subscription")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_back_keyboard(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])


def get_ask_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Без вопроса", callback_data="no_question")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="tarot_menu")]
    ])