from typing import Optional
from decimal import Decimal
from typing import Union
from dataclasses import dataclass


import asyncio
import requests
from web3 import Web3
from eth_utils import to_wei, from_wei
from eth_typing import ChecksumAddress
from web3.contract import AsyncContract

from data.config import logger


CONTRACT_ADDRESS = '0x73A0469348BcD7AAF70D9E34BBFa794deF56081F'


@dataclass
class API:
    url: str
    docs: str


class TokenAmount:
    Wei: int
    Ether: Decimal
    decimals: int

    def __init__(self, amount: Union[int, float, str, Decimal], decimals: int = 18, wei: bool = False) -> None:
        """
        A token amount instance.

        :param Union[int, float, str, Decimal] amount: an amount
        :param int decimals: the decimals of the token (18)
        :param bool wei: the 'amount' is specified in Wei (False)
        """
        if wei:
            self.Wei: int = amount
            self.Ether: Decimal = Decimal(str(amount)) / 10 ** decimals

        else:
            self.Wei: int = int(Decimal(str(amount)) * 10 ** decimals)
            self.Ether: Decimal = Decimal(str(amount))

        self.decimals = decimals


class Network:
    def __init__(self, name: str, rpc: str, chain_id: Optional[int] = None, tx_type: int = 0,
                 coin_symbol: Optional[str] = None, explorer: Optional[str] = None, api: Optional[API] = None
                 ) -> None:
        self.name: str = name.lower()
        self.rpc: str = rpc
        self.chain_id: Optional[int] = chain_id
        self.tx_type: int = tx_type
        self.coin_symbol: Optional[str] = coin_symbol
        self.explorer: Optional[str] = explorer
        self.api: Optional[API] = api

        if not self.chain_id:
            try:
                self.chain_id = Web3(Web3.HTTPProvider(self.rpc)).eth.chain_id
            except:
                pass

        if not self.coin_symbol:
            try:
                response = requests.get('https://chainid.network/chains.json').json()
                for network in response:
                    if network['chainId'] == self.chain_id:
                        self.coin_symbol = network['nativeCurrency']['symbol']
                        break
            except:
                pass

        if self.coin_symbol:
            self.coin_symbol = self.coin_symbol.upper()


class Networks:
    # Mainnets
    Ethereum = Network(
        name='ethereum',
        rpc='https://rpc.ankr.com/eth/',
        chain_id=1,
        tx_type=2,
        coin_symbol='ETH',
        explorer='https://etherscan.io/',
        api=API(url='https://api.etherscan.io/api', docs='https://docs.etherscan.io/'),
    )

    opBNB = Network(
        name='opbnb',
        rpc='https://opbnb-mainnet-rpc.bnbchain.org',
        chain_id=204,
        tx_type=0,
        coin_symbol='BNB',
        explorer='https://opbnb.bscscan.com/',
        api=API(url='https://api.arbiscan.io/api', docs='https://docs.arbiscan.io/'),
    )



@dataclass
class DefaultABIs:
    Token = [
        {
            'constant': True,
            'inputs': [],
            'name': 'name',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'symbol',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'totalSupply',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'decimals',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': 'who', 'type': 'address'}],
            'name': 'balanceOf',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': '_owner', 'type': 'address'}, {'name': '_spender', 'type': 'address'}],
            'name': 'allowance',
            'outputs': [{'name': 'remaining', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_spender', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'approve',
            'outputs': [],
            'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_to', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'transfer',
            'outputs': [], 'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        }]


class Contracts:
    def __init__(self, client) -> None:
        self.client = client

    async def get_contract(self,
                           contract_address: ChecksumAddress,
                           abi: Union[list, dict] = DefaultABIs
                           ) -> AsyncContract:
        return self.client.w3.eth.contract(address=contract_address, abi=abi)


unit_denominations = {
    'wei': 10 ** -18,
    'kwei': 10 ** -15,
    'mwei': 10 ** -12,
    'gwei': 10 ** -9,
    'szabo': 10 ** -6,
    'finney': 10 ** -3,
    'ether': 1,
    'kether': 10 ** 3,
    'mether': 10 ** 6,
    'gether': 10 ** 9,
    'tether': 10 ** 12,
}


class AutoRepr:
    def __repr__(self) -> str:
        values = ('{}={!r}'.format(key, value) for key, value in vars(self).items())
        return '{}({})'.format(self.__class__.__name__, ', '.join(values))


class Unit(AutoRepr):
    """
    An instance of an Ethereum unit.

    Attributes:
        unit (str): a unit name.
        decimals (int): a number of decimals.
        Wei (int): the amount in Wei.
        KWei (Decimal): the amount in KWei.
        MWei (Decimal): the amount in MWei.
        GWei (Decimal): the amount in GWei.
        Szabo (Decimal): the amount in Szabo.
        Finney (Decimal): the amount in Finney.
        Ether (Decimal): the amount in Ether.
        KEther (Decimal): the amount in KEther.
        MEther (Decimal): the amount in MEther.
        GEther (Decimal): the amount in GEther.
        TEther (Decimal): the amount in TEther.

    """
    unit: str
    decimals: int
    Wei: int
    KWei: Decimal
    MWei: Decimal
    GWei: Decimal
    Szabo: Decimal
    Finney: Decimal
    Ether: Decimal
    KEther: Decimal
    MEther: Decimal
    GEther: Decimal
    TEther: Decimal

    def __init__(self, amount: Union[int, float, str, Decimal], unit: str) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.
            unit (str): a unit name.

        """
        self.unit = unit
        self.decimals = 18
        self.Wei = to_wei(amount, self.unit)
        self.KWei = from_wei(self.Wei, 'kwei')
        self.MWei = from_wei(self.Wei, 'mwei')
        self.GWei = from_wei(self.Wei, 'gwei')
        self.Szabo = from_wei(self.Wei, 'szabo')
        self.Finney = from_wei(self.Wei, 'finney')
        self.Ether = from_wei(self.Wei, 'ether')
        self.KEther = from_wei(self.Wei, 'kether')
        self.MEther = from_wei(self.Wei, 'mether')
        self.GEther = from_wei(self.Wei, 'gether')
        self.TEther = from_wei(self.Wei, 'tether')

    def __add__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(self.Wei + other.Wei)

        elif isinstance(other, int):
            return Wei(self.Wei + other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei + GWei(other).GWei)

            else:
                return Ether(self.Ether + Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __radd__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(other.Wei + self.Wei)

        elif isinstance(other, int):
            return Wei(other + self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei + self.GWei)

            else:
                return Ether(Ether(other).Ether + self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __sub__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(self.Wei - other.Wei)

        elif isinstance(other, int):
            return Wei(self.Wei - other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei - GWei(other).GWei)

            else:
                return Ether(self.Ether - Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rsub__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(other.Wei - self.Wei)

        elif isinstance(other, int):
            return Wei(other - self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei - self.GWei)

            else:
                return Ether(Ether(other).Ether - self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __mul__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(self.Ether)) * Decimal(str(other.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(self.Wei * other.Wei / denominations)

        elif isinstance(other, int):
            return Wei(self.Wei * other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei * GWei(other).GWei)

            else:
                return Ether(self.Ether * Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rmul__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(other.Ether)) * Decimal(str(self.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(other.Wei * self.Wei / denominations)

        elif isinstance(other, int):
            return Wei(other * self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei * self.GWei)

            else:
                return Ether(Ether(other).Ether * self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __truediv__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(self.Ether)) / Decimal(str(other.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(self.Wei / other.Wei * denominations)

        elif isinstance(other, int):
            return Wei(self.Wei / Decimal(str(other)))

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei / GWei(other).GWei)

            else:
                return Ether(self.Ether / Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rtruediv__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(other.Ether)) / Decimal(str(self.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(other.Wei / self.Wei * denominations)

        elif isinstance(other, int):
            return Wei(Decimal(str(other)) / self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei / self.GWei)

            else:
                return Ether(Ether(other).Ether / self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __iadd__(self, other):
        return self.__add__(other)

    def __isub__(self, other):
        return self.__sub__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __itruediv__(self, other):
        return self.__truediv__(other)

    def __lt__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei < other.Wei

        elif isinstance(other, int):
            return self.Wei < other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei < GWei(other).GWei

            else:
                return self.Ether < Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __le__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei <= other.Wei

        elif isinstance(other, int):
            return self.Wei <= other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei <= GWei(other).GWei

            else:
                return self.Ether <= Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __eq__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei == other.Wei

        elif isinstance(other, int):
            return self.Wei == other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei == GWei(other).GWei

            else:
                return self.Ether == Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __ne__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei != other.Wei

        elif isinstance(other, int):
            return self.Wei != other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei != GWei(other).GWei

            else:
                return self.Ether != Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __gt__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei > other.Wei

        elif isinstance(other, int):
            return self.Wei > other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei > GWei(other).GWei

            else:
                return self.Ether > Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __ge__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei >= other.Wei

        elif isinstance(other, int):
            return self.Wei >= other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei >= GWei(other).GWei

            else:
                return self.Ether >= Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")


class Wei(Unit):
    """
    An instance of a Wei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'wei')


class MWei(Unit):
    """
    An instance of a MWei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'mwei')


class GWei(Unit):
    """
    An instance of a GWei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'gwei')


class Szabo(Unit):
    """
    An instance of a Szabo unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'szabo')


class Finney(Unit):
    """
    An instance of a Finney unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'finney')


class Ether(Unit):
    """
    An instance of an Ether unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'ether')


class KEther(Unit):
    """
    An instance of a KEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'kether')


class MEther(Unit):
    """
    An instance of a MEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'mether')


class GEther(Unit):
    """
    An instance of a GEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'gether')


class TEther(Unit):
    """
    An instance of a TEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'tether')


class Transactions:
    def __init__(self, client):
        self.client = client

    @staticmethod
    async def gas_price(w3: Web3, max_retries=30) -> Wei:
        retries = 0
        while retries < max_retries:
            try:
                return Wei(await w3.eth.gas_price)
            except asyncio.exceptions.TimeoutError:
                logger.debug(f"Retry {retries + 1}/{max_retries} due to TimeoutError ETH gas price")
                retries += 1

        raise ValueError(f"Unable to get gas price after {max_retries} retries")


class Wallet:
    def __init__(self, client) -> None:
        self.client = client

    async def balance(self, token_address: Optional[str] = None,
                      address: Optional[ChecksumAddress] = None) -> Union[Wei, TokenAmount]:
        if not address:
            address = self.client.account.address

        address = Web3.to_checksum_address(address)
        if not token_address:
            return Wei(await self.client.w3.eth.get_balance(account=address))

        token_address = Web3.to_checksum_address(token_address)
        contract = await self.client.contracts.get_contract(contract_address=token_address)
        return TokenAmount(
            amount=await contract.functions.balanceOf(address).call(),
            decimals=await contract.functions.decimals().call(),
            wei=True
        )

    async def nonce(self, address: Optional[ChecksumAddress] = None) -> int:
        if not address:
            address = self.client.account.address
        return await self.client.w3.eth.get_transaction_count(address)