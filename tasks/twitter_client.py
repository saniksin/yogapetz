import sys
import time
import base64
import traceback
import random
import io
import datetime
from json.decoder import JSONDecodeError
from urllib.parse import urlparse

import asyncio
import aiofiles
from PIL import Image
from better_automation.twitter import TwitterClient, TwitterAccount
from better_automation.base import BaseAsyncSession
from better_automation.twitter.errors import Forbidden, HTTPException, Unauthorized
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from curl_cffi.requests.errors import RequestsError
from eth_account.messages import encode_defunct
from web3.exceptions import ContractLogicError, TransactionNotFound, Web3ValidationError

from data.settings import SLEEP_FROM, SLEEP_TO, NUMBER_OF_ATTEMPTS, API_KEY, MIN_BALANCE, API_KEY
from data.config import logger, PROBLEMS, BANNER_IMAGE, DB, ACTUAL_REF, WELL_ABI
from exeptions.exeptions import WrongCaptcha
from utils.db_func import async_write_json, async_read_json
from data.models import Networks, CONTRACT_ADDRESS
from tasks.eth_client import EthClient


class TwitterTasksCompleter:
        
    def __init__(self, token, data: dict, spare_ref_codes) -> None:
        self.account_token: str = token
        self.account_tasks: list = data['tasks']
        self.account_proxy: str | None = data['proxy']
        self.async_session: BaseAsyncSession = BaseAsyncSession(proxy=self.account_proxy, verify=False)
        self.register = data['register']
        self.ref_code = data['ref_code']
        self.refresh_token = data['refresh_token']
        self.id_token = data['id_token']
        self.platform = data['platform']
        self.private_key = data['private_key']
        self.twitter_account_status = data['twitter_account_status']
        self.user_agent = UserAgent().chrome
        self.user_platform = random.choice(['macOS', 'Windows', 'Linux'])
        self.spare_ref_codes = spare_ref_codes

        # Рандомизируем список задач
        random.shuffle(self.account_tasks)

        self.twitter_client: TwitterClient | None = None
        self.twitter_account: TwitterAccount = TwitterAccount(token)
    
    async def write_to_db(self):
        actual_db = await async_read_json(DB)
        actual_db[self.account_token] = {
            'register': self.register,
            'id_token': self.id_token,
            'refresh_token': self.refresh_token,
            'ref_code': self.ref_code,
            'proxy': self.account_proxy,
            'private_key': self.private_key,
            'twitter_account_status': self.twitter_account_status,
            'tasks': self.account_tasks,
            'platform': self.platform
        }
        await async_write_json(actual_db, DB)

    def get_reserv_codes(self):
        self.ref_code = self.spare_ref_codes.pop(0) if self.spare_ref_codes else None

    async def start_tasks(self, option: int):
        """ Стартуем задачи """

        if self.twitter_account_status == "SUSPENDED":
            await self.write_status("SUSPENDED")
            return
        
        if self.twitter_account_status == "BAD_TOKEN":
            await self.write_status("BAD_TOKEN")
            return

        # Количество попыток в случае неудачи
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            try:
                logger.info(f'{self.twitter_account} | Попытка {num}')
                async with TwitterClient(
                    account=self.twitter_account,
                    proxy=self.account_proxy, 
                    verify=False
                ) as twitter:
                    
                    self.twitter_client = twitter
                    # Совершаем любое действие чтобы обновить статус аккаунта
                    try:
                        await self.get_name()
                    except Unauthorized:
                        logger.error(f'{self.twitter_account} | Не удалось авторизироваться по данному токену! Проверьте токен')
                        self.twitter_account_status = "BAD_TOKEN"
                        await self.write_to_db()
                        await self.write_status(status="Unauthorized")
                        break

                    if option == 1:
                        # Регистрация
                        if not self.register:
                            if not self.ref_code:
                                self.get_reserv_codes()
                            logger.info(f'{self.twitter_account} | Начинаю регистрацию')
                            result = await self.registration()
                            self.refresh_token = result['refreshToken']
                            self.id_token = result['idToken']
                            result = await self.send_invite_code()
                            if 'не актульный' in str(result):
                                self.get_reserv_codes()
                                if not self.ref_code:
                                    await self.write_status('REF_CODE_PROBLEM')
                                    break
                                msg = (f'{self.twitter_account} | взял запасной реф код, осталось запасных актуальных реф кодов {len(self.spare_ref_codes)}')
                                logger.warning(msg)
                                continue
                            if result:
                                logger.info(f'{self.twitter_account} | Успешно зарегистрирован или был зарегистрован раньше')
                                self.register = True
                                await self.write_to_db()
                                await self.sleep_after_action()
                            else:
                                logger.error(f'{self.twitter_account} | Произошла ошибка при регистрации')
                                if num == NUMBER_OF_ATTEMPTS:
                                    await self.write_status(status='REF_CODE_PROBLEM')
                                continue
                        
                        # Выполняем основные твиттер таски (основные)
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
                                            logger.warning(f'{self.twitter_account} | уже успешно репостнул {task["tweet_id"]}')
                                            self.account_tasks[num]['status'] = 'completed'
                                            changed = True
                                        elif 'already_favorited' in str(err):
                                            logger.warning(f'{self.twitter_account} | уже успешно лайкнул {task["tweet_id"]}')
                                            self.account_tasks[num]['status'] = 'completed'
                                            changed = True
                                        else:
                                            logger.error(f'Неизвестная ошибка: {err}')

                                elif task_type == 'update_banner':
                                    image_bytes = await self.read_image_as_base64_encoded_bytes(BANNER_IMAGE)
                                    media_id = await twitter.upload_image(image=image_bytes)
                                    status = await twitter.update_profile_banner(media_id=media_id)
                                    if status:
                                        logger.success(f'{self.twitter_account} | Баннер был успешно установлен!')
                                        self.account_tasks[num]['status'] = 'completed'
                                        changed = True
                                        await self.sleep_after_action()
                                    else:
                                        logger.error(f'{self.twitter_account} | Баннер не был установлен!')
                                        continue

                                if changed:
                                    await self.write_to_db()
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
                                    
                        # Подтверждаем основные таски на платформе
                        await self.login()
                        account_data = await self.get_account_data()

                        # Ежедневное задание
                        for name, value in account_data['ygpzQuesting']['info']['dailyProgress'].items():
                            if "complete-breath-session" in name and value['value'] != 2:

                                if value['nextAvailableFrom']:
                                    current_time = int(str(datetime.datetime.now().timestamp()).replace(".","")[:-3])
                                    human_readable_time = datetime.datetime.fromtimestamp(current_time / 1000)
                                    formatted_time = human_readable_time.strftime('%Y-%m-%d %H:%M:%S')
                                    if value['nextAvailableFrom'] < current_time:
                                        status = await self.complete_breath_session()
                                    else:
                                        logger.info(f"{self.twitter_account} | ближайшая breath session {formatted_time}.")
                                        break
                                else:
                                    status = await self.complete_breath_session()

                                if status:
                                    logger.info(f'{self.twitter_account} | успешно выполнил breath session')
                                    await self.sleep_after_action()
                                else:
                                    logger.error(f'{self.twitter_account} | не удалось выполнить breath session')

                        for name, value in account_data['ygpzQuesting']['info']['specialProgress'].items():
                                
                            if name == 'add-well-to-twitter-profile':
                                continue

                            task_exists = any(task['task'] == name for task in self.platform)
                            
                            if task_exists:
                                for task in self.platform:
                                    if task['task'] == name and task['status'] != "completed":
                                        logger.info(f'{self.twitter_account} | подтверждение задачи {name}')
                                        status = await self.complete_other_tasks(task_name=name)
                                        if status:
                                            logger.info(f'{self.twitter_account} | успешно подтвердил {name}')
                                            task['status'] = 'completed'
                                            await self.write_to_db()
                                            await self.sleep_after_action()
                                        else:
                                            logger.error(f'{self.twitter_account} | не смог подтвердить задачу {name}')
                            else:
                                logger.error(f'Задача {name} не найдена в текущем списке задач!')
                    
                        logger.success(f'{self.twitter_account} | закончил все задания задания с твиттером')

                        break
                    elif option == 3:
                        await self.login()
                        account_data = await self.get_account_data()
                        if not account_data['contractInfo']:
                            signature = ('Welcome to Yogapetz\n' 
                                        'Click "Sign" to continue.\n\n'
                                        'Timestamp:\n'
                                       f'{str(datetime.datetime.now().timestamp()).replace(".","")[:-3]}')
                            
                            await self.start_welcome_sign_msg(signature)

                            account_data = await self.get_account_data()
                            if account_data.get('contractInfo', False):
                                logger.success(f'{self.twitter_account} | успешно подписал сообщение и прикрепил кошелек')
                            else:
                                logger.error(f'{self.twitter_account} | не удалось подписать сообщение и прикрепить кошелек')
                        
                        if account_data['contractInfo']['rankupQuest'].get('currentRank', False):
                            current_rank = account_data['contractInfo']['rankupQuest']['currentRank']
                            signature = account_data['contractInfo']['rankupQuest']['signature']
                                
                            await self.start_rankup_quest(current_rank, signature)

                        if account_data['contractInfo']['dailyQuest'].get('nonce', False):
                            nonce = account_data['contractInfo']['dailyQuest']['nonce']
                            signature = account_data['contractInfo']['dailyQuest']['signature']

                            await self.start_daily_quest(nonce, signature)
                            
                    elif option == 4:
                        await self.login()
                        account_data = await self.get_account_data()
                        if not account_data['referralInfo']['myReferralCodes']:
                            await self.generate_invite_codes()
                            logger.warning(f'{self.twitter_account} | не удалось получить реф. коды. Пробую сгенирировать...')
                            continue
                        ref_codes = [code_data['code'] for code_data in account_data['referralInfo']['myReferralCodes'] \
                                    if 'usedAt' not in code_data]
                        await self.write_status(ref_codes, ACTUAL_REF)
                    break

            except Forbidden as err:
                if self.twitter_account.status != 'GOOD':
                    logger.error(f'{self.twitter_account} | Возникла проблема с аккаунтом! Текущий статус аккаунта = {self.twitter_account.status}')
                    if self.twitter_account.status == 'BAD_TOKEN':
                        logger.warning(f'Неверный токен - {self.twitter_account}')
                        self.twitter_account_status = "BAD_TOKEN"
                        await self.write_to_db()
                        await self.write_status(status='BAD_TOKEN')
                        break
                    elif self.twitter_account.status == 'SUSPENDED':
                        logger.warning(f'Действие учетной записи приостановлено (бан)! Токен - {self.twitter_account}')
                        await self.write_status(status='SUSPENDED')
                        self.twitter_account_status = "SUSPENDED"
                        await self.write_to_db()
                        break
                    elif self.twitter_account.status == "LOCKED":
                        logger.warning(f'Учетная запись заморожена (лок)! Требуется прохождение капчи. Токен - {self.twitter_account}')
                        await self.write_status(status='LOCKED')
                        break
                    continue
                
                logger.error(f'Неизвестная ошибка: {err}')
                continue

            except JSONDecodeError:
                logger.error(f'{self.twitter_account} | Ошибка с получением ответа от API')
                continue

            except RequestsError:
                logger.error(f'{self.twitter_account} | проблема с прокси! Проверьте прокси!')
                await self.write_status(status='PROXY_ERR')
                break

            except KeyError:
                continue

    async def get_name(self):
        """ Возвращает никнейм пользователя, не username """

        await self.twitter_client.request_username()
        await self.twitter_client._request_user_data(self.twitter_account.username)

    async def write_status(self, status, path=PROBLEMS):
        """ Записывает текщий статус проблемного токена в соответсвующий файл """
        try:
            async with aiofiles.open(file=path, mode='a', encoding='utf-8-sig') as f:
                if path != PROBLEMS:
                    for item in status:
                        await f.write(f'{item}\n')
                else:
                    await f.write(f'{self.account_token} | {self.account_proxy} | {self.ref_code} | {status}\n')
            await asyncio.sleep(0.25)
        except OSError:
            await self.write_status(status, path)

    async def sleep_after_action(self):
        """ Сон между действиями"""
        
        sleep_time = random.randint(SLEEP_FROM, SLEEP_TO)
        logger.debug(f'{self.twitter_account} | Сон после действия: {sleep_time} секунд')
        await asyncio.sleep(sleep_time)

    async def follow_quest(self, username: str):
        """ Подписываемся на пользователя """
        user_info = await self.twitter_client.request_user_data(username)
        status = await self.twitter_client.follow(user_id=user_info.id)
        if status:
            logger.info(f'{self.twitter_account} | Успешно подписался на {username}')
            return True
        return False

    async def like_and_reetweet_quest(self, tweet_id: str):
        """ Лайкаем и делаем ретвит """
        tweet_id = await self.twitter_client.repost(tweet_id=tweet_id)
        like_status = await self.twitter_client.like(tweet_id=tweet_id)
        if like_status and tweet_id:
            logger.info(f'{self.twitter_account} | Успешно лайкнул и репостнул {tweet_id}')
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
                logger.error(f'{self.twitter_account} | Не удалось изменить имя пользователя')
            
            else:
                logger.success(f'{self.twitter_account} | {self.twitter_account.name} имя было успешно изменено на {new_name}')

            return change_twitter_name_result
        else:
            logger.warning(f'{self.twitter_account} | В имени аккаунта уже есть ❤️ $WELL, текущее имя - {self.twitter_account.name}')
            return True
        
    async def read_image_as_base64_encoded_bytes(self, file_path):
        """ Считываем изображение и превращаем его в байты с помощью PIL """
        
        image = Image.open(file_path)
        with io.BytesIO() as img_buffer:
            image.save(img_buffer, format=image.format)
            image_bytes = img_buffer.getvalue()
        return image_bytes
    
    async def registration(self):
        url = 'https://www.googleapis.com/identitytoolkit/v3/relyingparty/createAuthUri?key=AIzaSyBPmETcQFfpDrw_eB6s8DCkDpYYBt3e8Wg'
        json = {
            "providerId": "twitter.com",
            "continueUri": "https://auth.well3.com/__/auth/handler",
            "customParameter": {}
        }
        headers = {
            "X-Client-Data":"CPWCywE=",
            "content-type": "application/json"
        }
        
        response = await self.async_session.post(
            url=url,
            json=json,
            headers=headers
        )

        answer = response.json()
        auth_url = answer['authUri']
        session_id = answer['sessionId']
        self.async_session.cookies.update({
            'auth_token': self.account_token, 
            'ct0': self.twitter_account.ct0
        })
        response = await self.async_session.get(auth_url)

        soup = BeautifulSoup(response.text, 'html.parser')
        authenticity_token = soup.find('input', attrs={'name': 'authenticity_token'}).get('value')

        url = 'https://api.twitter.com/oauth/authorize'
        data = {
            'authenticity_token': authenticity_token,
            'redirect_after_login': auth_url,
            'oauth_token': auth_url.split("oauth_token=")[-1]
        }
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }

        response = await self.async_session.post(
            url=url,
            data=data,
            headers=headers
        )

        soup = BeautifulSoup(response.text, 'html.parser')
        link = soup.find('a', class_='maintain-context').get('href')

        url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=AIzaSyBPmETcQFfpDrw_eB6s8DCkDpYYBt3e8Wg'
        json = {
            "requestUri": link,
            "sessionId":session_id,
            "returnSecureToken": True,
            "returnIdpCredential": True
        }
        headers = {
            "X-Client-Data": "CJjeygE=",
            "content-type": "application/json"
        }

        response = await self.async_session.post(
            url=url,
            json=json,
            headers=headers
        )

        self.async_session.headers.update({
            "Authorization": response.json()['idToken']
            })
        
        url = 'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=AIzaSyBPmETcQFfpDrw_eB6s8DCkDpYYBt3e8Wg'
        json= {
            "idToken": response.json()['idToken']
        }
        headers={
            "X-Client-Data": "CJjeygE=",
            "content-type": "application/json"
        }

        other_response = await self.async_session.post(
            url=url,
            json=json,
            headers=headers
        )

        url = 'https://api.gm.io/ygpz/link-twitter'        
        json = {
            "oauth": {
                "oauthAccessToken": response.json()['oauthAccessToken'],
                "oauthTokenSecret": response.json()['oauthTokenSecret']
        }}
        
        other_response = await self.async_session.post(
            url=url,
            json=json,
            headers=self.get_headers()
        )

        return response.json()

    def get_headers(self):
        version = self.user_agent.split('Chrome/')[1].split('.')[0]

        headers = {
            'authority': 'api.gm.io',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.id_token,
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://well3.com',
            'pragma': 'no-cache',
            'referer': 'https://well3.com/',
            'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.user_platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }

        return headers
        

    async def send_invite_code(self):
        url = 'https://api.gm.io/ygpz/enter-referral-code'
        json = {
            "code": self.ref_code
        }
        headers = self.get_headers()
        response = await self.async_session.post(
            url=url,
            json=json,
            headers=headers
        )
        
        response_json = response.json()
        if response_json.get("message") == 'Already has referrer':
            logger.warning(f'{self.twitter_account} | Уже был зарегистрирован')
            return True

        if response_json.get("message")== 'Code not found or already used':
            logger.error(f'{self.twitter_account} | Реф код не актуальный либо уже был использован')
            return 'не актульный'
        if not response_json.get("generated", False) or response.status_code != 200:
            return False

        url = "https://api.gm.io/ygpz/generate-codes"
        other_response = await self.async_session.post(
            url=url,
            json={}
        )

        return True

    async def login(self):
        url = 'https://securetoken.googleapis.com/v1/token?key=AIzaSyBPmETcQFfpDrw_eB6s8DCkDpYYBt3e8Wg'
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        headers={
            "X-Client-Data": "CJjeygE=",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        res = await self.async_session.post(
            url=url,
            data=data,
            headers=headers
        )
        self.async_session.headers.update({
            "Authorization": res.json()['access_token']
        })

    async def get_account_data(self):
        version = self.user_agent.split('Chrome/')[1].split('.')[0]
        tries = 0
        while tries < 2:
            
            url = 'https://api.gm.io/ygpz/me'

            headers = {
                'authority': 'api.gm.io',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'access-control-request-headers': 'authorization, content-type',
                'access-control-request-method': 'GET',
                "Sec-Ch-Ua": f'Not_A Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"',
                "Sec-Ch-Ua-Mobile": "?0",
                'cache-control': 'no-cache',
                'origin': 'https://well3.com',
                'pragma': 'no-cache',
                'referer': 'https://well3.com/',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                "Sec-Ch-Ua-Platform": f'"{self.user_platform}"',
                "Referer": "https://well3.com/",
                'user-agent': self.user_agent,
            }

            result = await self.async_session.get(
                url=url,
                headers=headers
            )

            if '<!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>' in result.text:
                try:
                    status = self.get_cf_clearance(response=result)
                except:
                    tries += 1
                    continue
                
                if status:
                    result = await self.async_session.get(
                        url=url,
                        headers=headers
                    )
                    break

            else:
                break
        
        return result.json()
        

    async def get_cf_clearance(self, response):
        site_key = "0x4AAAAAAADnPIDROrmt1Wwj"
        action = "managed"
        c_data = "840ba80c69256ed3"
        chl_page_data = "3gAFo2l2Mbh6anBTbXVvcHlXZElJcVlJQW95OUtRPT2jaXYyuDBBRkxncW9sdkt5YlhSWDBQUVRqdFE9PaFk2gEATzRMcWd5MkRsMDQ5ZWk2WVZpQVZwbUJFMGlvOExHem1CWTNSOVRqeEs1RnZwNXZFdVRaT3lDWTlRaHJnUmtLVmtyMkZoVUxmcXhjVGU5dElkUzgwL1ZqNTJVTTZiR3FTQnk5YnhBSHY5RnFoZlV4SW9aVm01blZVUkhxZndaS1p2Rlo5UzZqSUx6UktlYmNGb21sWkVicnNrK1lJanlzVDg3MlBFVFhYNjhtcDVXTjljNUpDOHVIKzFWTjVzNE5INTdJY3p5eE1XS2RnTGxDVFFBb3o0ajBDWElIamcyMWdNaVY4U2NHRUFLTHQzdnBEbSsyQVBUV2RiN3lGTmlLSKFt2Sw2aHNPUFBrVHovdXh4N0FmN3JyY3dRWVhiRHRBSUs1QkJaZUVrVVJaWXhJPaF0tE1UY3dORFExTnpBeU9TNDFOVGc9"
        url = "https://api.gm.io/ygpz/me"

        if '<head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0' in response.text:
            return True

        html_base64_encoded = base64.b64encode(response.text.encode('utf-8')).decode('utf-8')

        proxy_url = self.account_proxy
        parsed = urlparse(proxy_url)

        proxy_ip = parsed.hostname
        proxy_port = parsed.port
        proxy_log, proxy_pass = parsed.username, parsed.password

        json = {
            "clientKey": API_KEY,
            "task": {
                "type": "TurnstileTask",
                "websiteURL": url,
                "websiteKey": site_key,
                "proxyType": "http",
                "proxyAddress": proxy_ip,
                "proxyPort": proxy_port,
                "proxyLogin": proxy_log,
                "proxyPassword": proxy_pass,
                "cloudflareTaskType": "cf_clearance",
                "htmlPageBase64": html_base64_encoded,
                "userAgent": self.user_agent,
                "pageAction": action,
                "data": c_data,
                "pageData": chl_page_data
            }
        }

        tries = 0
        while tries < 2:

            tries += 1
            
            url = 'https://api.capmonster.cloud/createTask'
            async with self.async_session.post(
                url=url, 
                json=json,
                timeout=120
            ) as response:
                task_id = response.json()['taskId']

            await asyncio.sleep(5)

            url = 'https://api.capmonster.cloud/getTaskResult/'
            json1 = {
                "clientKey": API_KEY,
                "taskId": task_id
            }

            res = False

            secode_try = 0
            while secode_try < 80:
                async with self.async_session.post(
                    url=url, 
                    json=json1, 
                    timeout=60
                ) as response:
                    result = response.json()

                    if result['errorId'] == 0 and result['status'] == "ready":
                        self.cf_clearance = result['solution']['cf_clearance']
                        res = True
                        break

                    elif result['errorId'] != 0:
                        break

                    await asyncio.sleep(5)

            if res == True:
                break
            else:
                raise Exception("Не удалось решить капчу !")

        self.async_session.cookies.update({
            'cf_clearance': self.cf_clearance,
        })

        return True

    async def complete_breath_session(self):

        headers = {
            'authority': 'api.gm.io',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'access-control-request-headers': 'authorization, content-type',
            'access-control-request-method': 'POST',
            'cache-control': 'no-cache',
            'origin': 'https://well3.com',
            'pragma': 'no-cache',
            'referer': 'https://well3.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }

        url = 'https://api.gm.io/ygpz/complete-breath-session'
        headers['content-type'] = None

        res = await self.async_session.post(
            url=url,
            headers=headers,
        )

        
        retry = 0
        while retry < 10:
            if res.status_code == 401 or res.status_code == 400:
                result = await self.registration()
                self.refresh_token = result['refreshToken']
                self.id_token = result['idToken']

                await self.write_to_db()
                res = await self.async_session.post(
                url=url,
                headers=headers,
                )
                retry += 1
            else:
                break
        
        if res.status_code == 401 or res.status_code == 400:
            return False
        return True
    
    async def complete_other_tasks(self, task_name):

        url = f'https://api.gm.io/ygpz/claim-exp/{task_name}'
        headers = {
            'authority': 'api.gm.io',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'access-control-request-headers': 'authorization, content-type',
            'access-control-request-method': 'POST',
            'cache-control': 'no-cache',
            'origin': 'https://well3.com',
            'pragma': 'no-cache',
            'referer': 'https://well3.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }

        res = await self.async_session.post(
            url=url,
            headers=headers,
        )

        retry = 0
        while retry < 10:
            if res.status_code == 400 or res.status_code == 401:
                result = await self.registration()
                self.refresh_token = result['refreshToken']
                self.id_token = result['idToken']
                await self.write_to_db()
                res = await self.async_session.post(
                    url=url,
                    headers=headers,
                )
                answer = res.json()
                if answer.get("message") == 'EXP already claimed':
                    return True
                retry += 1
            else:
                break

        if res.status_code == 401 or res.status_code == 400:
            return False
        return True
    

    async def start_welcome_sign_msg(self, signature):

        eth_client = EthClient(private_key=self.private_key, proxy=self.account_proxy)
        
        # Кодируем сообщение
        message_encoded = encode_defunct(text=signature)
        
        # Подписываем сообщение
        signed_message = eth_client.account.sign_message(message_encoded)
        version = self.user_agent.split('Chrome/')[1].split('.')[0]

        url = 'https://api.gm.io/ygpz/link-wallet'
        headers = {
            'authority': 'api.gm.io',
            'accept': 'application/json',
            'accept-language': 'pl-PL,pl;q=0.9',
            'authorization': self.id_token,
            'content-type': 'application/json',
            'origin': 'https://well3.com',
            'referer': 'https://well3.com/',
            'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.user_platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }
        json = {
            'address': eth_client.account.address,
            'signature': signed_message.signature.hex(),
            'msg': signature,
        }

        res = await self.async_session.post(
            url=url,
            headers=headers,
            json=json
        )
        
        retry = 0
        while retry < 10:
            if res.status_code == 400 or res.status_code == 401:
                result = await self.registration()
                self.refresh_token = result['refreshToken']
                self.id_token = result['idToken']
                await self.write_to_db()
                res = await self.async_session.post(
                    url=url,
                    headers=headers,
                    json=json
                )
                answer = res.json
                retry += 1
            else:
                break

        if res.status_code == 401 or res.status_code == 400:
            return False
        return True

    async def get_abi(self):
        return await async_read_json(WELL_ABI)
    

    async def wait_tx_status(self, client, tx_hash: str, max_wait_time=100) -> None:
        start_time = time.time()
        while True:
            try:
                receipts = await client.w3.eth.get_transaction_receipt(tx_hash)
                status = receipts.get("status")
                if status == 1:
                    return (f"{self.twitter_account} | успешно сминтили книгу | tx hash: "
                            f"https://opbnb.bscscan.com/tx/{tx_hash}")
                elif status is None:
                    await asyncio.sleep(0.3)
                else:
                    return (f"{self.twitter_account} | не удалось сминтить книгу | tx hash: "
                            f"https://opbnb.bscscan.com/tx/{tx_hash}")
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                   return (f"{self.twitter_account} | не удалось сминтить книгу | tx hash: "
                            f"https://opbnb.bscscan.com/tx/{tx_hash}")
                await asyncio.sleep(3)


    async def start_rankup_quest(self, rank, signature):
        
        bnb_client = EthClient(network=Networks.opBNB, private_key=self.private_key, proxy=self.account_proxy)

        balance = await bnb_client.w3.eth.get_balance(bnb_client.account.address)
        if balance <= MIN_BALANCE:
            logger.error(f'{self.twitter_account} | нету достаточного кол-ва bnb в сети opBNB')
            return

        abi = await self.get_abi()
        contract = bnb_client.w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

        rank = int(rank)
        quest_amount = await contract.functions.getQuests(
            int(rank), 
            bnb_client.w3.to_checksum_address(bnb_client.account.address)
        ).call()

        chain_id = await bnb_client.w3.eth.chain_id
        gas_price = await bnb_client.w3.eth.gas_price
        nonce = await bnb_client.w3.eth.get_transaction_count(bnb_client.account.address)
        try:
            gas_limit = await  contract.functions.rankupQuestAmount(
                rank,
                signature=signature,
                questAmount=quest_amount
            ).estimate_gas({'from': bnb_client.account.address})
        except Web3ValidationError:
            logger.error(f'{self.twitter_account} | ошибка в логике контракта')
        except ContractLogicError:
            logger.warning(f'{self.twitter_account} | минт пока недоступен')
            return

        transaction = await contract.functions.rankupQuestAmount(
            rank,
            signature=signature,
            questAmount=quest_amount
        ).build_transaction({
            'chainId': chain_id,
            'gas': int(gas_limit * 1.2),
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_txn = bnb_client.account.sign_transaction(transaction)
        txn_hash = await bnb_client.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        msg = await self.wait_tx_status(client=bnb_client, tx_hash=txn_hash.hex())
        if 'успешно' in msg:
            logger.success(msg)
        else:
            logger.error(msg)

    async def start_daily_quest(self, request_nonce, signature):
        
        bnb_client = EthClient(network=Networks.opBNB, private_key=self.private_key, proxy=self.account_proxy)

        balance = await bnb_client.w3.eth.get_balance(bnb_client.account.address)
        if balance <= MIN_BALANCE:
            logger.error(f'{self.twitter_account} | нету достаточного кол-ва bnb в сети opBNB')
            return

        abi = await self.get_abi()
        contract = bnb_client.w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

        chain_id = await bnb_client.w3.eth.chain_id
        gas_price = await bnb_client.w3.eth.gas_price
        nonce = await bnb_client.w3.eth.get_transaction_count(bnb_client.account.address)
        try:
            gas_limit = await  contract.functions.nonceQuest(
                request_nonce,
                signature=signature
            ).estimate_gas({'from': bnb_client.account.address})
        except Web3ValidationError:
            logger.error(f'{self.twitter_account} | ошибка в логике контракта')
        except ContractLogicError:
            logger.warning(f'{self.twitter_account} | минт пока недоступен')
            return

        transaction = await contract.functions.nonceQuest(
            request_nonce,
            signature=signature
        ).build_transaction({
            'chainId': chain_id,
            'gas': int(gas_limit * 1.2),
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_txn = bnb_client.account.sign_transaction(transaction)
        txn_hash = await bnb_client.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        msg = await self.wait_tx_status(client=bnb_client, tx_hash=txn_hash.hex())
        if 'успешно' in msg:
            logger.success(msg)
        else:
            logger.error(msg)

    async def generate_invite_codes(self):
        headers = self.get_headers()
        url = "https://api.gm.io/ygpz/generate-codes"
        other_response = await self.async_session.post(
            url=url,
            json={},
            headers=headers
        )
        
        retry = 0
        while retry < 10:
            if other_response.status_code == 400 or other_response.status_code == 401:
                result = await self.registration()
                self.refresh_token = result['refreshToken']
                self.id_token = result['idToken']
                headers = self.get_headers()
                await self.write_to_db()
                other_response = await self.async_session.post(
                    url=url,
                    json={},
                    headers=headers
                )
                answer = other_response.json()
                retry += 1
            else:
                break
        if other_response.status_code == 401 or other_response.status_code == 400:
            return False
        return True


async def start_twitter_task(token: str, data: dict, сhoise: int, spare_ref_codes: list | None) -> bool:
    try:
        await TwitterTasksCompleter(token=token, data=data, spare_ref_codes=spare_ref_codes).start_tasks(сhoise)
    except KeyboardInterrupt:
        sys.exit(1)

    except WrongCaptcha:
        pass

    except Exception as error:
        logger.error(f'{token} | Неизвестная ошибка: {error}')
        print(traceback.print_exc())
