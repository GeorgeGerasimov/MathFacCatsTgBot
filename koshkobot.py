# -*- coding: utf-8 -*-
import os
import json
import random
#from dotenv import load_dotenv
from google import genai
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from pathlib import Path
filepath = Path(__file__).parent / "cats_db.json"


BOT_TOKEN = 'BOTTOKEN'
CHANNEL_NAME = "@mathfaccats"

MODEL = "gemini-3.1-flash-lite-preview"
client = genai.Client(api_key = "APIKEY")


COLOR_OPTIONS = [
    ["orange", "black", "white"],
    ["grey", "brown", "mixed"]
]

def load_cats_db():
    """Загрузка базы данных из JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    except Exception as e:
        print(f"Ошибка базы данных: {e}")
        return []


def extract_cat_traits(user_message: str) -> dict:
    prompt = f"""
    Пользователь просит тебя прислать ему кота, возможно с какими то уточнениями или наоборот недоговорками.
    Извлеки нужные характеристики кота из текстового запроса пользователя.
    
    Верни СТРОГО JSON формат со СТРОГО такими полями:
    - "color": ОДИН из ["orange", "black", "white", "grey", "brown", "mixed"]
    - "size": ОДИН из ["small", "medium","fat" ,"big"]
    - "name": ОДИН из ["Не предоставлено", "Нет совпадений", "Сеня", "сёма", "Мурзайка", "СтепанГригорьевичБорзый", "Дуся", "Барин", "Манюня", "Маруся", "Шерлок", "Царапка", "Петр", "Кишка", "Алиса", "Кискимо", "Кыся", "Мия", "каспер", "Ляля", "Лютик", "Амур", "Лима", "Венечка", "Нюша", "Руни", "Тимофей"]
    
    Если нет точного совпадения с предоставленными характеристиками, выбери наиболее подходящую по смыслу
        
    Если не в запросе не уточнен цвет, то выбери один случайный цвет из списка ["orange", "black", "white", "grey", "brown", "mixed"]
    
    Под значение "small" для ключа "size" подпадают только котята или маленькие кошки (или синонимичные)
    "medium" это стандартное значение для ключа "size", т.е. если размер в запросе не уточнен, то "size" нужно ставить "medium"
        
    Если пользователь попросил прислать кота по имени, или просто написал имя, то попробуй найти это имя в списке значений для ключа "name", и выбери его
    Если тебе не удалось найти имя в списке, то для ключа "name" выбери значение "Нет совпадений"
    Если пользователь вообще не уточнял имени в запросе, то для ключа "name" выбери значение "Не предоставлено"
    
    Сообщение пользователя: "{user_message}"
    
    Верни СТРОГО JSON формат со СТРОГО теми полями, которые были предоставлены выше, без пояснений, без markdown, без backtick.
    """
    
    response = client.models.generate_content(
    model=MODEL,
    contents=prompt
    )
    text = response.text.strip()
    return json.loads(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и вывод кнопок выбора цвета"""
    await update.message.reply_text("Привет! Напишите мне какую кошекчку вы хотите!\n\nХотя я ограничен в функциональности, и смогу передать только цвет и размер :)\n\nА еще я могу обрабатывать только ~15 запросов в минуту от всех пользователей, так что не печальтесь, если я не смогу присылать котиков некоторое время!...")

async def handle_color_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора цвета пользователем"""
    user_text = update.message.text
    

    all_colors = [color for sublist in COLOR_OPTIONS for color in sublist]    
    
    cat_traits = []
    
    try:
        cat_traits = extract_cat_traits(user_text)
    except Exception as e:
        print(f"[-] Ошибка нейронки: {e}")
        await update.message.reply_text("Извините, я не смог обработать запрос, временной лимит использования нейросети автора бота был исчерпан!... :(\n\nПопробуйте повторить запрос через минуту!")
        print(cat_traits)
        return
        
    
    selected_color = cat_traits["color"]
    selected_size = cat_traits["size"]
    selected_name = cat_traits["name"]
    
    chosen_cat = [] #будет уточнен дальше

    no_such_size = False #есть ли кошечка подходящего размера с выбранным цветом
    
    no_avaible_name = (selected_name == "Не предоставлено" or selected_name == "Нет совпадений")
    no_name_chosen = (selected_name == "Не предоставлено")

    print(f"[*] Пользователь выбрал цвет: {selected_color}")
    print(f"[*] Пользователь выбрал размер: {selected_size}")
    print(f"[*] Пользователь выбрал имя: {selected_name}")


    cats = load_cats_db()
    
    # Если уточнено имя кота, то выполняется этот скрипт
    if not no_name_chosen:
        if no_avaible_name:
            await update.message.reply_text("Извините, но я не смог найти такого котика в канале! :(")
            return
        else:
            for cat in cats:
                if cat["name"] == selected_name:
                    chosen_cat = cat
                    break
    
    # Если имя кота не нашлось или не было предоставлено, то идет стандартный выбор кота по размеру и цвету
    if not chosen_cat:
        candidates = [cat for cat in cats if cat.get('color') == selected_color and cat.get('size') == selected_size]

        # По цвету точно найдется хоть какой то котик
        if not candidates:
            candidates = [cat for cat in cats if cat.get('color') == selected_color]
            no_such_size = True
        
        chosen_cat = random.choice(candidates)


    # тут идет выбор поста с уже выбарнным котом и его дальнейшая пересылка пользователю
    if chosen_cat:
        post_id = random.choice(chosen_cat['ids'])
        
        try:
            if no_such_size:
                await update.message.reply_text(f"Извините, но у нас не было именно такой кошечки, поэтому мы пришлем немного другую!...\n\nВстречайте! Котик {chosen_cat['name']}!")
            else:
                await update.message.reply_text(f"Встречайте! Котик {chosen_cat['name']}!")
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_NAME,
                message_id=post_id
            )
            print(f"[+] Отправлен пост {post_id} (цвет: {selected_color})")

            await update.message.reply_text("Пишите если хотите еще кошечек!")
            
        except Exception as e:
            print(f"[-] Ошибка копирования: {e}")
            await update.message.reply_text(f"Нашел котика {chosen_cat['name']}, но не смог переслать фото...")
    else:
        await update.message.reply_text(
            f"Такого котика пока нет в базе! :( \n\nПопробуйте другой запрос",
        )

if __name__ == "__main__":    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_color_selection))
    
    print("Бот запущен")
    application.run_polling()