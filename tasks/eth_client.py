
import random
from typing import Optional

from fake_useragent import UserAgent
from web3 import Web3
from web3.eth import AsyncEth
from eth_account.signers.local import LocalAccount

from data.models import (
    Network,
    Networks,
    Contracts,
    Transactions,
    Wallet,
)

class EthClient:
    network: Network
    account: Optional[LocalAccount]
    w3: Web3

    def __init__(self, private_key: Optional[str] = None, network: Network = Networks.Ethereum,
                 proxy: Optional[str] = None) -> None:
        self.network = network
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'user-agent': UserAgent().chrome
        }
        self.proxy = proxy
        self.connector = None

        self.w3 = Web3(
            provider=Web3.AsyncHTTPProvider(
                endpoint_uri=self.network.rpc,
                request_kwargs={'proxy': self.proxy, 'headers': self.headers}
            ),
            modules={'eth': (AsyncEth,)},
            middlewares=[]
        )
        
        if private_key:
            self.account = self.w3.eth.account.from_key(private_key=private_key)
        else:
            self.account = self.w3.eth.account.create(extra_entropy=str(random.randint(1, 999_999_999)))
        self.wallet = Wallet(self)
        self.contracts = Contracts(self)
        self.transactions = Transactions(self)
