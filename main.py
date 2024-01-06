import sys
import itertools

import asyncio

from data.config import ACCOUNTS, PROXYS, CODES, logger, DB
from utils.policy import set_windows_event_loop_policy
from utils.validate_token import validate_token
from utils.db_func import process_tasks, clear_complete
from utils.create_files import create_files
from tasks.twitter_client import start_twitter_task


def get_accounts_info(path): 
    with open(path, 'r', encoding='utf-8-sig') as file:
        if path == ACCOUNTS:
            info: list[str] = [validate_token(input_string=row.strip()) for row in file]
        else:
            info: list[str] = [row.strip() for row in file]
    return info


async def main():
    accounts_list: list[str] = get_accounts_info(ACCOUNTS)
    proxies_list: list[str] = get_accounts_info(PROXYS)
    ref_codes: list[str] = get_accounts_info(CODES)

    cycled_proxies_list = itertools.cycle(proxies_list) if proxies_list else None
    
    formatted_accounts_list: list = [
        {
            'account_token': current_account,
            'account_proxy': next(cycled_proxies_list) if cycled_proxies_list else None,
            'ref_code': ref_codes.pop(0) if ref_codes else None
        } for current_account in accounts_list
    ]

    db, len_db = await process_tasks(file_path=DB, source_data=formatted_accounts_list)
    
    logger.info(f'Загружено в accounts.txt {len(accounts_list)} аккаунтов \n'
                f'\t\t\t\t\t\t\tЗагружено в proxys.txt {len(proxies_list)} прокси \n'
                f'\t\t\t\t\t\t\tЗагружено в базу данных {len_db} токенов \n')
    
    if len_db == 0 and not formatted_accounts_list:
        logger.error('Вы не добавили токены в файл и в базе данных тоже пусто!')
        sys.exit(1)

    tasks: list = []
    for token, data in db.items():
        tasks.append(asyncio.create_task(start_twitter_task(token=token, data=data)))

    await asyncio.wait(tasks)

if __name__ == '__main__':
    create_files()
    set_windows_event_loop_policy()
    asyncio.run(main())
