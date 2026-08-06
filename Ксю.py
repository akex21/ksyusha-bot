import os
import random
import threading
from datetime import datetime, date
from flask import Flask
from telebot import TeleBot, types
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# -------------------------------------------------------------
# НАСТРОЙКИ И ЗАЩИТА
# -------------------------------------------------------------
TOKEN = '8682556777:AAEmSYXZyvwcl7ZQ5tmYAFsRRK2XmtMO-0s'
YOUR_TELEGRAM_ID = 749984711
KSYUSHA_USERNAME = 'rriritt'  # Юзернейм Ксюши

# 🗓 Дата начала отношений (11 мая 2026)
RELATIONSHIP_START_DATE = date(2026, 5, 11)  

bot = TeleBot(TOKEN)
MSK_TZ = timezone('Europe/Moscow')

CHAT_ID_FILE = "ksyusha_chat_id.txt"
HUGS_FILE = "hugs_count.txt"
WISHES_STATE_FILE = "wishes_enabled.txt"

# -------------------------------------------------------------
# ХРАНЕНИЕ ДАННЫХ
# -------------------------------------------------------------
def get_saved_chat_id():
    if os.path.exists(CHAT_ID_FILE):
        try:
            with open(CHAT_ID_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return None
    return None

def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(chat_id))

def get_hugs_count():
    if os.path.exists(HUGS_FILE):
        try:
            with open(HUGS_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def increment_hugs():
    count = get_hugs_count() + 1
    with open(HUGS_FILE, "w") as f:
        f.write(str(count))
    return count

def is_wishes_enabled():
    if os.path.exists(WISHES_STATE_FILE):
        try:
            with open(WISHES_STATE_FILE, "r") as f:
                return f.read().strip() == "1"
        except Exception:
            return True
    return True

def set_wishes_enabled(state: bool):
    with open(WISHES_STATE_FILE, "w") as f:
        f.write("1" if state else "0")

ksyusha_chat_id = get_saved_chat_id()

def check_access(user):
    if user.id == YOUR_TELEGRAM_ID:
        return True
    if user.username and user.username.lower().replace('@', '') == KSYUSHA_USERNAME.lower():
        return True
    return False

# -------------------------------------------------------------
# БАЗЫ ДАННЫХ
# -------------------------------------------------------------
WEEKLY_WISHES = [
    "☀️ *Понедельник:* Пусть эта неделя начинается с твоей лёгкой улыбки! Напоминаю: против твоих зелёных глаз у меня всё так же нет шансов. ❤️",
    "☀️ *Вторник:* Желаю тебе самого тёплого и уютного дня. Помни, ты - лучшее, что происходит со мной каждый день! ✨",
    "☀️ *Среда:* Экватор недели! Маленькое напоминание посреди дня: ты невероятная, любимая и самая лучшая. 🌿",
    "☀️ *Четверг:* Пусть сегодняшний день принесёт тебе столько же радости и тепла, сколько ты даришь мне своей улыбкой! 💖",
    "☀️ *Пятница:* Ура, почти выходные! Вспоминаю твой смех и невольно улыбаюсь сам. Хорошего дня, сокровище! 🥰",
    "☀️ *Суббота:* Желаю самых неспешных, умиротворённых и приятных выходных. Наслаждайся каждым мгновением! ✨",
    "☀️ *Воскресенье:* Пусть этот день будет наполнен уютом, отдыхом и любимым чаем. Помни, что я всегда рядом! ❤️"
]

COMPLIMENTS = [
    "Ты делаешь любой, даже самый суматошный день, лёгким и тёплым. ✨",
    "Вспоминаю твою улыбку - и невольно улыбаюсь сам. ❤️",
    "Просто напоминаю: ты моя самая большая радость.",
    "Рядом с тобой я чувствую себя по-настоящему дома.",
    "Спасибо за твою нежность и за то, какая ты настоящая.",
    "Ты - лучшее, что произошло со мной.",
    "Каждая минута с тобой - это бесценный подарок.",
    "Твой смех - мой любимый звук на свете. 🎶",
    "Ты вдохновляешь меня становиться лучше каждый день.",
    "Твой взгляд способен исправить абсолютно любой неудачный день. ✨",
    "Ты прекрасна в любой момент - и спросонья, и в нарядном платье.",
    "У тебя невероятно доброе и чуткое сердце.",
    "Ты - моё самое любимое совпадение в жизни. ❤️",
    "Просто знай: ты невероятно сильно любима. 💖"
]

QUOTES = [
    "«Против твоих зелёных глаз у меня с первого дня нет никаких шансов...» 🌿",
    "«Самые счастливые моменты - те, что мы проживаем вместе.»",
    "«Эффект В.З.Г.: Взглянула, Заворожила, Готово! Работает бесперебойно.» ✨",
    "«С той самой прогулки в Приморском парке и до сегодня - ты всё так же прекрасна.» 🌲",
    "«Дом - это не адрес. Дом - это когда ты держишь меня за руку.»",
    "«С тобой даже тихий вечер с чаем превращается в лучшее событие недели.» ☕",
    "«Любить - значит видеть в одном человеке целый мир. Я свой мир нашёл.» ❤️",
    "«Есть люди, с которыми легко. А есть ты - с кем идеально.» ✨",
    "«Ты - та самая деталь, благодаря которой вся мозаика жизни сложилась.»"
]

HUG_TYPES = [
    "крепкое согревающее объятие ☕",
    "нежное объятие с поцелуем в щёчку 🥰",
    "уютное объятие со спины 🌿",
    "самое тёплое медвежье объятие 🧸",
    "искреннее и долгое объятие ✨"
]

COUPONS = {
    "c_movie": "🎬 Выбор фильма на вечер без споров",
    "c_playlist": "🎧 Персональный плейлист от Саши",
    "c_walk": "🍦 Прогулка по любому твоему маршруту",
    "c_win": "👑 Королева споров (1 победа без споров)",
    "c_tea": "☕ Заботливый чай/кофе при встрече"
}

REACTION_RESPONSES = {
    "act_hug": "🥰 *Саша крепко обнял тебя в ответ!*",
    "act_kiss": "😘 *Саша нежно поцеловал тебя в щёчку!*",
    "act_pat": "💆‍♂️ *Саша заботливо погладил тебя по голове!*",
    "act_bite": "😼 *Саша любя укусил тебя за щёчку!*"
}

# -------------------------------------------------------------
# КЛАВИАТУРЫ И МЕНЮ
# -------------------------------------------------------------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💌 Тёплые слова"),
        types.KeyboardButton("❤️ Обнимашки"),
        types.KeyboardButton("🎁 Купоны желаний"),
        types.KeyboardButton("💬 Написать Саше"),
        types.KeyboardButton("⚙️ Настройки и Инфо")
    )
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💋 Отправить поцелуй"),
        types.KeyboardButton("☕ Передать заботу"),
        types.KeyboardButton("🤗 Обнять в ответ"),
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def get_words_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("✨ Комплимент"),
        types.KeyboardButton("📖 Цитата"),
        types.KeyboardButton("☀️ Пожелание на сегодня"),
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def get_hugs_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🤗 Обнять Сашу"),
        types.KeyboardButton("📊 Счётчик объятий"),
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def get_settings_keyboard():
    w_status = "🔔 Рассылка: Включена ✅" if is_wishes_enabled() else "🔕 Рассылка: Выключена ❌"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton(w_status),
        types.KeyboardButton("🗓 Сколько дней мы вместе"),
        types.KeyboardButton("ℹ️ О боте"),
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def get_coupons_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for code, text in COUPONS.items():
        markup.add(types.InlineKeyboardButton(text, callback_data=f"use_coupon_{code}"))
    return markup

# -------------------------------------------------------------
# ОБРАБОТКА КОМАНД
# -------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    global ksyusha_chat_id
    if not check_access(message.from_user):
        bot.send_message(message.chat.id, "🔒 Извини, это частный бот, созданный только для одного специального человека!")
        return

    if message.from_user.id != YOUR_TELEGRAM_ID:
        ksyusha_chat_id = message.chat.id
        save_chat_id(ksyusha_chat_id)

    text = (
        "Привет, Ксюш! 🌿\n\n"
        "Я твой личный бот-помощник и хранитель тёплых слов от Саши.\n"
        "Выбирай нужный раздел в меню ниже 👇"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

# СЕКРЕТНАЯ ПАНЕЛЬ САШИ
@bot.message_handler(commands=['sasha', 'admin'])
def show_admin_panel(message):
    if message.from_user.id == YOUR_TELEGRAM_ID:
        bot.send_message(
            message.chat.id, 
            "👑 *Панель управления Саши*\n\nОтсюда ты можешь отправлять мгновенные знаки внимания Ксюше!", 
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "🔒 Это секретная панель Саши! 🤫")

# -------------------------------------------------------------
# ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ И МОСТА СВЯЗИ
# -------------------------------------------------------------
@bot.message_handler(content_types=['text', 'sticker', 'photo', 'voice', 'video_note', 'document', 'animation'])
def handle_all_messages(message):
    global ksyusha_chat_id

    if not check_access(message.from_user):
        bot.send_message(message.chat.id, "🔒 Доступ ограничен.")
        return

    # Сохраняем chat_id Ксюши
    if message.from_user.id != YOUR_TELEGRAM_ID:
        if ksyusha_chat_id != message.chat.id:
            ksyusha_chat_id = message.chat.id
            save_chat_id(ksyusha_chat_id)

    # Если САША отвечает на пересланное сообщение от Ксюши
    if message.from_user.id == YOUR_TELEGRAM_ID and message.reply_to_message:
        target_id = get_saved_chat_id()
        if target_id:
            bot.send_message(target_id, "💬 *Саша ответил тебе:*", parse_mode="Markdown")
            bot.copy_message(target_id, message.chat.id, message.message_id)
            bot.send_message(message.chat.id, "Ответ доставлен Ксюше! 📬")
        return

    # 1. Секретные действия Саши
    if message.from_user.id == YOUR_TELEGRAM_ID:
        target_id = get_saved_chat_id()
        if message.text == "💋 Отправить поцелуй":
            if target_id:
                bot.send_message(target_id, "💋 *Саша только что прислал тебе внезапный поцелуй прямо посреди дня!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Поцелуй успешно доставлен Ксюше! 😘")
            return
        elif message.text == "☕ Передать заботу":
            if target_id:
                bot.send_message(target_id, "☕ *Саша заботливо передаёт тебе чашку тёплого чая и обнимает!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Забота доставлена! 🥰")
            return
        elif message.text == "🤗 Обнять в ответ":
            if target_id:
                bot.send_message(target_id, "🥰 *Саша крепко обнял тебя!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Объятие доставлено! ❤️")
            return

    # 2. Переходы по главным разделам
    if message.text in ["💌 Тёплые слова"]:
        bot.send_message(message.chat.id, "Выбери, что именно ты хочешь прочитать:", reply_markup=get_words_keyboard())
        return

    elif message.text in ["❤️ Обнимашки"]:
        bot.send_message(message.chat.id, "Раздел самых тёплых обнимашек 🤗", reply_markup=get_hugs_keyboard())
        return

    elif message.text in ["🎁 Купоны желаний"]:
        bot.send_message(
            message.chat.id, 
            "🎁 *Маленькие купоны желаний*\n\nВыбери купон, который хочешь активировать прямо сейчас, и Саша сразу получит уведомление!", 
            reply_markup=get_coupons_inline(),
            parse_mode="Markdown"
        )
        return

    elif message.text in ["⚙️ Настройки и Инфо", "⏰ Расписание"]:
        bot.send_message(message.chat.id, "Настройки и информация:", reply_markup=get_settings_keyboard())
        return

    elif message.text in ["🔙 Главное меню"]:
        bot.send_message(message.chat.id, "Возвращаемся в главное меню 🌿", reply_markup=get_main_keyboard())
        return

    # 3. Подразделы "Тёплые слова"
    elif message.text in ["✨ Комплимент"]:
        bot.send_message(message.chat.id, f"«{random.choice(COMPLIMENTS)}»")
        return

    elif message.text in ["📖 Цитата", "📖 Романтическая цитата"]:
        bot.send_message(message.chat.id, f"{random.choice(QUOTES)}")
        return

    elif message.text in ["☀️ Пожелание на сегодня"]:
        day_of_week = datetime.now(MSK_TZ).weekday()
        bot.send_message(message.chat.id, WEEKLY_WISHES[day_of_week], parse_mode="Markdown")
        return

    # 4. Подразделы "Обнимашки" с Ачивкам
    elif message.text in ["🤗 Обнять Сашу", "❤️ Обнять Сашу"]:
        count = increment_hugs()
        hug_type = random.choice(HUG_TYPES)
        bot.send_message(message.chat.id, f"Отправлено {hug_type}! 🥰\n\nЭто ваше *{count}-е* объятие в боте!", parse_mode="Markdown")

        # Проверка Ачивок
        achievements = {
            25: "🧸 *Достижение разблокировано: Новичок-обнимашка (25 объятий)!*",
            50: "✨ *Достижение разблокировано: Уровень Уютный пледик (50 объятий)!*",
            100: "❤️ *Достижение разблокировано: Мастера нежности (100 объятий)!*",
            250: "🔥 *Достижение разблокировано: Профессиональные обнимальщики (250 объятий)!*",
            500: "🏆 *Достижение разблокировано: Абсолютные рекордсмены любви (500 объятий)!*"
        }
        if count in achievements:
            bot.send_message(message.chat.id, achievements[count], parse_mode="Markdown")

        if YOUR_TELEGRAM_ID:
            inline_markup = types.InlineKeyboardMarkup(row_width=2)
            btn1 = types.InlineKeyboardButton("🥰 Обнять в ответ", callback_data="act_hug")
            btn2 = types.InlineKeyboardButton("😘 Поцеловать", callback_data="act_kiss")
            btn3 = types.InlineKeyboardButton("💆‍♂️ Погладить", callback_data="act_pat")
            btn4 = types.InlineKeyboardButton("😼 Укусить за щёчку", callback_data="act_bite")
            inline_markup.add(btn1, btn2, btn3, btn4)
            
            bot.send_message(
                YOUR_TELEGRAM_ID, 
                f"🔔 *Ксюша только что обняла тебя через бота!*\nФормат: _{hug_type}_\n(Всего объятий: {count})", 
                reply_markup=inline_markup, 
                parse_mode="Markdown"
            )
        return

    elif message.text in ["📊 Счётчик объятий"]:
        count = get_hugs_count()
        bot.send_message(message.chat.id, f"📊 Вы обнялись через бота уже *{count}* раз! ❤️", parse_mode="Markdown")
        return

    # 5. Подразделы "Настройки и Инфо"
    elif message.text in ["🔔 Рассылка: Включена ✅", "🔕 Рассылка: Выключена ❌"]:
        current_state = is_wishes_enabled()
        new_state = not current_state
        set_wishes_enabled(new_state)
        status_msg = "включили ✅" if new_state else "поставили на паузу ❌"
        bot.send_message(message.chat.id, f"Утреннюю рассылку пожеланий {status_msg}.", reply_markup=get_settings_keyboard())
        return

    elif message.text in ["🗓 Сколько дней мы вместе"]:
        today = date.today()
        days_together = (today - RELATIONSHIP_START_DATE).days
        bot.send_message(message.chat.id, f"🗓 Вы вместе уже *{days_together}* дней! ❤️\nИ каждый из них - особенный.", parse_mode="Markdown")
        return

    elif message.text in ["ℹ️ О боте"]:
        info_text = (
            "🌿 *О боте*\n\n"
            "Этот маленький цифровой уголок создан специально для тебя - чтобы ты всегда знала, "
            "что о тебе помнят, заботятся и любят каждую секунду, где бы мы ни находились.\n\n"
            "✨ *Что умеет бот:*\n"
            "☀️ *Утренние послания:* Каждый день ровно в *11:00 по Москве* тебя ждёт новое тёплое пожелание.\n"
            "💌 *Прямой мост:* Любой твой текст, фото, голосовое сообщение, кружочек или стикер мгновенно прилетают мне в ЛС.\n"
            "🤗 *Обнимашки:* Когда хочется тепла - нажми кнопку, и я сразу обниму тебя в ответ.\n"
            "🎁 *Купоны:* Маленькие приятные желалочки.\n"
            "🗓 *Наша история:* Бот бережно хранит и считает каждый день нашего счастья.\n\n"
            "_Сделано с бесконечной любовью специально для Ксюши._ ❤️"
        )
        bot.send_message(message.chat.id, info_text, parse_mode="Markdown")
        return

    elif message.text in ["💬 Написать Саше"]:
        bot.send_message(
            message.chat.id, 
            "💌 *Прямая связь с Сашей*\n\nПросто отправь прямо в этот чат любой текст, фото, картинку, голосовое сообщение, кружочек или стикер - и бот моментально перешлёт это Саше!", 
            parse_mode="Markdown"
        )
        return

    # 6. ПЕРЕСЫЛКА ЛЮБОГО ДРУГОГО КОНТЕНТА ОТ КСЮШИ САШЕ
    if message.from_user.id != YOUR_TELEGRAM_ID:
        bot.send_message(YOUR_TELEGRAM_ID, "💌 *Сообщение от Ксюши:*", parse_mode="Markdown")
        bot.copy_message(YOUR_TELEGRAM_ID, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "Сообщение доставлено Саше! 📬")

# -------------------------------------------------------------
# ОБРАБОТКА ИНТЕРАКТИВНЫХ КНОПОК
# -------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("use_coupon_"))
def handle_coupon_activation(call):
    coupon_code = call.data.replace("use_coupon_", "")
    coupon_name = COUPONS.get(coupon_code, "Неизвестный купон")
    
    bot.answer_callback_query(call.id, "Купон активирован!")
    bot.send_message(call.message.chat.id, f"✅ Ты активировала купон:\n*{coupon_name}*\n\nСаша уже получил уведомление! ❤️", parse_mode="Markdown")

    if YOUR_TELEGRAM_ID:
        inline_markup = types.InlineKeyboardMarkup()
        btn_accept = types.InlineKeyboardButton("Принять в работу ✅", callback_data="accept_coupon_action")
        inline_markup.add(btn_accept)

        bot.send_message(
            YOUR_TELEGRAM_ID,
            f"🎁 *Ксюша активировала купон!*\n\nНазвание: _{coupon_name}_",
            reply_markup=inline_markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data == "accept_coupon_action")
def handle_accept_coupon(call):
    target_id = get_saved_chat_id()
    if target_id:
        bot.send_message(target_id, "🥰 *Саша принял твой купон в работу!*", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Уведомление отправлено Ксюше!")
        bot.edit_message_text("✅ Ты принял купон!", call.from_user.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("act_"))
def handle_hug_reactions(call):
    target_id = get_saved_chat_id()
    text_to_send = REACTION_RESPONSES.get(call.data, "🥰 *Саша передаёт тебе тёплый привет!*")

    if target_id:
        bot.send_message(target_id, text_to_send, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Реакция отправлена Ксюше!")
        
        clean_text = text_to_send.replace("*", "")
        bot.edit_message_text(f"✅ Ты ответил: {clean_text}", call.from_user.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Ксюша ещё не запускала бота.")

# -------------------------------------------------------------
# ЕЖЕДНЕВНАЯ РАССЫЛКА (СТРОГО В 11:00 ПО МОСКВЕ)
# -------------------------------------------------------------
def send_daily_message():
    if is_wishes_enabled():
        target_id = get_saved_chat_id()
        if target_id:
            day_of_week = datetime.now(MSK_TZ).weekday()
            wish_text = WEEKLY_WISHES[day_of_week]
            bot.send_message(target_id, wish_text, parse_mode="Markdown")

scheduler = BackgroundScheduler(timezone=MSK_TZ)
scheduler.add_job(send_daily_message, 'cron', hour=11, minute=0, id='daily_wish_job')
scheduler.start()

# -------------------------------------------------------------
# ВЕБ-СЕРВЕР ДЛЯ РАЗВЕРТЫВАНИЯ НА RENDER
# -------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Бот работает 24/7!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run, daemon=True).start()

# -------------------------------------------------------------
# ЗАПУСК БОТА
# -------------------------------------------------------------
if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling()
if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling()
