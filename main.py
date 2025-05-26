import random

from telebot import types
import telebot

from database import *
from statistics import get_stat
import chardet
import io
from parse import parse_new_book
import google.generativeai as genai
from langdetect import detect


genai.configure(api_key=config.api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

db = Database(config.database_path)
bot_token = config.prod_bot_token
bot = telebot.TeleBot(bot_token)

CHAT_BY_DATETIME = dict()
LAST_QUERY = datetime.now()
QUERY_COUNT = 0

def check_query_cnt():
    error = 0
    global LAST_QUERY
    global QUERY_COUNT
    current_time = datetime.now()
    delta_seconds = (current_time - LAST_QUERY).total_seconds()
    if QUERY_COUNT > 14 and delta_seconds < 60:
        error = 1
    elif delta_seconds > 60:
        LAST_QUERY = current_time
        QUERY_COUNT = 1
    else:
        QUERY_COUNT += 1
    return error

def check_time(message):
    current_time = datetime.now()
    error = 0
    last_datetime = CHAT_BY_DATETIME.get(message.chat.id)
    if not last_datetime:
        CHAT_BY_DATETIME[message.chat.id] = current_time
    else:
        delta_seconds = (current_time - last_datetime).total_seconds()
        CHAT_BY_DATETIME[message.chat.id] = current_time
        if delta_seconds < 2:
            error = 1
    return error

def write_statistics(statistics_type, user_id):
    now = datetime.now().strftime("%d.%m.%y")
    date_list = db.get_date_str_statistics()
    if now not in date_list:
        db.write_new_date_statistics()
    db.write_statistics(statistics_type, user_id)


@bot.message_handler(commands=['start'])
def start(message):
    # db.create_db()
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!')
    if db.check_new_user(message.from_user.id):
        db.write_new_user(message)
        write_statistics("new_user", message.from_user.id)
        bot.send_message(message.chat.id, f'{config.hello_message}')
    return wait_command(message)


@bot.message_handler(commands=['stat'])
def stat(message):
    if message.from_user.id == config.admin_tg_id:
        cnt = get_stat()
        bot.send_message(message.chat.id, f'Всего пользователей {cnt}')
        bot.register_next_step_handler(message, stat_step2)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn1 = types.KeyboardButton('Да')
        btn2 = types.KeyboardButton('Нет')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, f'Хотите получить полную статистику по боту?', reply_markup=markup)


def stat_step2(message):
    if 'да' in message.text.lower():
        with open("./statistics.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
        with open("./users_information.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
        with open("./payments.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
    return wait_command(message, 0)


@bot.message_handler(commands=['newsletter'])
def newsletter(message):
    if message.from_user.id == config.admin_tg_id:
        bot.send_message(message.chat.id, f'Введи текст рассылки!')
        bot.register_next_step_handler(message, newsletter_step2)


def newsletter_step2(message):
    text = message.text
    chat_id_list = db.get_user_id_list()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Сделать рассылку')
    btn2 = types.KeyboardButton('Отмена')
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, f'Количество получателей: {len(chat_id_list)}. Им будет направлена следующая рассылка:\n{text}', reply_markup=markup)
    bot.register_next_step_handler(message, newsletter_step3, chat_id_list, text)


def newsletter_step3(message, chat_id_list, text):
    if 'сделать рассылку' in message.text.lower():
        if len(chat_id_list) > 0:
            for chat_id in chat_id_list:
                try:
                    bot.send_message(chat_id, text)
                except Exception as e:
                    print("Произошла ошибка:", e)
        else:
            bot.send_message(message.chat.id, f'Отсутствуют получатели, рассылка невозможна')
    elif message.text.lower() != "отмена":
        bot.send_message(message.chat.id, f'Неизвестная команда')
    return wait_command(message)


def wait_command(message):
    book_id = db.get_user_parameter(message.from_user.id, 'book_id')
    words_values = db.get_user_words(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(f'Загрузить книгу')
    btn2 = types.KeyboardButton('Начать читать')
    markup.row(btn1, btn2)
    if book_id != 0:
        btn3 = types.KeyboardButton('Продолжить чтение')
        markup.row(btn3)
        if len(words_values) > 0:
            btn4 = types.KeyboardButton('Тренировка')
            markup.row(btn4)
    bot.send_message(message.chat.id, f'Выбери команду\n', reply_markup=markup)
    bot.register_next_step_handler(message, info)

def print_all_books_info(message):
    df = db.get_book_table()
    text = ""
    for index, row in df.iterrows():
        text += "№ = " + str(row['book_id']) + " Автор: " + row['author'] + " Название: " + row['title'] + \
                " Страниц: " + str(row['page_cnt']) + " Сложность: " + str(row['complexity']) + "\n\n"
    bot.send_message(message.chat.id, '<b>Наша библиотека</b>\n', parse_mode='html')
    chars_cnt_per_message = 4000
    i = 0
    while len(text) > i*chars_cnt_per_message:
        bot.send_message(message.chat.id, f'{text[i*chars_cnt_per_message:(i+1)*chars_cnt_per_message]}')
        i += 1


@bot.message_handler()
def info(message):
    if message.text is None:
        return wait_command(message)
    elif message.text.lower() == '/start':
        return start(message)
    elif message.text.lower() == '/newsletter':
        return newsletter(message)
    elif message.text.lower() == '/stat':
        return stat(message)
    elif message.text.lower() == 'начать читать':
        print_all_books_info(message)
        bot.send_message(message.chat.id, 'Напишите № книги из библиотеки')
        return bot.register_next_step_handler(message, check_book_id)
    elif message.text.lower() == 'продолжить чтение':
        return reading(message)
    elif message.text.lower() == 'тренировка':
        return train(message)
    elif message.text.lower() == 'загрузить книгу':
        bot.send_message(message.chat.id, 'Отправьте книгу боту в формате fb2')
        return bot.register_next_step_handler(message, add_book)
    else:
        bot.send_message(message.chat.id, '<b>Я пока не знаю такой команды</b>', parse_mode='html')
        return wait_command(message)

def get_book_info(message, book_id):
    bot.send_message(message.chat.id, f"Получение информации о книге № {book_id}")
    if not str(book_id).isdigit():
        bot.send_message(message.chat.id, f"Неверный формат № книги, должно быть число!")
        return 1
    error, book_id, title, author, page_cnt, complexity = db.get_book_information(int(book_id))
    if error == 0:
        bot.send_message(message.chat.id, f"№ {book_id}, название: {title}, автор: {author}, количество страниц: {page_cnt}, "
                              f"сложность (количество уникальных слов): {complexity}")
    else:
        bot.send_message(message.chat.id, f"Книга № {book_id} не найдена")
    return error

def add_book(message):
    file_info = bot.get_file(message.document.file_id)  # Получаем информацию о файле
    downloaded_file = bot.download_file(file_info.file_path)  # Скачиваем файл
    file_name = message.document.file_name.lower()

    if file_name.endswith(".fb2"):  # Если это FB2
        bot.send_message(message.chat.id, 'Подождите...')
        file_like_object = io.BytesIO(downloaded_file)
        raw_data = file_like_object.getvalue()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        content = raw_data.decode(encoding)
        # content = file_like_object.getvalue().decode('utf-8')
        book_id = parse_new_book(content)
        if book_id == 0:
            bot.reply_to(message, "Ошибка при обработке FB2. Возможно, файл поврежден.")
        else:
            bot.reply_to(message, f"Успешно! Книга загружена в библиотеку, id = {book_id}")
            error = get_book_info(message, book_id)

    else:
        bot.reply_to(message, "Этот формат не поддерживается!")
    return wait_command(message)

def check_book_id(message):
    if message.text is None:
        return wait_command(message)
    book_id = message.text
    error = get_book_info(message, book_id)
    if error == 1:
        return wait_command(message)
    db.update_user_book(message.from_user.id, int(book_id))
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(f'Читать')
    btn2 = types.KeyboardButton('Отмена')
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, f'Выбери команду\n', reply_markup=markup)
    bot.register_next_step_handler(message, reading)


def reading(message, page_text=""):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(f'Назад')
    btn2 = types.KeyboardButton(f'Дальше')
    markup.row(btn1, btn2)
    if check_time(message) == 1:
        return bot.register_next_step_handler(message, reading)
    if message.text is None or message.text.lower() == 'отмена':
        return wait_command(message)
    elif message.text.lower() == '/start':
        return start(message)
    elif message.text.lower() in {'читать', 'дальше', 'продолжить чтение', 'назад'}:
        if message.text.lower() == 'назад':
            page_text, new_page, max_book_page_number = db.get_user_page_text(message.from_user.id, page_type='previous')
        elif message.text.lower() in {'дальше', 'читать'}:
            page_text, new_page, max_book_page_number = db.get_user_page_text(message.from_user.id, page_type='next')
        else:
            page_text, new_page, max_book_page_number = db.get_user_page_text(message.from_user.id, page_type='current')
        bot.send_message(message.chat.id, f'{page_text}\n{new_page}\\{max_book_page_number}', reply_markup=markup)

    else:
        translating(message, page_text, markup)
    bot.register_next_step_handler(message, reading, page_text)

def translating(message, page_text, markup):
    word = message.text
    language = detect(page_text)
    if language not in ['en', 'fr']:
        bot.send_message(message.chat.id, f'Переводится только текст на английском и французском языках!',
                         parse_mode='html', reply_markup=markup)
        return 0
    sentence = ""
    for sen in page_text.split("."):
        if word.lower() in sen.lower():
            sentence = sen
            break
    if sentence != "":
        if check_query_cnt() == 1:
            bot.send_message(message.chat.id, 'Достигнут лимит запросов, попробуйте позже')
        else:
            wait_mes = bot.send_message(message.chat.id, 'Уже перевожу, подождите несколько секунд...')
            db.add_new_word(message.from_user.id, word)
            answer = get_translate(word, sentence)
            bot.delete_message(message.chat.id, wait_mes.id)
            bot.send_message(message.chat.id, f'{answer}', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f'Слово <b>{word}</b> не найдено на данной странице книги!',
                         parse_mode='html', reply_markup=markup)


def get_translate(word, sentence):
    response = model.generate_content(f"Пожалуйста переведи на русский язык значение следующей фразы: {word} в "
                                      f"контексте следующего предложения: {sentence}")
    answer = response.text
    return answer


def train(message):
    words_values = db.get_user_words(message.from_user.id)
    if len(words_values) == 0:
        bot.send_message(message.chat.id, f'У вас нет слов для тренировок! Чтобы добавить их, начните читать книгу и '
                                          f'переведите непонятные для вас слова с помощью бота. Они '
                                          f'автоматически добавятся вам в тренировку. После {config.correct_answers} '
                                          f'правильных ответов добавленное слово пропадет из тренировки.')
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton(f'Отмена')
        markup.row(btn1)
        rand_word = random.choice(words_values)
        bot.send_message(message.chat.id, f'Напиши перевод слова <b>{rand_word}</b>', parse_mode='html',
                         reply_markup=markup)
        bot.register_next_step_handler(message, train_step2, rand_word)


def train_step2(message, rand_word):
    if check_time(message) == 1:
        return train(message)
    if message.text is None or message.text.lower() == 'отмена':
        return wait_command(message)
    elif message.text.lower() == '/start':
        return start(message)
    user_translate = message.text
    response = model.generate_content(f"Верно ли следующее утверждение: перевод на русский язык значения фразы:"
                                      f" {rand_word} это: {user_translate}, ответь коротко 'да' или 'нет'")
    answer = response.text
    if 'да' in answer.lower():
        bot.send_message(message.chat.id, 'Верно!')
        db.add_correct_translate(message.from_user.id, rand_word)
    else:
        response = model.generate_content(f"Пожалуйста переведи на русский язык значение следующей фразы: {rand_word}")
        answer = response.text
        bot.send_message(message.chat.id, f'Не верно!\n{answer}')
    return train(message)

bot.infinity_polling()