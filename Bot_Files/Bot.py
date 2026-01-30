

import vk_api
from telebot import TeleBot

VK_ACCESS_TOKEN = "TOKEN" ## Здесь нужно ввести ваш ACCESS TOKEN для вконтакте
TG_ACCESS_TOKEN = "TOKEN" ## Здесь нужно ввести токен вашего бота в телеграмме
bot = TeleBot(token=TG_ACCESS_TOKEN)
vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
vk = vk_session.get_api()

def main():

    try:
        response = vk.users.get()

        user_id = response[0]["id"]
        first_name = response[0]["first_name"]
        print(f"Успешное подключение! Здравствуй, {first_name} (ID: {user_id})")

    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка API: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

if __name__ == "__main__":
    main()

def get_stat(domain = None):
    likes = 0
    comments = 0
    reposts = 0
    try:
        if not domain:
            print("Вы ничего не ввели!")
            return 0, 0, 0

        response = vk.wall.get(domain=domain, count=5, filter="all")

        if response["items"]:

            pin_count = 0
            for post in response["items"]:

                is_pinned = post.get("is_pinned")

                if is_pinned == 1:
                    print("Пропускаю закреп...")
                    pin_count += 1

                    if pin_count == 5:
                        print("Не удалось найти последний незакреплённый пост!")
                        break
                    else:
                        continue
                else:
                    likes = post["likes"]["count"]
                    comments = post["comments"]["count"]
                    reposts = post["reposts"]["count"]
                    print("Сбор данных успешен!")
                    break
        else:
            print("Стена пуста или посты недоступны")

    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка API: {e}")
    except Exception as e:
        print(f"Произошла непревдвиденная ошибка: {e}")

    return likes, comments, reposts

@bot.message_handler(commands=["start", "help"])
def bot_welcome(message):
    bot.send_message(message.chat.id,"Введите краткое имя группы или пользователя без @ в начале")

@bot.message_handler(content_types=["text"])
def bot_vk_stats(message):
    likes, comments, reposts = get_stat(domain = message.text)
    bot.send_message(message.chat.id, f"Статистика по последнему посту: лайки - {likes}, комментарии - {comments}, репосты - {reposts}")

bot.infinity_polling()