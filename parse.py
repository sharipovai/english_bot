from langdetect import detect
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import xml.etree.ElementTree as ET

import config
from database import Database

# import nltk
# nltk.download('punkt_tab')
# nltk.download('stopwords')

def verify_book(content, ns):
    verify_error = 0
    try:
        root = ET.fromstring(content)
        body = root.find('.//fb:body', ns)
        paragraphs = body.findall('.//fb:p', ns)
        book_text = "".join(p.text for p in paragraphs[10:100] if p.text)
        language = detect(book_text)
        if language not in ['ru', 'en', 'fr']:
            verify_error = 1
    except Exception:
        verify_error = 1
    return  verify_error


def extract_text(element):
    texts = []

    # Получаем текст непосредственно в текущем элементе
    if element.text:
        texts.append(element.text)

    # Обрабатываем все дочерние элементы
    for child in element:
        # Добавляем текст после текущего элемента, если он есть
        if child.tag.endswith("p") or child.tag.endswith("subtitle"):
            texts.append("\n")
        elif child.tag.endswith("title"):
            texts.append("\n\n")

        # Рекурсивно обрабатываем дочерние элементы
        texts.extend(extract_text(child))

        # Добавляем текст после дочернего элемента
        if child.tail:
            texts.append(child.tail)

    return texts


def add_book_info(db, book_id, page_cnt, book_text):
    language = detect(book_text)
    error = 0
    # Словари для обработки разных языков
    language_dict = {
        'ru': 'russian',
        'fr': 'french',
        'en': 'english',
    }
    text = book_text.lower()
    tokenized_text = [
        i for i in word_tokenize(text, 'russian')
        if i not in stopwords.words(language_dict[language]) and i.isalpha()  # Убираем не буквенные символы
    ]

    stemmer = SnowballStemmer(language=language_dict[language])
    stemmed_words = [stemmer.stem(word) for word in tokenized_text]
    complexity = len(set(stemmed_words))
    db.update_book_complexity_and_page_cnt(book_id, complexity, page_cnt)

    return error

def parse_new_book(content):
    ns = {'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0'}
    if verify_book(content, ns) == 1:
        return 0
    root = ET.fromstring(content)
    book_title = root.find('.//fb:book-title', ns).text
    author = root.find('.//fb:first-name', ns).text + " " + root.find('.//fb:last-name', ns).text
    body = root.find('.//fb:body', ns)
    db = Database(config.database_path)
    book_id = db.check_new_book(book_title)
    if book_id != 0:
        return book_id
    book_text = ""
    book_id = db.add_new_book(book_title, author, 0, 0)
    chapter_len = 0
    page_cnt = 0
    chapter_text = ""
    for section in body.findall('.//fb:section', ns):
        ext_text = "".join(extract_text(section))
        title_ext = ext_text.split("\n\n")

        for title in title_ext:
            ext_text = title.split("\n")

            for ext in ext_text:
                section_len = len(ext)
                chapter_len += section_len
                if chapter_len > config.book_char_cnt_per_message and len(chapter_text) > 100:
                    page_cnt += 1
                    chapter_text = chapter_text.strip().strip("\n")
                    db.add_new_page(book_id, page_cnt, chapter_text)
                    book_text += chapter_text
                    chapter_text = ""
                    chapter_len = section_len
                chapter_text = chapter_text + ext
                if len(ext)>0:
                    chapter_text += '\n'
            chapter_text = chapter_text.strip().strip("\n")
            if len(chapter_text) > 0:
                page_cnt += 1
                db.add_new_page(book_id, page_cnt, chapter_text)
                book_text += chapter_text
                chapter_text = ""
                chapter_len = 0
    add_book_info(db, book_id, page_cnt, book_text)
    return book_id



# book_path = "/home/user/Documents/school21/python/english_bot/Rouling_Harry_Potter_1_Harry_Potter_and_the_Sorcerer_s_Stone_172165.fb2"
# with open(book_path, 'rb') as file:
#     fb2_content = file.read()
# error = parse_new_book(fb2_content)
# if error == 1:

#     print("книга уже заведена!")