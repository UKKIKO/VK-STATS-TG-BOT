import os
import threading
import logging
import telebot
from flask import Flask, request
from dotenv import load_dotenv
from Bot_Dev import bot, logger
from Scheduler import main_loop
from config import TG_ACCESS_TOKEN

load_dotenv()
app = Flask(__name__)

@app.route(f'/{TG_ACCESS_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])

        return {'status': 'ok'}, 200
    else:
        return {'status': 'bad request'}, 400

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

    webhook_url = os.environ.get('WEBHOOK_URL')

    if webhook_url:
        full_webhook_url = f"{webhook_url}/{TG_ACCESS_TOKEN}"

        logger.info(f"Устанавливаем Webhook на: {full_webhook_url}")

        bot.remove_webhook()
        bot.set_webhook(url=full_webhook_url)
    else:
        logger.warning("Переменная WEBHOOK_URL не найдена. Webhook не настроен.")

    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Сервер запускается на порту {port}...")
    app.run(host='0.0.0.0', port=port)

