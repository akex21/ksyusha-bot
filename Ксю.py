import os
import json
import random
import threading
from datetime import datetime, date

from flask import Flask
from telebot import TeleBot, types
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# -------------------------------------------------------------
# НАСТРОЙКИ
# -------------------------------------------------------------
# В Render задайте переменную окружения BOT_TOKEN.
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN. Добавьте его в Environment Variables на Render.")

YOUR_TELEGRAM_ID = 749984711
KSYUSHA_USERNAME = "rriritt"
RELATIONSHIP_START_DATE = date(2026, 5, 11)
MSK_TZ = timezone("Europe/Moscow")

bot = TeleBot(TOKEN)

CHAT_ID_FILE = "ksyusha_chat_id.txt"
HUGS_FILE = "hugs_count.txt"
WISHES_STATE_FILE = "wishes_enabled.txt"
BOT_DATA_FILE = "bot_data.json"

# Состояния действуют только в памяти до выполнения действия.
user_states = {}

# -------------------------------------------------------------
# ХРАНЕНИЕ ДАННЫХ
# -------------------------------------------------------------
def load_bot_data():
    default_data = {"memories": [], "daily_history": []}
    if not os.path.exists(BOT_DATA_FILE):
        return default_data

    try:
        with open(BOT_DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            return default_data
        data.setdefault("memories", [])
        data.setdefault("daily_history", [])
        return data
    except (OSError, json.JSONDecodeError):
        return default_data


def save_bot_data(data):
    temp_file = f"{BOT_DATA_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temp_file, BOT_DATA_FILE)


def get_saved_chat_id():
    if not os.path.exists(CHAT_ID_FILE):
        return None
    try:
        with open(CHAT_ID_FILE, "r", encoding="utf-8") as file:
            return int(file.read().strip())
    except (OSError, ValueError):
        return None


def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, "w", encoding="utf-8") as file:
        file.write(str(chat_id))


def get_hugs_count():
    if not os.path.exists(HUGS_FILE):
        return 0
    try:
        with open(HUGS_FILE, "r", encoding="utf-8") as file:
            return int(file.read().strip())
    except (OSError, ValueError):
        return 0


def increment_hugs():
    count = get_hugs_count() + 1
    with open(HUGS_FILE, "w", encoding="utf-8") as file:
        file.write(str(count))
    return count


def is_wishes_enabled():
    if not os.path.exists(WISHES_STATE_FILE):
        return True
    try:
        with open(WISHES_STATE_FILE, "r", encoding="utf-8") as file:
            return file.read().strip() == "1"
    except OSError:
        return True


def set_wishes_enabled(state):
    with open(WISHES_STATE_FILE, "w", encoding="utf-8") as file:
        file.write("1" if state else "0")


ksyusha_chat_id = get_saved_chat_id()


def check_access(user):
    if user.id == YOUR_TELEGRAM_ID:
        return True
    return bool(
        user.username
        and user.username.lower().replace("@", "") == KSYUSHA_USERNAME.lower()
    )


def get_ksyusha_chat_id():
    return get_saved_chat_id()


def current_author_name(user):
    if user.id == YOUR_TELEGRAM_ID:
        return "Саша"
    return "Ксюша"

# -------------------------------------------------------------
# ТЕКСТЫ
# -------------------------------------------------------------
COMPLIMENTS = [
    "Ты делаешь любой, даже самый суматошный день, лёгким и тёплым. ✨",
    "Вспоминаю твою улыбку — и невольно улыбаюсь сам. ❤️",
    "Просто напоминаю: ты моя самая большая радость.",
    "Рядом с тобой я чувствую себя по-настоящему дома.",
    "Спасибо за твою нежность и за то, какая ты настоящая.",
    "Ты — лучшее, что произошло со мной.",
    "Каждая минута с тобой — это бесценный подарок.",
    "Твой смех — мой любимый звук на свете. 🎶",
    "Ты вдохновляешь меня становиться лучше каждый день.",
    "Твой взгляд способен исправить абсолютно любой неудачный день. ✨",
    "Ты прекрасна в любой момент — и спросонья, и в нарядном платье.",
    "У тебя невероятно доброе и чуткое сердце.",
    "Ты — моё самое любимое совпадение в жизни. ❤️",
    "Просто знай: ты невероятно сильно любима. 💖",
]

QUOTES = [
    "«Против твоих зелёных глаз у меня с первого дня нет никаких шансов...» 🌿",
    "«Самые счастливые моменты — те, что мы проживаем вместе.»",
    "«Эффект В.З.Г.: Взглянула, Заворожила, Готово! Работает бесперебойно.» ✨",
    "«С той самой прогулки в Приморском парке и до сегодня — ты всё так же прекрасна.» 🌲",
    "«Дом — это не адрес. Дом — это когда ты держишь меня за руку.»",
    "«С тобой даже тихий вечер с чаем превращается в лучшее событие недели.» ☕",
    "«Любить — значит видеть в одном человеке целый мир. Я свой мир нашёл.» ❤️",
    "«Есть люди, с которыми легко. А есть ты — с кем идеально.» ✨",
    "«Ты — та самая деталь, благодаря которой вся мозаика жизни сложилась.»",
]

DAILY_WISHES = [
    "☀️ Доброе утро, Ксюш. Пусть сегодня всё сложное решается чуть легче, а хорошего будет немного больше, чем ты ждёшь. ❤️",
    "🌿 Маленькое напоминание на сегодня: пожалуйста, не забывай беречь себя. Ты очень важна для меня.",
    "☕ Желаю тебе дня без лишней спешки. А если она всё-таки будет — мысленно отправляю тебе чай, объятие и немного спокойствия.",
    "✨ Ты умеешь делать пространство вокруг себя теплее. Надеюсь, сегодня это тепло вернётся к тебе вдвойне.",
    "💌 Не обязательно быть продуктивной каждую минуту. Иногда лучший план — выдохнуть. Я рядом.",
    "🌙 Пусть сегодня у тебя будет хотя бы один момент, когда ты улыбнёшься просто так. Мне очень нравится представлять эту улыбку.",
    "🌷 Желаю тебе мягкого дня и добрых людей рядом. А вечером обязательно расскажи себе, что ты молодец.",
    "❤️ Сегодня без особого повода хочу сказать: ты очень-очень мне дорога.",
    "🌿 Пусть у тебя получится всё, что для тебя важно. А то, что не получится, пусть спокойно подождёт до завтра.",
    "☀️ Доброе утро, сокровище. Желаю, чтобы у тебя нашлась минута на любимый чай, музыку или просто тишину.",
    "✨ Ты сильнее, внимательнее и прекраснее, чем иногда позволяешь себе думать. Помни об этом сегодня.",
    "💖 Я знаю, что день может быть разным. Но в каждом его варианте ты остаёшься моей любимой Ксюшей.",
    "🌸 Пусть сегодня будет больше лёгкости, чем тревог, и больше улыбок, чем поводов для них искать.",
    "🫶 Мысленно крепко обнимаю тебя. Пусть это маленькое объятие сделает день чуточку уютнее.",
    "☕ Если день будет быстрым и шумным, пожалуйста, найди немного времени для себя. Ты заслуживаешь заботы.",
    "🌿 В тебе удивительно много света. Спасибо, что делишься им со мной.",
    "✨ Пусть сегодня какая-нибудь маленькая хорошая вещь случится именно для тебя.",
    "❤️ Иногда мне достаточно вспомнить тебя, чтобы день стал лучше. Надеюсь, это послание тоже немного согреет тебя.",
    "🌼 Желаю спокойствия в мыслях, тепла в сердце и уверенности в каждом шаге.",
    "💌 Ничего не нужно доказывать сегодня. Ты уже достаточно хорошая, умная и любимая.",
    "☀️ Пусть сегодняшнее утро начнётся бережно, а закончится чувством: «я справилась». Я в тебя верю.",
    "🌿 Где бы ты сегодня ни была, мысленно я рядом и держу тебя за руку.",
    "✨ Ты — не просто часть моего дня. Ты та, из-за кого хочется, чтобы дней вместе было бесконечно много.",
    "💖 Желаю, чтобы сегодня тебе чаще встречались поводы чувствовать себя счастливой.",
    "☕ Отправляю тебе виртуальный чай, плед и очень тёплое объятие. Пользуйся в любой момент.",
    "🌸 Пусть всё важное сложится, а лишнее не заберёт у тебя слишком много сил.",
    "❤️ Даже в самом обычном дне ты для меня остаёшься чем-то очень особенным.",
    "🌿 Надеюсь, сегодня ты посмотришь на себя так же тепло, как смотрю на тебя я.",
    "✨ Ты умеешь справляться с огромным количеством вещей. Но сегодня можно ещё и просто быть собой — этого достаточно.",
    "💌 Пожалуйста, улыбайся, когда захочется. Твоя улыбка — одна из моих любимых вещей на свете.",
    "🎉 Пятница уже рядом или уже наступила — пусть день завершится приятным ощущением, что можно наконец-то немного выдохнуть.",
    "🌿 Пусть выходной будет твоим: неспешным, уютным и наполненным тем, что действительно радует тебя.",
    "☀️ Воскресенье создано для отдыха. Желаю тебе не торопиться, согреться и набраться сил для новой недели.",
    "❤️ Хорошего дня, любимая. Я горжусь тобой — не за результаты, а просто за то, какая ты есть.",
    "🌸 Пусть сегодня тебе будет легко принимать добро, заботу и комплименты. Ты их правда заслуживаешь.",
    "✨ Если вдруг станет непросто, помни: тебе не нужно проходить всё в одиночку. Я рядом.",
    "💖 Ты — моя тихая радость, мой уют и очень важный человек. Береги себя сегодня.",
    "☕ Желаю тебе дня, в котором хватит времени и на дела, и на маленькие приятности.",
    "🌿 Пусть сегодня будет меньше «надо» и больше «хочу».",
    "❤️ Просто посылаю тебе немного любви на весь день. Пусть её хватит до нашей встречи.",
]

HUG_TYPES = [
    "крепкое согревающее объятие ☕",
    "нежное объятие с поцелуем в щёчку 🥰",
    "уютное объятие со спины 🌿",
    "самое тёплое медвежье объятие 🧸",
    "искреннее и долгое объятие ✨",
]

COUPONS = {
    "c_movie": "🎬 Выбор фильма на вечер без споров",
    "c_playlist": "🎧 Персональный плейлист от Саши",
    "c_walk": "🍦 Прогулка по любому твоему маршруту",
    "c_win": "👑 Королева споров (1 победа без споров)",
    "c_tea": "☕ Заботливый чай/кофе при встрече",
}

REACTION_RESPONSES = {
    "act_hug": "🥰 *Саша крепко обнял тебя в ответ!*",
    "act_kiss": "😘 *Саша нежно поцеловал тебя в щёчку!*",
    "act_pat": "💆‍♂️ *Саша заботливо погладил тебя по голове!*",
    "act_bite": "😼 *Саша любя укусил тебя за щёчку!*",
}

# -------------------------------------------------------------
# КЛАВИАТУРЫ
# -------------------------------------------------------------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💌 Тёплые слова"),
        types.KeyboardButton("❤️ Обнимашки"),
        types.KeyboardButton("🎁 Купоны желаний"),
        types.KeyboardButton("🖼 Наши воспоминания"),
        types.KeyboardButton("💬 Написать Саше"),
        types.KeyboardButton("⚙️ Настройки и Инфо"),
    )
    return markup


def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
    types.KeyboardButton("📤 Отправить Ксюше"),
    types.KeyboardButton("🖼 Наши воспоминания"),
    types.KeyboardButton("💋 Отправить поцелуй"),
    types.KeyboardButton("☕ Передать заботу"),
    types.KeyboardButton("🤗 Обнять в ответ"),
    types.KeyboardButton("🔙 Главное меню"),
)
    return markup


def get_words_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("✨ Комплимент"),
        types.KeyboardButton("📖 Цитата"),
        types.KeyboardButton("☀️ Пожелание на сегодня"),
        types.KeyboardButton("🔙 Главное меню"),
    )
    return markup


def get_hugs_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🤗 Обнять Сашу"),
        types.KeyboardButton("📊 Счётчик объятий"),
        types.KeyboardButton("🔙 Главное меню"),
    )
    return markup


def get_settings_keyboard():
    status = "🔔 Рассылка: Включена ✅" if is_wishes_enabled() else "🔕 Рассылка: Выключена ❌"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton(status),
        types.KeyboardButton("🗓 Сколько дней мы вместе"),
        types.KeyboardButton("ℹ️ О боте"),
        types.KeyboardButton("🔙 Главное меню"),
    )
    return markup


def get_memories_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📸➕ Добавить воспоминание"),
        types.KeyboardButton("📚 Смотреть воспоминания"),
        types.KeyboardButton("🔙 Главное меню"),
    )
    return markup


def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✖️ Отмена"))
    return markup


def get_skip_caption_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("⏭ Без подписи"),
        types.KeyboardButton("✖️ Отмена"),
    )
    return markup


def get_coupons_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for code, text in COUPONS.items():
        markup.add(types.InlineKeyboardButton(text, callback_data=f"use_coupon_{code}"))
    return markup


def get_memory_inline(index, total):
    markup = types.InlineKeyboardMarkup(row_width=3)
    previous_index = (index - 1) % total
    next_index = (index + 1) % total
    markup.add(
        types.InlineKeyboardButton("⬅️", callback_data=f"memory_show_{previous_index}"),
        types.InlineKeyboardButton(f"{index + 1} / {total}", callback_data="memory_noop"),
        types.InlineKeyboardButton("➡️", callback_data=f"memory_show_{next_index}"),
    )
    markup.add(
        types.InlineKeyboardButton("🗑 Удалить", callback_data=f"memory_delete_{index}"),
        types.InlineKeyboardButton("🔙 Закрыть", callback_data="memory_close"),
    )
    return markup

# -------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -------------------------------------------------------------
def send_memory(chat_id, index):
    data = load_bot_data()
    memories = data["memories"]
    if not memories:
        bot.send_message(chat_id, "📭 Пока нет ни одного воспоминания.")
        return

    index %= len(memories)
    memory = memories[index]
    caption_parts = [
        f"🖼 Воспоминание {index + 1} из {len(memories)}",
        f"Добавил(а): {memory['author_name']}",
        f"Дата: {memory['created_at']}",
    ]
    if memory.get("caption"):
        caption_parts.append(f"\n{memory['caption']}")
    caption = "\n".join(caption_parts)
    markup = get_memory_inline(index, len(memories))

    if memory["media_type"] == "photo":
        bot.send_photo(chat_id, memory["file_id"], caption=caption, reply_markup=markup)
    else:
        bot.send_video(chat_id, memory["file_id"], caption=caption, reply_markup=markup)


def save_pending_memory(user_id, caption):
    state = user_states.get(user_id)
    if not state or state.get("mode") != "memory_caption":
        return False

    pending = state["memory"]
    data = load_bot_data()
    data["memories"].append({
        "file_id": pending["file_id"],
        "media_type": pending["media_type"],
        "caption": caption.strip(),
        "author_id": pending["author_id"],
        "author_name": pending["author_name"],
        "created_at": datetime.now(MSK_TZ).strftime("%d.%m.%Y %H:%M"),
    })
    save_bot_data(data)
    user_states.pop(user_id, None)
    return True


def choose_daily_wish():
    data = load_bot_data()
    history = data["daily_history"][-10:]
    options = [wish for wish in DAILY_WISHES if wish not in history]
    if not options:
        options = DAILY_WISHES[:]
    wish = random.choice(options)
    data["daily_history"] = (history + [wish])[-10:]
    save_bot_data(data)
    return wish


def forward_from_sasha(message):
    target_id = get_ksyusha_chat_id()
    if not target_id:
        bot.send_message(message.chat.id, "⚠️ Ксюша ещё не запускала бота. Сначала ей нужно нажать /start.")
        return
    bot.send_message(target_id, "💌 *Сообщение от Саши:*", parse_mode="Markdown")
    bot.copy_message(target_id, message.chat.id, message.message_id)
    bot.send_message(message.chat.id, "✅ Сообщение доставлено Ксюше!", reply_markup=get_admin_keyboard())

# -------------------------------------------------------------
# КОМАНДЫ
# -------------------------------------------------------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
    global ksyusha_chat_id
    if not check_access(message.from_user):
        bot.send_message(message.chat.id, "🔒 Извини, это частный бот.")
        return

    if message.from_user.id != YOUR_TELEGRAM_ID:
        ksyusha_chat_id = message.chat.id
        save_chat_id(ksyusha_chat_id)

    bot.send_message(
        message.chat.id,
        "Привет, Ксюш! 🌿\n\nЯ хранитель тёплых слов, наших воспоминаний и маленьких знаков внимания от Саши.\nВыбирай нужный раздел в меню ниже 👇",
        reply_markup=get_main_keyboard(),
    )


@bot.message_handler(commands=["sasha", "admin"])
def show_admin_panel(message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        bot.send_message(message.chat.id, "🔒 Это секретная панель Саши! 🤫")
        return
    user_states.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "👑 *Панель управления Саши*\n\nМожно отправить Ксюше любое сообщение, фото, видео, голосовое, стикер или документ.",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown",
    )

# -------------------------------------------------------------
# ОСНОВНОЙ ОБРАБОТЧИК
# -------------------------------------------------------------
@bot.message_handler(content_types=["text", "sticker", "photo", "voice", "video_note", "document", "animation", "video"])
def handle_all_messages(message):
    global ksyusha_chat_id

    if not check_access(message.from_user):
        bot.send_message(message.chat.id, "🔒 Доступ ограничен.")
        return

    user_id = message.from_user.id
    text = message.text or ""
    state = user_states.get(user_id, {})

    if user_id != YOUR_TELEGRAM_ID and ksyusha_chat_id != message.chat.id:
        ksyusha_chat_id = message.chat.id
        save_chat_id(ksyusha_chat_id)

    if text == "✖️ Отмена":
        user_states.pop(user_id, None)
        keyboard = get_admin_keyboard() if user_id == YOUR_TELEGRAM_ID else get_main_keyboard()
        bot.send_message(message.chat.id, "Действие отменено.", reply_markup=keyboard)
        return

    # Режим отправки от Саши: следующее любое сообщение уйдёт Ксюше.
    if user_id == YOUR_TELEGRAM_ID and state.get("mode") == "send_to_ksyusha":
        forward_from_sasha(message)
        user_states.pop(user_id, None)
        return

    # Ожидание фото или видео для нового воспоминания.
    if state.get("mode") == "memory_media":
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = "photo"
        elif message.video:
            file_id = message.video.file_id
            media_type = "video"
        else:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, отправь именно фотографию или видео. Или нажми «✖️ Отмена».",
                reply_markup=get_cancel_keyboard(),
            )
            return

        # Подпись, добавленная непосредственно к фото/видео, сохраняется сразу.
        if message.caption:
            user_states[user_id] = {
                "mode": "memory_caption",
                "memory": {
                    "file_id": file_id,
                    "media_type": media_type,
                    "author_id": user_id,
                    "author_name": current_author_name(message.from_user),
                },
            }
            save_pending_memory(user_id, message.caption)
            bot.send_message(
                message.chat.id,
                "✅ Воспоминание сохранено с подписью!",
                reply_markup=get_memories_keyboard(),
            )
        else:
            user_states[user_id] = {
                "mode": "memory_caption",
                "memory": {
                    "file_id": file_id,
                    "media_type": media_type,
                    "author_id": user_id,
                    "author_name": current_author_name(message.from_user),
                },
            }
            bot.send_message(
                message.chat.id,
                "🌿 Отлично! Теперь напиши короткую подпись к воспоминанию или выбери «⏭ Без подписи».",
                reply_markup=get_skip_caption_keyboard(),
            )
        return

    # Ожидание подписи к новому воспоминанию.
    if state.get("mode") == "memory_caption":
        if not text:
            bot.send_message(message.chat.id, "Напиши подпись текстом или выбери «⏭ Без подписи».")
            return
        caption = "" if text == "⏭ Без подписи" else text
        save_pending_memory(user_id, caption)
        bot.send_message(
            message.chat.id,
            "✅ Воспоминание сохранено! Теперь оно доступно вам обоим в разделе «Наши воспоминания».",
            reply_markup=get_memories_keyboard(),
        )
        return

    # Ответ Саши на пересланное от Ксюши сообщение.
    if user_id == YOUR_TELEGRAM_ID and message.reply_to_message:
        target_id = get_ksyusha_chat_id()
        if target_id:
            bot.send_message(target_id, "💬 *Саша ответил тебе:*", parse_mode="Markdown")
            bot.copy_message(target_id, message.chat.id, message.message_id)
            bot.send_message(message.chat.id, "✅ Ответ доставлен Ксюше!", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось найти чат Ксюши.")
        return

    # Панель Саши.
    if user_id == YOUR_TELEGRAM_ID:
        if text == "📤 Отправить Ксюше":
            if not get_ksyusha_chat_id():
                bot.send_message(message.chat.id, "⚠️ Ксюша ещё не запускала бота. Сначала ей нужно нажать /start.")
                return
            user_states[user_id] = {"mode": "send_to_ksyusha"}
            bot.send_message(
                message.chat.id,
                "📤 Отправь следующее сообщение Ксюше. Подойдут текст, фото, видео, голосовое, документ, стикер, кружок или анимация.",
                reply_markup=get_cancel_keyboard(),
            )
            return
        if text == "💋 Отправить поцелуй":
            target_id = get_ksyusha_chat_id()
            if target_id:
                bot.send_message(target_id, "💋 *Саша только что прислал тебе внезапный поцелуй прямо посреди дня!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Поцелуй успешно доставлен Ксюше! 😘")
            return
        if text == "☕ Передать заботу":
            target_id = get_ksyusha_chat_id()
            if target_id:
                bot.send_message(target_id, "☕ *Саша заботливо передаёт тебе чашку тёплого чая и обнимает!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Забота доставлена! 🥰")
            return
        if text == "🤗 Обнять в ответ":
            target_id = get_ksyusha_chat_id()
            if target_id:
                bot.send_message(target_id, "🥰 *Саша крепко обнял тебя!*", parse_mode="Markdown")
                bot.send_message(message.chat.id, "Объятие доставлено! ❤️")
            return

    # Главное меню и разделы.
    if text == "💌 Тёплые слова":
        bot.send_message(message.chat.id, "Выбери, что именно ты хочешь прочитать:", reply_markup=get_words_keyboard())
        return
    if text == "❤️ Обнимашки":
        bot.send_message(message.chat.id, "Раздел самых тёплых обнимашек 🤗", reply_markup=get_hugs_keyboard())
        return
    if text == "🎁 Купоны желаний":
        bot.send_message(
            message.chat.id,
            "🎁 *Маленькие купоны желаний*\n\nВыбери купон, который хочешь активировать прямо сейчас, и Саша сразу получит уведомление!",
            reply_markup=get_coupons_inline(),
            parse_mode="Markdown",
        )
        return
    if text == "🖼 Наши воспоминания":
        bot.send_message(
            message.chat.id,
            "🖼 *Наши воспоминания*\n\nЗдесь можно бережно хранить общие фотографии и видео.",
            reply_markup=get_memories_keyboard(),
            parse_mode="Markdown",
        )
        return
    if text == "📸➕ Добавить воспоминание":
        user_states[user_id] = {"mode": "memory_media"}
        bot.send_message(
            message.chat.id,
            "📸 Отправь фотографию или видео, которое хочешь сохранить в нашей галерее. Можно сразу добавить подпись к медиа или написать её следующим сообщением.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    if text == "📚 Смотреть воспоминания":
        send_memory(message.chat.id, 0)
        return
    if text == "⚙️ Настройки и Инфо":
        bot.send_message(message.chat.id, "Настройки и информация:", reply_markup=get_settings_keyboard())
        return
   if text == "🔙 Главное меню":
    user_states.pop(user_id, None)
    bot.send_message(
        message.chat.id,
        "Возвращаемся в главное меню 🌿",
        reply_markup=get_main_keyboard(),
    )
    return

    # Тёплые слова.
    if text == "✨ Комплимент":
        bot.send_message(message.chat.id, f"«{random.choice(COMPLIMENTS)}»")
        return
    if text in ["📖 Цитата", "📖 Романтическая цитата"]:
        bot.send_message(message.chat.id, random.choice(QUOTES))
        return
    if text == "☀️ Пожелание на сегодня":
        bot.send_message(message.chat.id, choose_daily_wish())
        return

    # Обнимашки.
    if text in ["🤗 Обнять Сашу", "❤️ Обнять Сашу"]:
        count = increment_hugs()
        hug_type = random.choice(HUG_TYPES)
        bot.send_message(
            message.chat.id,
            f"Отправлено {hug_type}! 🥰\n\nЭто ваше *{count}-е* объятие в боте!",
            parse_mode="Markdown",
        )
        achievements = {
            25: "🧸 *Достижение разблокировано: Новичок-обнимашка (25 объятий)!*",
            50: "✨ *Достижение разблокировано: Уровень «Уютный пледик» (50 объятий)!*",
            100: "❤️ *Достижение разблокировано: Мастера нежности (100 объятий)!*",
            250: "🔥 *Достижение разблокировано: Профессиональные обнимальщики (250 объятий)!*",
            500: "🏆 *Достижение разблокировано: Абсолютные рекордсмены любви (500 объятий)!*",
        }
        if count in achievements:
            bot.send_message(message.chat.id, achievements[count], parse_mode="Markdown")

        inline_markup = types.InlineKeyboardMarkup(row_width=2)
        inline_markup.add(
            types.InlineKeyboardButton("🥰 Обнять в ответ", callback_data="act_hug"),
            types.InlineKeyboardButton("😘 Поцеловать", callback_data="act_kiss"),
            types.InlineKeyboardButton("💆‍♂️ Погладить", callback_data="act_pat"),
            types.InlineKeyboardButton("😼 Укусить за щёчку", callback_data="act_bite"),
        )
        bot.send_message(
            YOUR_TELEGRAM_ID,
            f"🔔 *Ксюша только что обняла тебя через бота!*\nФормат: _{hug_type}_\n(Всего объятий: {count})",
            reply_markup=inline_markup,
            parse_mode="Markdown",
        )
        return
    if text == "📊 Счётчик объятий":
        bot.send_message(message.chat.id, f"📊 Вы обнялись через бота уже *{get_hugs_count()}* раз! ❤️", parse_mode="Markdown")
        return

    # Настройки.
    if text in ["🔔 Рассылка: Включена ✅", "🔕 Рассылка: Выключена ❌"]:
        new_state = not is_wishes_enabled()
        set_wishes_enabled(new_state)
        status = "включили ✅" if new_state else "поставили на паузу ❌"
        bot.send_message(message.chat.id, f"Утреннюю рассылку пожеланий {status}.", reply_markup=get_settings_keyboard())
        return
    if text == "🗓 Сколько дней мы вместе":
        days_together = (date.today() - RELATIONSHIP_START_DATE).days
        bot.send_message(
            message.chat.id,
            f"🗓 Вы вместе уже *{days_together}* дней! ❤️\nИ каждый из них — особенный.",
            parse_mode="Markdown",
        )
        return
    if text == "ℹ️ О боте":
        info_text = (
            "🌿 *О боте*\n\n"
            "Этот маленький цифровой уголок создан специально для вас — чтобы хранить тепло, воспоминания и маленькие знаки внимания.\n\n"
            "✨ *Что умеет бот:*\n"
            "☀️ *Утренние послания:* каждый день в *11:00 по Москве* приходит новое тёплое пожелание.\n"
            "💌 *Прямой мост:* сообщения от Ксюши мгновенно прилетают Саше, а Саша может отправить ей любой контент через панель /admin.\n"
            "🖼 *Общие воспоминания:* вы оба можете добавлять и смотреть фото и видео.\n"
            "🤗 *Обнимашки:* когда хочется тепла — нажми кнопку, и Саша сразу узнает об этом.\n"
            "🎁 *Купоны:* маленькие приятные желалочки.\n"
            "🗓 *Наша история:* бот считает дни вместе.\n\n"
            "_Сделано с бесконечной любовью специально для Ксюши._ ❤️"
        )
        bot.send_message(message.chat.id, info_text, parse_mode="Markdown")
        return
    if text == "💬 Написать Саше":
        bot.send_message(
            message.chat.id,
            "💌 *Прямая связь с Сашей*\n\nПросто отправь в этот чат любой текст, фото, видео, голосовое сообщение, кружочек, документ или стикер — бот моментально перешлёт это Саше!",
            parse_mode="Markdown",
        )
        return

    # Пересылка обычного контента от Ксюши Саше.
    if user_id != YOUR_TELEGRAM_ID:
        bot.send_message(YOUR_TELEGRAM_ID, "💌 *Сообщение от Ксюши:*", parse_mode="Markdown")
        bot.copy_message(YOUR_TELEGRAM_ID, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "Сообщение доставлено Саше! 📬")

# -------------------------------------------------------------
# INLINE-КНОПКИ
# -------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("use_coupon_"))
def handle_coupon_activation(call):
    if not check_access(call.from_user):
        bot.answer_callback_query(call.id, "Доступ ограничен.")
        return

    coupon_code = call.data.replace("use_coupon_", "")
    coupon_name = COUPONS.get(coupon_code, "Неизвестный купон")
    bot.answer_callback_query(call.id, "Купон активирован!")
    bot.send_message(
        call.message.chat.id,
        f"✅ Ты активировала купон:\n*{coupon_name}*\n\nСаша уже получил уведомление! ❤️",
        parse_mode="Markdown",
    )

    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton("Принять в работу ✅", callback_data="accept_coupon_action"))
    bot.send_message(
        YOUR_TELEGRAM_ID,
        f"🎁 *Ксюша активировала купон!*\n\nНазвание: _{coupon_name}_",
        reply_markup=inline_markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data == "accept_coupon_action")
def handle_accept_coupon(call):
    if call.from_user.id != YOUR_TELEGRAM_ID:
        bot.answer_callback_query(call.id, "Эта кнопка только для Саши.")
        return
    target_id = get_ksyusha_chat_id()
    if target_id:
        bot.send_message(target_id, "🥰 *Саша принял твой купон в работу!*", parse_mode="Markdown")
    bot.answer_callback_query(call.id, "Уведомление отправлено Ксюше!")
    bot.edit_message_text("✅ Ты принял купон!", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("act_"))
def handle_hug_reactions(call):
    if call.from_user.id != YOUR_TELEGRAM_ID:
        bot.answer_callback_query(call.id, "Эта кнопка только для Саши.")
        return
    target_id = get_ksyusha_chat_id()
    text_to_send = REACTION_RESPONSES.get(call.data, "🥰 *Саша передаёт тебе тёплый привет!*")
    if target_id:
        bot.send_message(target_id, text_to_send, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Реакция отправлена Ксюше!")
        clean_text = text_to_send.replace("*", "")
        bot.edit_message_text(f"✅ Ты ответил: {clean_text}", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Ксюша ещё не запускала бота.")


@bot.callback_query_handler(func=lambda call: call.data == "memory_noop")
def handle_memory_noop(call):
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("memory_show_"))
def handle_memory_show(call):
    if not check_access(call.from_user):
        bot.answer_callback_query(call.id, "Доступ ограничен.")
        return
    try:
        index = int(call.data.replace("memory_show_", ""))
    except ValueError:
        bot.answer_callback_query(call.id, "Не удалось открыть воспоминание.")
        return
    bot.answer_callback_query(call.id)
    send_memory(call.message.chat.id, index)


@bot.callback_query_handler(func=lambda call: call.data.startswith("memory_delete_"))
def handle_memory_delete(call):
    if not check_access(call.from_user):
        bot.answer_callback_query(call.id, "Доступ ограничен.")
        return
    try:
        index = int(call.data.replace("memory_delete_", ""))
    except ValueError:
        bot.answer_callback_query(call.id, "Не удалось удалить воспоминание.")
        return

    data = load_bot_data()
    memories = data["memories"]
    if index < 0 or index >= len(memories):
        bot.answer_callback_query(call.id, "Эта запись уже удалена.")
        return

    deleted = memories.pop(index)
    save_bot_data(data)
    bot.answer_callback_query(call.id, "Воспоминание удалено.")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(
        call.message.chat.id,
        f"🗑 Воспоминание от {deleted['author_name']} удалено.",
        reply_markup=get_memories_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "memory_close")
def handle_memory_close(call):
    if not check_access(call.from_user):
        bot.answer_callback_query(call.id, "Доступ ограничен.")
        return
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "Галерея закрыта 🌿", reply_markup=get_memories_keyboard())

# -------------------------------------------------------------
# ЕЖЕДНЕВНАЯ РАССЫЛКА: 11:00 ПО МОСКВЕ
# -------------------------------------------------------------
def send_daily_message():
    if not is_wishes_enabled():
        return
    target_id = get_ksyusha_chat_id()
    if target_id:
        bot.send_message(target_id, choose_daily_wish())


scheduler = BackgroundScheduler(timezone=MSK_TZ)
scheduler.add_job(
    send_daily_message,
    "cron",
    hour=11,
    minute=0,
    id="daily_wish_job",
    replace_existing=True,
)
scheduler.start()

# -------------------------------------------------------------
# WEB-СЕРВЕР ДЛЯ RENDER
# -------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def home():
    return "Бот работает 24/7!"


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("Бот успешно запущен!")
    bot.infinity_polling(skip_pending=True)
