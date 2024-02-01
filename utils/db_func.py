import json
import aiofiles
import asyncio
import shutil

from data.config import BACKUP_DB, DB, BAD_TOKEN, BAD_PROXY, BAD_PK, DB_DIR
from data.config import logger


write_lock = asyncio.Lock()


# Функция для асинхронного чтения JSON файла
async def async_read_json(file_path):
    async with write_lock: 
        async with aiofiles.open(file_path, 'r') as file:
            data = await file.read()
            return json.loads(data)
    

# Функция для асинхронной записи в JSON файл
async def async_write_json(data, file_path):
    async with write_lock: 
        async with aiofiles.open(file_path, 'w') as file:
            await file.write(json.dumps(data, indent=4))


# Функция для обновления и выполнения задач
async def process_tasks(file_path, source_data):
    tasks = await async_read_json(file_path)

    tasks_list = [
        {"type": "follow", "target": "GMioETH", "status": "pending"},
        {"type": "follow", "target": "keung", "status": "pending"},
        {"type": "follow", "target": "Yogapetz", "status": "pending"},
        {"type": "retweet", "tweet_id": "1741493362858062271", "status": "completed"},
        {"type": "retweet", "tweet_id": "1742132803142299950", "status": "completed"},
        {"type": "retweet", "tweet_id": "1742530102221771001", "status": "completed"},
        {"type": "retweet", "tweet_id": "1743249418357194952", "status": "completed"},
        {"type": "retweet", "tweet_id": "1743364888586764724", "status": "completed"},
        {"type": "update_banner", "status": "pending"},
        {"type": "retweet", "tweet_id": "1744373398934003773", "status": "completed"},
        {"type": "retweet", "tweet_id": "1745127428039847937", "status": "pending"},
        {"type": "retweet", "tweet_id": "1745143426642030966", "status": "completed"},
        {"type": "retweet", "tweet_id": "1749049904889213387", "status": "completed"},
        {"type": "retweet", "tweet_id": "1750523880463340019", "status": "pending"},
        {"type": "retweet", "tweet_id": "1750535387095691606", "status": "pending"},
    ]

    platform_list = [
        {"task": "set-well-twitter-profile-banner", "status": "pending"},
        {"task": "retweet-yogapetz-1743364888586764724", "status": "completed"},
        {"task": "retweet-yogapetz-1742530102221771001", "status": "completed"},
        {"task": "retweet-Aizcalibur-1743249418357194952", "status": "completed"},
        {"task": "retweet-keung-1741493362858062271", "status": "completed"},
        {"task": "follow-yogapetz", "status": "pending"},
        {"task": "follow-keung", "status": "pending"},
        {"task": "follow-gmio", "status": "pending"},
        {"task": "retweet-BNBCHAIN-1744373398934003773", "status": "completed"},
        {"task": "retweet-yogapetz-1745127428039847937", "status": "pending"},
        {"task": "retweet-keung-1745143426642030966", "status": "completed"},
        {"task": "retweet-yogapetz-1749049904889213387", "status": "completed"},
        {"task": "retweet-yogapetz-1750523880463340019", "status": "pending"},
        {"task": "retweet-CyberKongz-1750535387095691606", "status": "pending"},
        {"task": "share-phaver-open", "status": "pending"},
        {"task": "share-phaver-holder", "status": "pending"},
        {"task": "join-eesee", "status": "pending"},       
    ]

    # Обновление токенов
    token = 'account_token'
    proxy = 'account_proxy'
    for account in source_data:
        if account[token] not in tasks:
            tasks[account[token]] = {
                
                # Зареган аккаунт или нет
                "register": False,

                # Реферальный код
                "ref_code": account['ref_code'],

                # Прокси который используется
                "proxy": account[proxy],

                # Токен
                "id_token": None,

                # Токен
                "refresh_token": None,

                "private_key": account['private_key'],

                "twitter_account_status": None,
                # Задачи твиттер
                "tasks": tasks_list,

                # Задания на платформе
                "platform": platform_list,
            }
            
        if tasks[account[token]]['proxy'] != account[proxy]:
            tasks[account[token]]['proxy'] = account[proxy]

        if tasks[account[token]]['ref_code'] != account['ref_code']:
            tasks[account[token]]['ref_code'] = account['ref_code']

        if tasks[account[token]]['private_key'] != account['private_key']:
            tasks[account[token]]['private_key'] = account['private_key']

        

    # Добавляем обновления в базу данных
    for token, data in tasks.items():

        # Актуализируем новые задачи

        # Проходим по фактической базе данных обновляем статусы неактуальных задач
        for actual_task in data['tasks']:
            if actual_task["type"] != "retweet":
                continue

            # Ищем соответствующую задачу в первоначальном списке
            for task in tasks_list:
                if task["type"] != "retweet":
                    continue

                if task['status'] == 'completed':
                    if actual_task['tweet_id'] == task['tweet_id']:
                        if actual_task['status'] != task['status']:
                            actual_task['status'] = task['status']
        
        # Проходим по фактической базе данных обновляем статусы неактуальных задач
        for actual_task in data['platform']:
            if not actual_task["task"].startswith('retweet') or actual_task["task"] in [
                'retweet-yogapetz-1745127428039847937', 
                'retweet-yogapetz-1750523880463340019',
                'retweet-CyberKongz-1750535387095691606',
            ]:
                continue

            # Ищем соответствующую задачу в первоначальном списке
            for task in platform_list:
                if not task["task"].startswith('retweet') or actual_task["task"] in [
                    'retweet-yogapetz-1745127428039847937', 
                    'retweet-yogapetz-1750523880463340019',
                    'retweet-CyberKongz-1750535387095691606',
                ]:
                    continue

                if task['status'] == 'completed':
                    if actual_task['task'] == task['task']:
                        if actual_task['status'] != task['status']:
                            actual_task['status'] = task['status']


        # new_task = {"type": "retweet", "tweet_id": "1750523880463340019", "status": "pending"},
        # new_task2 = {"type": "retweet", "tweet_id": "1750535387095691606", "status": "pending"},

        # if len(data['tasks']) != len(tasks_list):
        #     if new_task not in data['tasks']:
        #         data['tasks'] += new_task
        #     if new_task2 not in data['tasks']:
        #          data['tasks'] += new_task2
        
        new_task = {"task": "share-phaver-open", "status": "pending"},
        new_task2 = {"task": "share-phaver-holder", "status": "pending"},
        new_task3 = {"task": "join-eesee", "status": "pending"},       

        if len(data['platform']) != len(platform_list):
            if new_task not in data['platform']:
                data['platform'] += new_task
            if new_task2 not in data['platform']:
                 data['platform'] += new_task2
            if new_task3 not in data['platform']:
                 data['platform'] += new_task3

    await async_write_json(tasks, file_path)

    return tasks, len(tasks)


# Функция для очистки от задач которые не актуальны
async def clear_complete(db):
    actual_accounts = {}
    for token, data in db.items():
        for task in data['tasks']:
            if task['status'] == 'pending':
                actual_accounts[token] = data

        for task in data['platform']:
            if task['status'] == 'pending':
                actual_accounts[token] = data
    
    return actual_accounts


def clear_db_from_bad_tokens():
    logger.info(f'Делаю бэкап db в {DB_DIR}')
    shutil.copy(DB, BACKUP_DB)
    with open(DB, "r") as f:
        tasks_data = json.load(f)

    bad_accounts = 0
    for account_id, task_data in tasks_data.items():
        if task_data["twitter_account_status"] in ["SUSPENDED", "BAD_TOKEN"]: 
            bad_accounts += 1
            with open(BAD_TOKEN, "a") as f:
                f.write(account_id + "\n")
            with open(BAD_PK, "a") as f:
                f.write(task_data["private_key"] + "\n")
            with open(BAD_PROXY, "a") as f:
                f.write(task_data["proxy"] + "\n")

    if bad_accounts > 0:

        with open(BAD_TOKEN, 'r', encoding='utf-8-sig') as file:
            bad_tokens: list[str] = [row.strip() for row in file]

        for token in bad_tokens:
            tasks_data.pop(token)

        with open("status/token_db/tasks.json", "w") as f:
            f.write(json.dumps(tasks_data, indent=4))

        msg = (
            f'База данных была успешно очищена от {len(bad_tokens)} аккаунтов.\n'
            f'\t\tВсе плохие токен были сохранены в: {BAD_TOKEN}\n'
            f'\t\tВсе приватные ключи от плохих токенов были сохранены в: {BAD_PK}\n'
            f'\t\tВсе прокси от плохих токенов были сохранены в: {BAD_PROXY}\n'
        )

        logger.info(msg) 
    
    else:
        logger.info('В базе данных нет плохих токенов!')