import json
import aiofiles


# Функция для асинхронного чтения JSON файла
async def async_read_json(file_path):
    async with aiofiles.open(file_path, 'r') as file:
        data = await file.read()
        return json.loads(data)
    

# Функция для асинхронной записи в JSON файл
async def async_write_json(data, file_path):
    async with aiofiles.open(file_path, 'w') as file:
        await file.write(json.dumps(data, indent=4))


# Функция для обновления и выполнения задач
async def process_tasks(file_path, source_data):
    tasks = await async_read_json(file_path)
    
    # Обновление токенов
    token = 'account_token'
    proxy = 'account_proxy'
    for account in source_data:
        if account[token] not in tasks:
            tasks[account[token]] = {
                "tasks": [
                    {"type": "follow", "target": "GMioETH", "status": "pending"},
                    {"type": "follow", "target": "keung", "status": "pending"},
                    {"type": "follow", "target": "Yogapetz", "status": "pending"},
                    {"type": "retweet", "tweet_id": "1741493362858062271", "status": "pending"},
                    {"type": "retweet", "tweet_id": "1742132803142299950", "status": "pending"},
                    {"type": "retweet", "tweet_id": "1742530102221771001", "status": "pending"},
                    {"type": "retweet", "tweet_id": "1743249418357194952", "status": "pending"},
                    {"type": "retweet", "tweet_id": "1743364888586764724", "status": "pending"},
                    {"type": "update_banner", "status": "pending"}
                ],
                "proxy": account[proxy]
            }
            
        if tasks[account[token]]['proxy'] != account[proxy]:
            tasks[account[token]]['proxy'] = account[proxy]

    for token, data in tasks.items():
        if len(data['tasks']) != 9:
            data['tasks'] += [
                {"type": "retweet", "tweet_id": "1743249418357194952", "status": "pending"},
                {"type": "retweet", "tweet_id": "1743364888586764724", "status": "pending"},
            ]

    await async_write_json(tasks, file_path)

    return tasks, len(tasks)


# Функция для очистки от задач которые не актуальны
async def clear_complete(db):
    actual_accounts = {}
    for token, data in db.items():
        for task in data['tasks']:
            if task['status'] == 'pending':
                actual_accounts[token] = data
    
    return actual_accounts
