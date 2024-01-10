import json
import aiofiles
import asyncio

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
        {"type": "retweet", "tweet_id": "1745143426642030966", "status": "pending"},
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
        {"task": "retweet-keung-1745143426642030966", "status": "pending"},
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
                'retweet-keung-1745143426642030966', 
                'retweet-yogapetz-1745127428039847937'
            ]:
                continue

            # Ищем соответствующую задачу в первоначальном списке
            for task in platform_list:
                if not task["task"].startswith('retweet') or actual_task["task"] in [
                'retweet-keung-1745143426642030966', 
                'retweet-yogapetz-1745127428039847937'
                ]:
                    continue

                if task['status'] == 'completed':
                    if actual_task['task'] == task['task']:
                        if actual_task['status'] != task['status']:
                            actual_task['status'] = task['status']


        new_task = {"type": "retweet", "tweet_id": "1745127428039847937", "status": "pending"},
        new_task2 = {"type": "retweet", "tweet_id": "1745143426642030966", "status": "pending"},

        if len(data['tasks']) != len(tasks_list):
            if new_task not in data['tasks']:
                data['tasks'] += new_task
            if new_task2 not in data['tasks']:
                 data['tasks'] += new_task2
        
        new_task = {"task": "retweet-keung-1745143426642030966", "status": "pending"},
        new_task2 = {"task": "retweet-yogapetz-1745127428039847937", "status": "pending"},

        if len(data['platform']) != len(platform_list):
            if new_task not in data['platform']:
                data['platform'] += new_task
            if new_task2 not in data['platform']:
                 data['platform'] += new_task2

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
