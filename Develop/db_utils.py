import sqlite3
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log', filemode='a', encoding='utf-8'
)
logger = logging.getLogger(__name__)

def db_connect():
    try:
        conn = sqlite3.connect('tg_vk_bot.db', timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')

        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise e

def save_stat(domain, stats_list):
    try:
        with db_connect() as conn:
            cursor = conn.cursor()
            data_to_insert = [
                (domain, p['id'], p['date'], p['views'], p['likes'], p['comments'], p['reposts'], p['members'])
                for p in stats_list
            ]
            cursor.executemany('''
                    INSERT OR REPLACE INTO post_stats (domain, post_id, post_date, views, likes, comments, reposts, members)
                        VALUES (?,?,?,?,?,?,?,?)''', data_to_insert)
            conn.commit()
            logger.info(f"Загружено {len(stats_list)} постов для группы {domain}")
    except sqlite3.Error as e:
        logger.error(f"Произошла ошибка при записи в БД: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка при записи в БД: {e}", exc_info=True)
