
from datetime import datetime
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
    stats_list = []
    try:
        if not domain:
            print("Вы ничего не ввели!")
            return 0, 0, 0

        response = vk.wall.get(domain=domain, count=10, filter="all")

        if response["items"]:

            group = vk.groups.getById(group_id=vk.utils.resolveScreenName(screen_name=domain)["object_id"], fields="members_count")
            members_count = group[0]["members_count"]
            pin_count = 0
            get_count = 0
            for post in response["items"]:

                is_pinned = post.get("is_pinned")

                if is_pinned == 1:
                    print("Пропускаю закреп...")
                    pin_count += 1

                    if pin_count == 10:
                        print("Не удалось найти последний незакреплённый пост!")
                    else:
                        continue
                else:
                    post_data = {"date": datetime.fromtimestamp(post["date"]).strftime("%Y.%m.%d"),
                                "views": post["views"]["count"],
                                 "likes": post["likes"]["count"],
                                 "comments": post["comments"]["count"],
                                 "reposts": post["reposts"]["count"],
                                 "members": members_count}
                    stats_list.append(post_data)
                    get_count += 1
                    print("Сбор данных успешен!")
                    if get_count == 5:
                        print("5 постов найдено!")
                        break
        else:
            print("Стена пуста или посты недоступны")

    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка API: {e}")
        return None
    except Exception as e:
        print(f"Произошла непревдвиденная ошибка: {e}")
        return None

    return stats_list

@bot.message_handler(commands=["start"])
def bot_welcome(message):
    bot.send_message(message.chat.id, "Этот бот выводит статистику указанной группы вконтаке.\n "
                                      "Для получения инструкции напишите: /help")



@bot.message_handler(commands=["help"])
def bot_help(message):
    bot.send_message(message.chat.id,"Для простой статистики по последним пяти постам введите:\n"
                                     "/simple (краткое имя группы без @ в начале)\n"
                                     "Для вывода коэффициента вовлечённости и лучшего поста из "
                                     "последних пяти, напишите:\n"
                                     "/complex (краткое имя группы без @ в начале)")

@bot.message_handler(commands=["simple"])
def simple_stats(message):
    full_message = ""
    number = 1
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "Пожалуйста, укажите имя группы! "
                                          "Пример: /complex apiclub")
        return
    stats_list = get_stat(domain=args[1])
    if not stats_list:
        bot.send_message(message.chat.id, "Не удалось получить данные. "
                                          "Проверьте имя группы и открыта ли она")
        return
    for post in stats_list:
        date = post["date"]
        views = post["views"]
        likes = post["likes"]
        comments = post["comments"]
        reposts = post["reposts"]
        one_line = (f"{number} - Статистика по последнему посту (За {date}): "
                    f"просмотры - {views}, "
                    f"лайки - {likes}, "
                    f"комментарии - {comments}, "
                    f"репосты - {reposts}\n\n")
        full_message += one_line
        number += 1

    bot.send_message(message.chat.id, full_message)

@bot.message_handler(commands=["complex"])
def complex_stats(message):
    er_list = []
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "Пожалуйста, укажите имя группы! "
                                          "Пример: /complex apiclub")
        return

    stats_list = get_stat(domain=args[1])

    if not stats_list:
        bot.send_message(message.chat.id, "Не удалось получить данные. "
                                          "Проверьте имя группы и открыта ли она")
        return

    best_post=None
    for post in stats_list:
        er=(post["likes"]/post.get("members", 1)) * 100
        er_list.append(er)
        if (best_post is None or (post["likes"]+post["comments"]+post["reposts"]) >
                (best_post["likes"]+best_post["comments"]+best_post["reposts"])):
            best_post = post
    avg_er = (sum(er_list)/len(er_list))

    bot.send_message(message.chat.id, f"Средний ER (Уровень вовлечённости) группы: {avg_er:.0%}\n\n "
                                      f"Лучший пост: дата - {best_post["date"]}, "
                                      f"просмотры - {best_post["views"]}, "
                                      f"лайки - {best_post["likes"]}, "
                                      f"комментарии - {best_post["comments"]}, "
                                      f"репосты - {best_post["reposts"]}")


bot.infinity_polling()