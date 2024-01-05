import sys
import traceback
import random
import io
from json.decoder import JSONDecodeError

import asyncio
import aiofiles
from PIL import Image
from better_automation.twitter import TwitterClient, TwitterAccount
from better_automation.twitter.errors import Forbidden, HTTPException

from data.settings import SLEEP_FROM, SLEEP_TO, NUMBER_OF_ATTEMPTS
from data.config import logger, LOCKED, SUSPENDED, BAD_TOKEN, BANNER_IMAGE, DB
from exeptions.exeptions import WrongCaptcha
from utils.db_func import async_write_json, async_read_json


class TwitterTasksCompleter:
        
    def __init__(self, token, data: dict) -> None:
        self.account_token: str = token
        self.account_tasks: list = data['tasks']
        self.account_proxy: str | None = data['proxy']
        # Рандомизируем список задач
        random.shuffle(self.account_tasks)

        self.twitter_client: TwitterClient | None = None
        self.twitter_account: TwitterAccount = TwitterAccount(token)

    async def start_tasks(self):
        """ Стартуем задачи """

        # Количество попыток в случае неудачи
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            try:
                logger.info(f'{self.account_token} | Попытка {num}')
                async with TwitterClient(
                    account=self.twitter_account,
                    proxy=self.account_proxy, 
                    verify=False
                ) as twitter:
                    
                    self.twitter_client = twitter
                    
                    await self.get_name()

                    # Начало работы над авторизацией в приложении
                    # bind_data = {
                    #     'client_id': 'AIzaSyBPmETcQFfpDrw_eB6s8DCkDpYYBt3e8Wg',
                    #     'code_challenge': 'challenge',
                    #     'state': 'state',
                    #     'redirect_uri': 'https://well3.com',
                    #     'code_challenge_method': 'plain',
                    #     'scope': 'users.read tweet.read offline.access',
                    #     'response_type': 'code',
                    # }
                    
                    # bind_code: str = await self.twitter_client.bind_app(**bind_data)
                    # print(bind_code)

                    for num, task in enumerate(self.account_tasks):
                        if task['status'] == 'pending':
                            task_type = task['type']
                            changed = False
                            
                            if task_type == 'follow':
                                status = await self.follow_quest(username=task['target'])
                                if status:
                                    self.account_tasks[num]['status'] = 'completed'
                                    changed = True

                            elif task_type == 'retweet':
                                try:
                                    status = await self.like_and_reetweet_quest(tweet_id=task['tweet_id'])
                                    if status:
                                        self.account_tasks[num]['status'] = 'completed'
                                        changed = True
                                except HTTPException as err:
                                    if 'already retweeted' in str(err):
                                        logger.warning(f'{self.account_token} | уже успешно репостнул {task["tweet_id"]}')
                                        self.account_tasks[num]['status'] = 'completed'
                                        changed = True
                                    elif 'already_favorited' in str(err):
                                        logger.warning(f'{self.account_token} | уже успешно лайкнул {task["tweet_id"]}')
                                        self.account_tasks[num]['status'] = 'completed'
                                        changed = True
                                    else:
                                        logger.error(f'Неизвестная ошибка: {err}')

                            elif task_type == 'update_banner':
                                image_bytes = await self.read_image_as_base64_encoded_bytes(BANNER_IMAGE)
                                media_id = await twitter.upload_image(image=image_bytes)
                                status = await twitter.update_profile_banner(media_id=media_id)
                                if status:
                                    logger.success(f'{self.account_token} | Баннер был успешно установлен!')
                                    self.account_tasks[num]['status'] = 'completed'
                                    changed = True

                            if changed:
                                actual_db = await async_read_json(DB)
                                actual_db[self.account_token] = {
                                    'tasks': self.account_tasks,
                                    'proxy': self.account_proxy
                                }
                                await async_write_json(actual_db, DB)
                                if num + 1 == len(self.account_tasks):
                                    break
                                await self.sleep_after_action()

                    # Меняем имя пользователя (цикл необходим потому что обновляется не с первого запроса)
                    # !!! ПОСЛЕ ДЕЙСВИЯ АККАУНТ БУДЕТ БРОШЕН В LOCKED!!! НАДО БУДЕТ ПРОХОДИТЬ КАПЧУ !!!
                    # await self.get_name()
                    # old_name = self.twitter_account.name
                    # while True:
                    #     await self.change_twitter_name()
                    #     await self.get_name()
                    #     new_name = self.twitter_account.name
                    #     print(old_name, new_name)
                    #     if old_name != new_name:
                    #         break

                    logger.success(f'{self.account_token} | закончил все задания')
                    break

            except Forbidden as err:
                if self.twitter_account.status != 'GOOD':
                    logger.error(f'{self.account_token} | Возникла проблема с аккаунтом! Текущий статус аккаунта = {self.twitter_account.status}')
                    if self.twitter_account.status == 'BAD_TOKEN':
                        logger.warning(f'Неверный токен - {self.twitter_account}')
                        await self.write_problem_status()
                    elif self.twitter_account.status == 'SUSPENDED':
                        logger.warning(f'Действие учетной записи приостановлено (бан)! Токен - {self.twitter_account}')
                        await self.write_problem_status()
                    elif self.twitter_account.status == "LOCKED":
                        logger.warning(f'Учетная запись заморожена (лок)! Требуется прохождение капчи. Токен - {self.twitter_account}')
                        await self.write_problem_status()
                    
                    continue
                
                logger.error(f'Неизвестная ошибка: {err}')

            except JSONDecodeError:
                logger.error(f'{self.account_token} | Ошибка с получением ответа от API')
                continue

    async def get_name(self):
        """ Возвращает никнейм пользователя, не username """

        await self.twitter_client.request_username()
        await self.twitter_client._request_user_data(self.twitter_account.username)

    async def write_problem_status(self, status):
        """ Записывает текщий статус проблемного токена в соответсвующий файл """
        
        status = {
            "LOCKED": LOCKED,
            "SUSPENDED": SUSPENDED,
            "BAD_TOKEN": BAD_TOKEN
        }

        required_file = status[self.twitter_account.status]
        async with aiofiles.open(file=required_file, mode='a', encoding='utf-8-sig') as f:
            await f.write(f'{self.account_token}\n')

    @staticmethod
    async def sleep_after_action():
        """ Сон между действиями"""
        
        sleep_time = random.randint(SLEEP_FROM, SLEEP_TO)
        logger.debug(f'Буду спать: {sleep_time}')
        await asyncio.sleep(sleep_time)

    async def follow_quest(self, username: str):
        """ Подписываемся на пользователя """
        user_info = await self.twitter_client.request_user_data(username)
        status = await self.twitter_client.follow(user_id=user_info.id)
        if status:
            logger.info(f'{self.account_token} | Успешно подписался на {username}')
            return True
        return False

    async def like_and_reetweet_quest(self, tweet_id: str):
        """ Лайкаем и делаем ретвит """
        tweet_id = await self.twitter_client.repost(tweet_id=tweet_id)
        like_status = await self.twitter_client.like(tweet_id=tweet_id)
        if like_status and tweet_id:
            logger.info(f'{self.account_token} | Успешно лайкнул и репостнул {tweet_id}')
            return True
        return False

    async def change_twitter_name(self) -> tuple[bool, str, int]:
        """ Меняем имя в твиттере """

        if '❤️ $WELL' not in self.twitter_account.name:

            if "❤️ Memecoin" in self.twitter_account.name:
                twitter_account_name = self.twitter_account.name.split('❤️')
                new_name = twitter_account_name[0] + '❤️ $WELL'
            else:
                new_name = self.twitter_account.name + '❤️ $WELL'
            
            change_twitter_name_result = await self.twitter_client.update_profile(
                name=self.twitter_account.name)

            if not change_twitter_name_result:
                logger.error(f'{self.account_token} | Не удалось изменить имя пользователя')
            
            else:
                logger.success(f'{self.account_token} | {self.twitter_account.name} имя было успешно изменено на {new_name}')

            return change_twitter_name_result
        else:
            logger.warning(f'{self.account_token} | В имени аккаунта уже есть ❤️ $WELL, текущее имя - {self.twitter_account.name}')
            return True
        
    async def read_image_as_base64_encoded_bytes(self, file_path):
        """ Считываем изображение и превращаем его в байты с помощью PIL """
        
        image = Image.open(file_path)
        with io.BytesIO() as img_buffer:
            image.save(img_buffer, format=image.format)
            image_bytes = img_buffer.getvalue()
        return image_bytes
    

async def start_twitter_task(token: str, data: dict) -> bool:
    try:
        await TwitterTasksCompleter(token=token, data=data).start_tasks()
    
    except KeyboardInterrupt:
        sys.exit(1)

    except WrongCaptcha:
        pass

    except Exception as error:
        logger.error(f'{token} | Неизвестная ошибка: {error}')
        print(traceback.print_exc())
