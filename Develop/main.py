import threading
import logging
import time
from Bot_Dev import main as run_bot
from Scheduler import main_loop as run_scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_background_tasks():
    bot_thread = threading.Thread(target=run_bot, name="BotThread")
    bot_thread.daemon = True
    bot_thread.start()

    scheduler_thread = threading.Thread(target=run_scheduler, name="SchedulerThread")
    scheduler_thread.daemon = True
    scheduler_thread.start()

    logger.info("Бот и Планировщик запущены в фоновом режиме")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Остановка приложения...")

if __name__ == "__main__":
    run_background_tasks()