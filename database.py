import sqlite3
from datetime import datetime, timedelta
import config
import pandas as pd

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    def create_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS user_information (user_id int primary_key, user_name varchar(50), "
            "first_name varchar(50), registration_date varchar(50), book_id int, page int)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS statistics (number INTEGER PRIMARY KEY AUTOINCREMENT, date varchar(20), "
            "user_id varchar(5000), new_user int, unique_users int)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS words (word_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id int, "
            "word varchar(50), correct_answers_cnt int)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS books (book_id INTEGER PRIMARY KEY AUTOINCREMENT, title varchar(40), "
            "author varchar(40), page_cnt int, complexity int, upload_date varchar(50))")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS pages (page_id INTEGER PRIMARY KEY AUTOINCREMENT, book_id int, page_number int,"
            "content varchar(9000))")
        conn.commit()
        cur.close()
        conn.close()

    def write_statistics(self, parameter_name, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        count = cur.execute(f"SELECT {parameter_name} FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0]
        count += 1
        cur.execute(f"UPDATE statistics SET {parameter_name}  = %d WHERE date = '%s'" % (count, today_date))
        conn.commit()
        user_id_str = str(cur.execute("SELECT user_id FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0])
        if str(user_id) not in user_id_str:
            user_id_str = str(user_id_str + "n" + str(user_id))
            cur.execute("UPDATE statistics SET user_id = ? WHERE date = ?", (user_id_str, today_date))
            conn.commit()
            unique_users = int(cur.execute("SELECT unique_users FROM statistics WHERE date = '%s'"
                                    % today_date).fetchall()[0][0])
            unique_users += 1
            cur.execute("UPDATE statistics SET unique_users = '%d' WHERE date = '%s'" % (unique_users, today_date))
            conn.commit()
        cur.close()
        conn.close()

    def get_date_str_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT date FROM statistics").fetchall()
        if len(result) > 0:
            result_list = [i[0] for i in result]
        else:
            result_list = []
        cur.close()
        conn.close()
        return result_list

    def write_new_date_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        cur.execute("INSERT INTO statistics (date, user_id, new_user, unique_users) VALUES "
                    "('%s', '%d', '%d', '%d')" % (today_date, 0, 0, 0))
        conn.commit()
        cur.close()
        conn.close()

    def check_new_user(self, user_id):
        # for new user return 1
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM user_information WHERE user_id = '%d'" % user_id).fetchall()
        cur.close()
        conn.close()
        return not bool(len(result))

    def write_new_user(self, message):
        if not self.check_new_user(message.from_user.id):
            return
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        reg_date = (datetime.now()).strftime("%d.%m.%y")
        cur.execute("INSERT INTO user_information (user_id, user_name, first_name, registration_date, book_id, "
                    "page) VALUES ('%d', '%s','%s', '%s', '%d', '%d')" % (message.from_user.id,
                                                                          message.from_user.username,
                                                                          message.from_user.first_name, reg_date,
                                                                          0, 0))
        conn.commit()
        cur.close()
        conn.close()

    def get_user_parameter(self, user_id, parameter_name):
        # return parameter value
        parameters = ["user_name", "first_name", "registration_date", "book_id", "page"]
        parameter_value = 0
        if parameter_name in parameters:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            parameter_value = cur.execute(f"SELECT {parameter_name} FROM user_information WHERE user_id = '%d'"
                                          % user_id).fetchall()[0][0]
            cur.close()
            conn.close()
        return parameter_value

    def get_user_id_list(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        chat_id_tuple = cur.execute(f"SELECT user_id FROM user_information").fetchall()
        chat_id_list = [i1[0] for i1 in chat_id_tuple if i1[0] != 0]
        cur.close()
        conn.close()
        return chat_id_list

    def add_new_book(self, title, author, page_cnt, complexity):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        upload_date = datetime.now().strftime("%d.%m.%y")
        cur.execute(
            "INSERT INTO books (title, author, page_cnt, complexity, upload_date) VALUES (?, ?, ?, ?, ?)",
            (title, author, page_cnt, complexity, upload_date)
        )

        book_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return book_id

    def update_book_complexity_and_page_cnt(self, book_id, complexity, page_cnt):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE books SET complexity = '%d' WHERE book_id = '%s'" % (complexity, book_id))
        cur.execute("UPDATE books SET page_cnt = '%d' WHERE book_id = '%s'" % (page_cnt, book_id))
        conn.commit()
        cur.close()
        conn.close()

    def add_new_page(self, book_id, page_number, content):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pages (book_id, page_number, content) VALUES (?, ?, ?)",
            (book_id, page_number, content)
        )
        conn.commit()
        cur.close()
        conn.close()

    def check_new_book(self, title):
        # for new book return 0
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM books WHERE title = ?", (title,)).fetchall()
        cur.close()
        conn.close()
        book_id = 0
        if len(result) > 0:
            book_id = result[0][0]
        return book_id

    def get_book_information(self, book_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM books WHERE book_id = '%d'" % book_id).fetchall()
        error, book_id, title, author, page_cnt, complexity = 0, 0, 0, 0, 0, 0
        if result:
            book_id, title, author, page_cnt, complexity, date = result[0]
        else:
            error = 1
        cur.close()
        conn.close()
        return error, book_id, title, author, page_cnt, complexity

    def update_user_book(self, user_id, book_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE user_information SET book_id = '%d' WHERE user_id = '%d'" % (book_id, user_id))
        cur.execute("UPDATE user_information SET page = '%d' WHERE user_id = '%s'" % (0, user_id))
        conn.commit()
        cur.close()
        conn.close()

    def get_user_page_text(self, user_id, page_type):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        page_number = cur.execute(f"SELECT page FROM user_information WHERE user_id = '%d'"
                                      % user_id).fetchall()[0][0]
        book_id = cur.execute(f"SELECT book_id FROM user_information WHERE user_id = '%d'"
                                 % user_id).fetchall()[0][0]
        max_book_page_number = cur.execute(f"SELECT page_cnt FROM books WHERE book_id = '%d'"
                                 % book_id).fetchall()[0][0]
        if page_type == 'next':
            if page_number + 1 <= max_book_page_number:
                new_page = page_number + 1
            else:
                new_page = 1
        elif page_type == 'previous':
            if page_number - 1 > 0:
                new_page = page_number - 1
            else:
                new_page = 1
        else:
            new_page = page_number

        cur.execute("UPDATE user_information SET page = '%d' WHERE user_id = '%s'" % (new_page, user_id))
        page_text = cur.execute(f"SELECT content FROM pages WHERE book_id = '%d' AND page_number = '%d'"
                                 % (book_id, new_page)).fetchall()[0][0]
        conn.commit()
        cur.close()
        conn.close()
        return page_text, new_page, max_book_page_number

    def get_book_table(self):
        database = config.database_path
        conn = sqlite3.connect(database)
        script = "SELECT * FROM books"
        df = pd.read_sql_query(script, conn)
        conn.close()
        return df

    def add_new_word(self, user_id, word):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        words_in_db = cur.execute(f"SELECT word FROM words WHERE user_id = '%d'"
                                  % user_id).fetchall()
        words_values = set([row[0] for row in words_in_db])
        if word not in words_values:
            cur.execute(
                "INSERT INTO words (user_id, word, correct_answers_cnt) VALUES (?, ?, ?)",
                (user_id, word, 0)
            )
        conn.commit()
        cur.close()
        conn.close()

    def get_user_words(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        words_in_db = cur.execute(f"SELECT word FROM words WHERE user_id = '%d'"
                                  % user_id).fetchall()
        words_values = [row[0] for row in words_in_db]
        conn.commit()
        cur.close()
        conn.close()
        return words_values

    def add_correct_translate(self, user_id, word):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        correct_answers_cnt = int(cur.execute(f"SELECT correct_answers_cnt FROM words WHERE user_id = ? and word = ?",
                                          (user_id, word)).fetchall()[0][0])
        correct_answers_cnt += 1
        if correct_answers_cnt > config.correct_answers:
            cur.execute("DELETE FROM words WHERE user_id = ? and word = ?", (user_id, word))
        else:
            cur.execute("UPDATE words SET correct_answers_cnt = ? WHERE user_id = ? and word = ?", (correct_answers_cnt,
                                                                                                   user_id, word))
        conn.commit()
        cur.close()
        conn.close()







