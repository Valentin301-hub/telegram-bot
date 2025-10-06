import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
from pathlib import Path

BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_USERNAME = os.environ['CHANNEL_USERNAME']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

bot = telebot.TeleBot(BOT_TOKEN)


def safe_filename(filename):
    try:
        return filename.encode('utf-8', 'ignore').decode('utf-8')
    except:
        return filename


def scan_files_directory(base_path="files"):
    files_structure = {}
    base_path = Path(base_path)

    if not base_path.exists():
        base_path.mkdir()
        return {"Файлы": {"Все файлы": []}}

    has_subfolders = any(item.is_dir() for item in base_path.iterdir())

    if not has_subfolders:
        files = []
        for item in base_path.iterdir():
            if item.is_file():
                try:
                    filename = safe_filename(item.name)
                    files.append(filename)
                except:
                    continue

        files.sort()
        files_structure["Файлы"] = {"Все файлы": files}

    else:
        for category_dir in base_path.iterdir():
            if category_dir.is_dir():
                try:
                    category_name = safe_filename(category_dir.name)
                    files_structure[category_name] = {}

                    has_subcategories = any(item.is_dir() for item in category_dir.iterdir())

                    if not has_subcategories:
                        files = []
                        for item in category_dir.iterdir():
                            if item.is_file():
                                try:
                                    filename = safe_filename(item.name)
                                    files.append(filename)
                                except:
                                    continue

                        files.sort()
                        files_structure[category_name]["Файлы"] = files

                    else:
                        for subcategory_dir in category_dir.iterdir():
                            if subcategory_dir.is_dir():
                                try:
                                    subcategory_name = safe_filename(subcategory_dir.name)
                                    files = []

                                    for file_path in subcategory_dir.iterdir():
                                        if file_path.is_file():
                                            try:
                                                filename = safe_filename(file_path.name)
                                                files.append(filename)
                                            except:
                                                continue

                                    files.sort()
                                    files_structure[category_name][subcategory_name] = files

                                except:
                                    continue

                except:
                    continue

    if not files_structure:
        files_structure = {"Файлы": {"Все файлы": []}}

    return files_structure


def get_file_path(category, subcategory, filename):
    try:
        path = Path("files") / category / subcategory / filename
        if path.exists():
            return path

        if category == "Файлы" and subcategory == "Все файлы":
            path = Path("files") / filename
            if path.exists():
                return path

        category_dir = Path("files") / category
        if category_dir.exists():
            if subcategory == "Файлы" or subcategory == "Все файлы":
                for file in category_dir.iterdir():
                    if file.is_file() and file.name.lower() == filename.lower():
                        return file
            else:
                for sub_dir in category_dir.iterdir():
                    if sub_dir.is_dir() and sub_dir.name.lower() == subcategory.lower():
                        for file in sub_dir.iterdir():
                            if file.is_file() and file.name.lower() == filename.lower():
                                return file

        return None
    except:
        return None


def count_total_files():
    total = 0
    for category in FILES.values():
        for subcategory_files in category.values():
            total += len(subcategory_files)
    return total


def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ['creator', 'administrator', 'member']
    except:
        return False


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        show_main_categories(message.chat.id)
    else:
        show_subscription_request(message.chat.id)


def show_subscription_request(chat_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    keyboard.add(InlineKeyboardButton("✅ Проверить подписку", callback_data='check_subscription'))

    bot.send_message(
        chat_id,
        f"📚 Для доступа к библиотеке Бэймакса из {count_total_files()} файлов подпишитесь на {CHANNEL_USERNAME}",
        reply_markup=keyboard
    )


def show_main_categories(chat_id, message_id=None):
    if not FILES:
        bot.send_message(chat_id, "❌ Файлы не найдены.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []

    for category in sorted(FILES.keys()):
        total_files = sum(len(files) for files in FILES[category].values())
        buttons.append(InlineKeyboardButton(
            f"{get_emoji(category)} {category} ({total_files})",
            callback_data=f"cat_{category}"
        ))

    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.add(buttons[i], buttons[i + 1])
        else:
            keyboard.add(buttons[i])

    keyboard.add(InlineKeyboardButton("🔄 Обновить список", callback_data="refresh_files"))

    text = f"📚 **Добро пожаловать в файловую библиотеку Бэймакса и проекта BAUMAN BRATSTVO!**\n\nВсего файлов: {count_total_files()}\nВыберите категорию:"

    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')


def show_subcategories(chat_id, category, message_id):
    if category not in FILES:
        bot.edit_message_text("❌ Категория не найдена", chat_id, message_id)
        return

    keyboard = InlineKeyboardMarkup()

    for subcategory in sorted(FILES[category].keys()):
        file_count = len(FILES[category][subcategory])
        keyboard.add(InlineKeyboardButton(
            f"📁 {subcategory} ({file_count})",
            callback_data=f"sub_{category}|{subcategory}|0"
        ))

    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))

    bot.edit_message_text(
        f"📂 **{category}**\nВыберите подкатегорию:",
        chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown'
    )


def show_files_page(chat_id, category, subcategory, page, message_id):
    if (category not in FILES or
            subcategory not in FILES[category] or
            not FILES[category][subcategory]):
        bot.edit_message_text("❌ Файлы не найдены", chat_id, message_id)
        return

    files = FILES[category][subcategory]
    items_per_page = 8
    total_pages = max(1, (len(files) + items_per_page - 1) // items_per_page)
    page = min(page, total_pages - 1)

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(files))

    keyboard = InlineKeyboardMarkup()

    for i in range(start_idx, end_idx):
        file_name = files[i]
        file_path = get_file_path(category, subcategory, file_name)
        file_size = get_file_size(file_path) if file_path else "?"

        button_text = f"📄 {truncate_filename(file_name, 30)}"
        if file_size:
            button_text += f" ({file_size})"

        keyboard.add(InlineKeyboardButton(button_text, callback_data=f"file_{category}|{subcategory}|{i}"))

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"sub_{category}|{subcategory}|{page - 1}"))

        nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="no_action"))

        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"sub_{category}|{subcategory}|{page + 1}"))

        keyboard.row(*nav_buttons)

    keyboard.add(InlineKeyboardButton("◀️ К подкатегориям", callback_data=f"cat_{category}"))
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))

    bot.edit_message_text(
        f"📂 **{category}** → **{subcategory}**\n"
        f"Страница {page + 1} из {total_pages}\n"
        f"Файлы {start_idx + 1}-{end_idx} из {len(files)}",
        chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown'
    )


def truncate_filename(filename, max_length):
    if len(filename) <= max_length:
        return filename
    name, ext = os.path.splitext(filename)
    return name[:max_length - len(ext) - 3] + "..." + ext


def get_file_size(file_path):
    if file_path and file_path.exists():
        try:
            size = file_path.stat().st_size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except:
            pass
    return None


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id

    try:
        if call.data == 'check_subscription':
            if check_subscription(user_id):
                show_main_categories(chat_id, message_id)
            else:
                bot.answer_callback_query(call.id, "❌ Вы еще не подписались!", show_alert=True)

        elif call.data == 'refresh_files':
            global FILES
            FILES = scan_files_directory()
            bot.answer_callback_query(call.id, f"✅ Обновлено! Файлов: {count_total_files()}")
            show_main_categories(chat_id, message_id)

        elif call.data == 'back_to_main':
            show_main_categories(chat_id, message_id)

        elif call.data == 'no_action':
            bot.answer_callback_query(call.id)

        elif call.data.startswith('cat_'):
            category = call.data[4:]
            show_subcategories(chat_id, category, message_id)

        elif call.data.startswith('sub_'):
            data_parts = call.data[4:].split('|')

            if len(data_parts) >= 3:
                category = data_parts[0]
                subcategory = data_parts[1]
                page = data_parts[2]
            else:
                category = data_parts[0] if len(data_parts) > 0 else ""
                subcategory = data_parts[1] if len(data_parts) > 1 else ""
                page = 0

            show_files_page(chat_id, category, subcategory, int(page), message_id)

        elif call.data.startswith('file_'):
            if check_subscription(user_id):
                data_parts = call.data[5:].split('|')

                if len(data_parts) >= 3:
                    category = data_parts[0]
                    subcategory = data_parts[1]
                    file_idx = data_parts[2]
                else:
                    category = data_parts[0] if len(data_parts) > 0 else ""
                    subcategory = data_parts[1] if len(data_parts) > 1 else ""
                    file_idx = 0

                file_idx = int(file_idx)

                if (category in FILES and
                        subcategory in FILES[category] and
                        file_idx < len(FILES[category][subcategory])):

                    file_name = FILES[category][subcategory][file_idx]
                    file_path = get_file_path(category, subcategory, file_name)

                    if file_path and file_path.exists():
                        try:
                            bot.answer_callback_query(call.id, "⏳ Отправляю файл...")

                            with open(file_path, 'rb') as file:
                                bot.send_document(chat_id, file, caption=f"📄 {file_name}")

                        except Exception as e:
                            bot.answer_callback_query(call.id, "❌ Ошибка отправки файла!", show_alert=True)
                    else:
                        bot.answer_callback_query(call.id, "❌ Файл не найден!", show_alert=True)
                else:
                    bot.answer_callback_query(call.id, "❌ Файл не найден!", show_alert=True)
            else:
                show_subscription_request(chat_id)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Произошла ошибка!", show_alert=True)


def get_emoji(category):
    emojis = {
        "Файлы": "📁", "Книги": "📚", "Презентации": "📊", "Архивы": "🗂️",
        "Видео": "🎬", "Аудио": "🎵", "Изображения": "🖼️",
        "Документы": "📄", "Таблицы": "📋", "Программы": "⚙️",
        "Музыка": "🎵", "Фото": "🖼️", "Тексты": "📝"
    }
    return emojis.get(category, "📁")


# Загружаем файлы при старте
FILES = scan_files_directory()

print("🤖 Бот запущен...")
bot.infinity_polling()
