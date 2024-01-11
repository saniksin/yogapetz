import json
from data.config import DB


def bad_accounts_count():
    with open("status/token_db/tasks.json", "r") as f:
        rasks_data = json.load(f)

    bad_accounts = 0
    for account_id, account_data in rasks_data.items():
        if account_data["twitter_account_status"] in ["SUSPENDED", "BAD_TOKEN", "LOCKED"]: #"SUSPENDED", "BAD_TOKEN", 
            bad_accounts += 1
    
    return bad_accounts