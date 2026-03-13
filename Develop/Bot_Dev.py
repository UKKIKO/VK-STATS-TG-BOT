import sqlite3
import vk_api
from telebot import TeleBot
import db_utils
import logging
import pandas as pd
import threading
import re
from vk_fetcher import get_stat
from config import VK_ACCESS_TOKEN, TG_ACCESS_TOKEN

logger = logging.getLogger(__name__)

def run_in_thread(func):
    def wrapper(*args, **kwargs):
        def worker():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в потоке (команда {func.__name__}): {e}", exc_info=True)

        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
    return wrapper

bot = TeleBot(token=TG_ACCESS_TOKEN)
vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
vk = vk_session.get_api()

CATEGORIES = ('IT', 'Мемы', 'Новости', 'Искусство')
BOT_MESSAGES = {"Welcome": "Этот бот выводит статистику указанной группы вконтакте.\n "
                                      "Для получения инструкции напишите: /help",
                "Help": "Для простой статистики по последним пяти постам введите:\n"
                                     "/simple (краткое имя группы)\n"
                                     "Для вывода коэффициента вовлечённости и лучшего поста из "
                                     "последних пяти, напишите:\n"
                                     "/complex (краткое имя группы)\n"
                                     "Для добавления своей группы в список отслеживаемых, напишите:\n"
                                     "/add (краткое имя группы) (категория группы)\n"
                                     "Категории: Мемы, IT, Новости, Искусство\n"
                                     "Для получения информации о отслеживаемой группе напишите:\n"
                                     "/info (краткое имя группы)\n"
                                     "Для удаления группы из отслеживаемых напишите:\n"
                                     "/delete (краткое имя группы)",
                "Warning_IncorrectDomain": "Пожалуйста укажите имя группы правильно! "
                                           "(Без спецсимволов и кириллицы) \nПример: "
                                           "/simple apiclub",
                "Warning_NotStatsList": "Не удалось получить данные. "
                                          "Проверьте имя группы и открыта ли она",
                "SimpleStats_line": "{i} - Статистика по посту за {date}: просмотры - {views}," 
                                    "лайки - {likes}, комментарии - {comments}, репосты - {reposts}",
                "ComplexStats_line": "Средний ER (Уровень вовлечённости) группы: {avg_er:.2f}%\n\n "
                                      "Лучший пост: дата - {date}, просмотры - {views}, "
                                      "лайки - {likes}, комментарии - {comments}, репосты - {reposts}",
                "Warning_NotCategory": "Введите категорию!\n"
                                          "Пример: /add apiclub IT\n"
                                          "Категории: {Categories}",
                "Warning_IncorrectCategory": "Неверная категория!\n"
                                          "Категории: {Categories}",
                "AddedToWatchlist": "Группа добавлена в отслеживаемые!",
                "AlreadyInWatchlist": "Эта группа уже отслеживается!",
                "Warning_NotInWatchlist": "Эта группа не в списке отслеживаемых!",
                "InfoGroup_line": "Группа {domain} \nКатегория - {category} \nПодписчики - {members} \n"
                                         "Отслеживается с {added}",
                "Warning_NotRows": "Ничего не найдено!",
                "ListGroup_line": "{i}. {domain} - {category} - {members} подписчиков",
                "DeletedFromWatchlist": "Группа успешно удалена из отслеживания!",
                "Processing": "Загружаю данные, это займет пару секунд...",
                "ThreadError": "Произошла ошибка при обработке запроса",
                "DeleteGroupError": "Произошла ошибка при попытке удалить группу из списка"
                }

def init_db():
    conn = db_utils.db_connect()
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            domain TEXT UNIQUE, 
            category TEXT CHECK(category IN {CATEGORIES}), 
            members INTEGER, 
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER, 
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            post_date TEXT,
            domain TEXT, 
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            reposts INTEGER,
            members INTEGER,
            UNIQUE(domain, post_id))
        ''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована!")

def main():

    try:
        response = vk.users.get()

        user_id = response[0]["id"]
        first_name = response[0]["first_name"]
        logger.info(f"Успешное подключение к вк! Здравствуйте, {first_name} (ID: {user_id})")
        init_db()

    except vk_api.exceptions.ApiError as e:
        logger.error(f"Ошибка API: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}", exc_info=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='bot.log', filemode='a', encoding='utf-8'
    )

def get_valid_domain(message):
    args = get_command_args(message)
    if not args:
        return None
    domain = args[0]
    pattern = r"^[a-zA-Z0-9_.]+$"
    if not re.match(pattern, domain):
        return None

    return domain

def get_valid_category(message, index=0):
    args = get_command_args(message)
    if len(args) <= index:
        return None
    category = args[index]
    if category not in CATEGORIES:
        return None
    return category

def get_command_args(message):
    args = message.text.split()
    clean_args = [arg.replace("@", "") for arg in args[1:]]

    return clean_args

@bot.message_handler(commands=["start"])
def bot_welcome(message):
    bot.send_message(message.chat.id, BOT_MESSAGES["Welcome"])

@bot.message_handler(commands=["help"])
def bot_help(message):
    bot.send_message(message.chat.id,BOT_MESSAGES["Help"])

@bot.message_handler(commands=["simple"])
@run_in_thread
def simple_stats(message):
    domain = get_valid_domain(message)
    if not domain:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectDomain"])
        logger.warning("Запрос с некорректным именем группы")
        return
    bot.send_message(message.chat.id, BOT_MESSAGES['Processing'])
    stats_list = get_stat(domain=domain)
    if not stats_list:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotStatsList"])
        logger.warning(f"Не удалось выполнить запрос постов для группы {domain}")
        return

    message_lines = [BOT_MESSAGES["SimpleStats_line"].format(i=i, **post)
                     for i, post in enumerate(stats_list, 1)
                     ]
    full_message = "\n\n".join(message_lines)
    bot.send_message(message.chat.id, full_message)
    logger.info(f"Запрос постов по группе {domain} выполнен успешно!")

@bot.message_handler(commands=["complex"])
@run_in_thread
def complex_stats(message):
    domain = get_valid_domain(message)
    if not domain:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectDomain"])
        logger.warning("Запрос с некорректным именем группы")
        return
    bot.send_message(message.chat.id, BOT_MESSAGES['Processing'])
    stats_list = get_stat(domain=domain)
    if not stats_list:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotStatsList"])
        logger.warning(f"Не удалось выполнить запрос постов по группе {domain}")
        return
    df = pd.DataFrame(stats_list)
    df['er'] = (df['likes'] + df['comments'] + df['reposts']) / df['members'] * 100
    df['total_activity'] = df['likes'] + df['comments'] + df['reposts']
    best_post_index = df['total_activity'].idxmax()
    best_post = df.loc[best_post_index].to_dict()
    avg_er = df['er'].mean()

    bot.send_message(message.chat.id, BOT_MESSAGES["ComplexStats_line"].format(avg_er=avg_er, **best_post))
    logger.info(f"Запрос постов по группе {domain} выполнен успешно!")

@bot.message_handler(commands=["add"])
@run_in_thread
def add_to_watchlist(message):
    domain = get_valid_domain(message)
    if not domain:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectDomain"])
        logger.warning("Запрос с некорректным именем группы")
        return
    category = get_valid_category(message, index=1)
    if not category:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotCategory"].format(categories=CATEGORIES))
        logger.warning(f"Попытка добавить группу {domain} без категории!")
        return
    if category not in CATEGORIES:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectCategory"].format(categories=CATEGORIES))
        logger.warning(f"Попытка добавления группы {domain} с неверной категорией {category}")
        return
    bot.send_message(message.chat.id, BOT_MESSAGES['Processing'])
    group = None
    try:
        group = vk.groups.getById(group_id=vk.utils.resolveScreenName(screen_name=domain)["object_id"],
                              fields="members_count")
    except Exception as e:
        bot.send_message(message.chat.id, BOT_MESSAGES["GetGroupError"])
        logger.error(f"Ошибка получения информации о группе {domain} при добавлении в список: {e}", exc_info=True)

    members = group[0]["members_count"]

    try:
        with db_utils.db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                        INSERT INTO watchlist (domain, category, members)
                        VALUES (?, ?, ?)
                        ''', (domain, category, members))
            conn.commit()
            bot.send_message(message.chat.id, BOT_MESSAGES["AddedToWatchlist"])
            logger.info(f"Группа {domain} успешно добавлена в отслеживаемые!")
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, BOT_MESSAGES["AlreadyInWatchlist"])
        logger.warning(f"Попытка добавления в список группы {domain}, уже состоящей в нём!")

@bot.message_handler(commands=["info"])
@run_in_thread
def info_group(message):
    domain = get_valid_domain(message)
    if not domain:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectDomain"])
        logger.warning("Запрос с некорректным именем группы")
        return
    bot.send_message(message.chat.id, BOT_MESSAGES["Processing"])
    conn = db_utils.db_connect()
    df = pd.read_sql_query("SELECT * FROM watchlist WHERE domain = :domain", conn, params={"domain": domain})
    conn.close()

    if df.empty:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotInWatchlist"])
        logger.warning(f"Запрос информации по группе {domain} отклонён, группа не в списке!")
    else:
        row = df.iloc[0].to_dict()
        bot.send_message(message.chat.id, BOT_MESSAGES["InfoGroup_line"].format(**row))
        logger.info(f"Запрос информации по группе {domain} выполнен успешно!")

@bot.message_handler(commands=["list"])
@run_in_thread
def list_group(message):
    category = get_valid_category(message, index=0)
    bot.send_message(message.chat.id, BOT_MESSAGES["Processing"])
    conn = db_utils.db_connect()
    query = ('''
                SELECT domain, category, members FROM watchlist ORDER BY id DESC
                ''')
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not category:
        if df.empty:
            bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotRows"])
            logger.warning("При запросе по всем категориям ничего не найдено!")
            return
        df_top = df.head(10)
        message_lines = [BOT_MESSAGES["ListGroup_line"].format(i=i, **row)
                         for i, (index, row) in enumerate(df_top.iterrows(), 1)]
        full_message = "\n".join(message_lines)

        bot.send_message(message.chat.id, full_message)
        logger.info("Запрос без категории выполнен успешно!")

    elif category:
        if category and category not in CATEGORIES:
            bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectCategory"].format(categories=CATEGORIES))
            logger.warning("Запрос с неверной категорией!")
            return
        query = ('''
                    SELECT * FROM watchlist WHERE category = ? ORDER BY id DESC
                    ''')
        params = (category,)
        with db_utils.db_connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotRows"])
            logger.warning(f"При запросе по категории {category} ничего не найдено!")
            return

        message_lines = (BOT_MESSAGES["ListGroup_line"].format(i=i, **row)
                         for i, (index, row) in enumerate(df.iterrows(), 1))
        full_message = "\n".join(message_lines)

        bot.send_message(message.chat.id, full_message)
        logger.info("Запрос с категорией выполнен успешно!")

@bot.message_handler(commands=["delete"])
@run_in_thread
def delete_group(message):
    domain = get_valid_domain(message)
    if not domain:
        bot.send_message(message.chat.id, BOT_MESSAGES["Warning_IncorrectDomain"])
        logger.warning("Запрос с некорректным именем группы")
        return
    bot.send_message(message.chat.id, BOT_MESSAGES["Processing"])
    try:
        with db_utils.db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                            DELETE FROM watchlist WHERE domain = ?
                            ''', (domain,))
            if cursor.rowcount > 0:
                bot.send_message(message.chat.id, BOT_MESSAGES["DeletedFromWatchlist"])
                logger.info(f"Группа {domain} успешно удалена из отслеживания!")
            else:
                bot.send_message(message.chat.id, BOT_MESSAGES["Warning_NotInWatchlist"])
                logger.warning(f"Запрос не может быть выполнен, так как группа "
                           f"{domain} не найдена в отслеживаемых!")
            conn.commit()
    except Exception as e:
        bot.send_message(message.chat.id, BOT_MESSAGES["DeleteGroupError"])
        logger.error(f"Ошибка при удалении группы {domain}: {e}", exc_info=True)