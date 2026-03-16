import threading
import logging
from Bot_Dev import bot
from Scheduler import main_loop


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_scheduler_thread():
    logger.info("Запуск планировщика в фоновом потоке...")
    try:
        main_loop()
    except Exception as e:
        logger.error(f"Критическая ошибка в потоке планировщика: {e}", exc_info=True)

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler_thread, name="SchedulerThread")
    scheduler_thread.daemon = True
    scheduler_thread.start()

    logger.info(f"Бот запущен!")
    logger.info("Нажми Ctrl+C, чтобы остановить бота и планировщик.")

    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("Остановка работы бота...")

