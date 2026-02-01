import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List
import json
import hashlib

DATABASE_PATH = "astro_bot.db"


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                birth_date TEXT,
                birth_time TEXT,
                birth_place TEXT,
                zodiac_sign TEXT,
                free_readings_used INTEGER DEFAULT 0,
                subscription_until TEXT,
                referrer_id INTEGER,
                referral_code TEXT UNIQUE,
                referral_count INTEGER DEFAULT 0,
                referral_bonus_days INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id)
            )
        """)
        
        # Настройки уведомлений пользователя
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_notifications (
                user_id INTEGER PRIMARY KEY,
                daily_horoscope BOOLEAN DEFAULT FALSE,
                astro_alarm BOOLEAN DEFAULT FALSE,
                astro_alarm_time TEXT DEFAULT '09:00',
                retrograde_alerts BOOLEAN DEFAULT FALSE,
                moon_calendar BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица рефералов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                bonus_applied BOOLEAN DEFAULT FALSE,
                created_at TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица раскладов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reading_type TEXT,
                question TEXT,
                cards TEXT,
                interpretation TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_id TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                payment_type TEXT NOT NULL,
                payment_method TEXT DEFAULT 'yookassa',
                status TEXT DEFAULT 'pending',
                description TEXT,
                paid_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица купленных услуг
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchased_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_type TEXT NOT NULL,
                payment_id TEXT,
                used BOOLEAN DEFAULT FALSE,
                created_at TEXT,
                used_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()


# ==================== ПОЛЬЗОВАТЕЛИ ====================

def generate_referral_code(user_id: int) -> str:
    """Генерация уникального реферального кода"""
    hash_input = f"{user_id}_astro_ai_secret"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()


async def get_user(user_id: int) -> Optional[dict]:
    """Получить пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(
    user_id: int, 
    username: str, 
    first_name: str,
    referrer_id: Optional[int] = None
) -> dict:
    """Создать пользователя"""
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, referrer_id, referral_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, referrer_id, referral_code, now, now))
        
        # Создаём настройки уведомлений
        await db.execute("""
            INSERT OR IGNORE INTO user_notifications (user_id)
            VALUES (?)
        """, (user_id,))
        
        await db.commit()
    
    return await get_user(user_id)


async def get_user_by_referral_code(referral_code: str) -> Optional[dict]:
    """Найти пользователя по реферальному коду"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE referral_code = ?", (referral_code.upper(),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_user_birth_data(
    user_id: int, 
    birth_date: str, 
    birth_time: str, 
    birth_place: str,
    zodiac_sign: str
):
    """Обновить данные рождения"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                birth_date = ?, birth_time = ?, birth_place = ?,
                zodiac_sign = ?, updated_at = ?
            WHERE user_id = ?
        """, (birth_date, birth_time, birth_place, zodiac_sign, now, user_id))
        await db.commit()


# ==================== УВЕДОМЛЕНИЯ ====================

async def get_user_notifications(user_id: int) -> Optional[dict]:
    """Получить настройки уведомлений"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_notifications WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_notification_setting(user_id: int, setting: str, value):
    """Обновить настройку уведомлений"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"""
            UPDATE user_notifications SET {setting} = ? WHERE user_id = ?
        """, (value, user_id))
        await db.commit()


async def get_users_with_notification(setting: str) -> List[dict]:
    """Получить пользователей с включённым уведомлением"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"""
            SELECT u.*, n.* FROM users u
            JOIN user_notifications n ON u.user_id = n.user_id
            WHERE n.{setting} = TRUE AND u.subscription_until > ?
        """, (datetime.now().isoformat(),)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ==================== ПОДПИСКА ====================

async def set_subscription(user_id: int, until: datetime):
    """Установить подписку"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET subscription_until = ?, updated_at = ? WHERE user_id = ?
        """, (until.isoformat(), datetime.now().isoformat(), user_id))
        await db.commit()


async def extend_subscription(user_id: int, days: int) -> datetime:
    """Продлить подписку на N дней"""
    user = await get_user(user_id)
    
    if user and user.get('subscription_until'):
        current_until = datetime.fromisoformat(user['subscription_until'])
        if current_until > datetime.now():
            new_until = current_until + timedelta(days=days)
        else:
            new_until = datetime.now() + timedelta(days=days)
    else:
        new_until = datetime.now() + timedelta(days=days)
    
    await set_subscription(user_id, new_until)
    return new_until


async def has_active_subscription(user_id: int) -> bool:
    """Проверить активную подписку"""
    user = await get_user(user_id)
    if not user or not user.get('subscription_until'):
        return False
    sub_until = datetime.fromisoformat(user['subscription_until'])
    return sub_until > datetime.now()


async def get_subscription_end(user_id: int) -> Optional[datetime]:
    """Получить дату окончания подписки"""
    user = await get_user(user_id)
    if not user or not user.get('subscription_until'):
        return None
    return datetime.fromisoformat(user['subscription_until'])


# ==================== РЕФЕРАЛЫ ====================

async def add_referral(referrer_id: int, referred_id: int) -> bool:
    """Добавить реферала"""
    if referrer_id == referred_id:
        return False
    
    referrer = await get_user(referrer_id)
    if not referrer:
        return False
    
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO referrals (referrer_id, referred_id, created_at)
                VALUES (?, ?, ?)
            """, (referrer_id, referred_id, now))
            
            await db.execute("""
                UPDATE users SET referral_count = referral_count + 1, updated_at = ?
                WHERE user_id = ?
            """, (now, referrer_id))
            
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def apply_referral_bonus(referrer_id: int, referred_id: int, bonus_days: int) -> bool:
    """Применить бонус за реферала"""
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT bonus_applied FROM referrals WHERE referrer_id = ? AND referred_id = ?",
            (referrer_id, referred_id)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0]:
                return False
        
        await db.execute("""
            UPDATE referrals SET bonus_applied = TRUE WHERE referrer_id = ? AND referred_id = ?
        """, (referrer_id, referred_id))
        
        await db.execute("""
            UPDATE users SET referral_bonus_days = referral_bonus_days + ?, updated_at = ?
            WHERE user_id = ?
        """, (bonus_days, now, referrer_id))
        
        await db.commit()
    
    await extend_subscription(referrer_id, bonus_days)
    return True


async def get_referral_stats(user_id: int) -> dict:
    """Получить статистику рефералов"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)
        ) as cursor:
            total = (await cursor.fetchone())[0]
        
        async with db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND bonus_applied = TRUE",
            (user_id,)
        ) as cursor:
            activated = (await cursor.fetchone())[0]
        
        user = await get_user(user_id)
        bonus_days = user.get('referral_bonus_days', 0) if user else 0
        
        return {
            "total_referrals": total,
            "activated_referrals": activated,
            "pending_referrals": total - activated,
            "total_bonus_days": bonus_days
        }


async def get_referrals_list(user_id: int, limit: int = 10) -> List[dict]:
    """Получить список рефералов"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.*, u.username, u.first_name
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ==================== РАСКЛАДЫ ====================

async def increment_readings(user_id: int):
    """Увеличить счётчик бесплатных раскладов"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET free_readings_used = free_readings_used + 1
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def save_reading(
    user_id: int, 
    reading_type: str, 
    question: str, 
    cards: list, 
    interpretation: str
):
    """Сохранить расклад"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO readings 
            (user_id, reading_type, question, cards, interpretation, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, reading_type, question, json.dumps(cards, ensure_ascii=False), interpretation, now))
        await db.commit()


async def can_use_free_reading(user_id: int, limit: int = 1) -> bool:
    """Можно ли использовать бесплатный расклад"""
    if await has_active_subscription(user_id):
        return True
    user = await get_user(user_id)
    if not user:
        return True
    return user.get('free_readings_used', 0) < limit


# ==================== ПЛАТЕЖИ ====================

async def create_payment(
    user_id: int,
    payment_id: str,
    amount: float,
    payment_type: str,
    description: str = "",
    payment_method: str = "yookassa",
    currency: str = "RUB"
) -> int:
    """Создать запись о платеже"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO payments 
            (user_id, payment_id, amount, currency, payment_type, payment_method, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (user_id, payment_id, amount, currency, payment_type, payment_method, description, now, now))
        await db.commit()
        return cursor.lastrowid


async def update_payment_status(payment_id: str, status: str, payment_method: str = None):
    """Обновить статус платежа"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if status == 'succeeded':
            await db.execute("""
                UPDATE payments SET status = ?, paid_at = ?, updated_at = ?
                WHERE payment_id = ?
            """, (status, now, now, payment_id))
        else:
            await db.execute("""
                UPDATE payments SET status = ?, updated_at = ?
                WHERE payment_id = ?
            """, (status, now, payment_id))
        await db.commit()


async def get_payment(payment_id: str) -> Optional[dict]:
    """Получить платёж"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ==================== УСЛУГИ ====================

async def add_purchased_service(user_id: int, service_type: str, payment_id: str):
    """Добавить купленную услугу"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO purchased_services (user_id, service_type, payment_id, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, service_type, payment_id, now))
        await db.commit()


async def has_purchased_service(user_id: int, service_type: str) -> bool:
    """Есть ли неиспользованная услуга"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("""
            SELECT id FROM purchased_services 
            WHERE user_id = ? AND service_type = ? AND used = FALSE
        """, (user_id, service_type)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def use_purchased_service(user_id: int, service_type: str) -> bool:
    """Использовать купленную услугу"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            UPDATE purchased_services SET used = TRUE, used_at = ?
            WHERE user_id = ? AND service_type = ? AND used = FALSE
        """, (now, user_id, service_type))
        await db.commit()
        return cursor.rowcount > 0