import db_utils
import pandas as pd
from vk_fetcher import get_stat
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='scheduler.log', filemode='a', encoding='utf-8'
)
logger = logging.getLogger(__name__)
SLEEP_TIME = 6 * 60 * 60
WARNING_TIME = 5 * 60

def run_collector():
    with db_utils.db_connect() as conn:
        df = pd.read_sql_query("SELECT domain FROM watchlist", conn)
        for domain in df['domain']:
            if pd.notna(domain):
                try:
                    stats_list = get_stat(domain)
                    db_utils.save_stat(domain, stats_list)
                except Exception as e:
                    logger.error(f"Ошибка при фоновом сборе данных для группы {domain}: "
                                 f"{e}", exc_info=True)
                    continue

def main_loop():
    logger.info("Планировщик запущен в фоновом режиме...")

    while True:
        try:
            run_collector()
            logger.info("Сбор завершён, жду до следующего...")
            time.sleep(SLEEP_TIME)

        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}", exc_info=True)
            time.sleep(WARNING_TIME)

if __name__ == "__main__":
    main_loop()