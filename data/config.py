import os
import sys
from pathlib import Path

from loguru import logger


if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent.absolute()
else:
    ROOT_DIR = Path(__file__).parent.parent.absolute()


STATUS_DIR = os.path.join(ROOT_DIR, 'status')
ACCOUNTS_DIR = os.path.join(ROOT_DIR, 'accounts')
DB_DIR = os.path.join(STATUS_DIR, 'token_db')

LOG = os.path.join(STATUS_DIR, 'log.txt')
SUSPENDED = os.path.join(STATUS_DIR, 'suspended.txt')
LOCKED = os.path.join(STATUS_DIR, 'locked.txt')
BAD_TOKEN = os.path.join(STATUS_DIR, 'bad_token.txt')
ACCOUNTS = os.path.join(ACCOUNTS_DIR, 'accounts.txt')
PROXYS = os.path.join(ACCOUNTS_DIR, 'proxys.txt')
BANNER_IMAGE = os.path.join(ACCOUNTS_DIR, 'banner.jpg')
DB = os.path.join(DB_DIR, 'tasks.json')

IMPORTANT_FILES = [ACCOUNTS, PROXYS, BAD_TOKEN, LOCKED, LOG, SUSPENDED, DB]

logger.add(LOG, format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}', level='DEBUG')