import vk_api
import datetime
import logging
import db_utils
from datetime import datetime
from config import VK_ACCESS_TOKEN

logger = logging.getLogger(__name__)

GET_COUNT = 20
SHOW_COUNT = 10

def get_stat(domain = None, get_count = GET_COUNT, show_count = SHOW_COUNT):

    local_vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
    local_vk = local_vk_session.get_api()
    stats_list = []

    try:
        if not domain:
            logger.warning("Domain не введён!")
            return []

        response = local_vk.wall.get(domain=domain, count=get_count, filter="all")

        if response["items"]:

            group = local_vk.groups.getById(group_id=domain, fields="members_count")
            members_count = group[0]["members_count"]
            pin_count = 0
            post_count = 0
            for post in response["items"]:

                is_pinned = post.get("is_pinned")

                if is_pinned == 1:
                    logger.info("Пропускаю закреп...")
                    pin_count += 1

                    if pin_count == get_count:
                        logger.warning("Не удалось найти последний незакреплённый пост!")
                else:
                    post_data = {"date": datetime.fromtimestamp(post["date"]),
                                "views": post["views"]["count"],
                                 "likes": post["likes"]["count"],
                                 "comments": post["comments"]["count"],
                                 "reposts": post["reposts"]["count"],
                                 "members": members_count,
                                 "id": post["id"]}
                    stats_list.append(post_data)
                    post_count += 1
                    logger.info("Сбор данных успешен!")
                    if post_count == show_count:
                        logger.info(f"{post_count} постов найдено!")
                        break
            if stats_list:
                try:
                    db_utils.save_stat(domain, stats_list)
                    logger.info(f"{len(stats_list)} постов для группы {domain} успешно загружено!")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке постов для группы {e}!", exc_info=True)
        else:
            logger.warning("Стена пуста или посты недоступны")

    except vk_api.exceptions.ApiError as e:
        logger.error(f"Ошибка API: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Произошла непревдвиденная ошибка: {e}", exc_info=True)
        return None

    return stats_list