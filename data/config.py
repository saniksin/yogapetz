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
EXTENSION_DIR = os.path.join(ROOT_DIR, 'extensions')
ABIS_DIR = os.path.join(ROOT_DIR, 'abis')

ACCOUNTS = os.path.join(ACCOUNTS_DIR, 'accounts.txt')
PROXYS = os.path.join(ACCOUNTS_DIR, 'proxys.txt')
CODES = os.path.join(ACCOUNTS_DIR, 'ref_code.txt')
PROBLEMS = os.path.join(STATUS_DIR, 'problems.txt')
LOG = os.path.join(STATUS_DIR, 'log.txt')
DB = os.path.join(DB_DIR, 'tasks.json')
ACTUAL_REF = os.path.join(ACCOUNTS_DIR, 'actual_ref.txt')
PRIVATE_KEYS = os.path.join(ACCOUNTS_DIR, 'private_keys.txt')
NFT_STATS = os.path.join(STATUS_DIR, 'nft_stats.csv')

WELL_ABI = os.path.join(ABIS_DIR, 'well3.json')
METAMASK = os.path.join(EXTENSION_DIR, 'metamask')
BANNER_IMAGE = os.path.join(ACCOUNTS_DIR, 'banner.jpg')

IMPORTANT_FILES = [ACCOUNTS, PROXYS, CODES, PROBLEMS, LOG, DB, ACTUAL_REF, PRIVATE_KEYS, NFT_STATS]

logger.add(LOG, format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}', level='DEBUG')