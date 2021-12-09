"""
API for Uniswap v3 distributed exchange (uniswap.exchange)
- price info is pulled from the smart contract via uniswap-python library
- volume is pulled manually via eth.getLogs
- liquidity is pulled manually via erc20 balance checks on the pair contract
"""
import logging
from web3 import Web3
import time
import requests

from .base_exchange import Daily24hChangeTrackedAPI, NoLiquidityException
from .erc20_abi import erc20_abi
from secret_info import ETHEREUM_NODE_URL
from constants import SECONDS_PER_ETH_BLOCK
from token_class import Token, NoTokenMatchError
from weighted_average import WeightedAverage
from uniswap import Uniswap

# list of exchange contract addresses. each pair has a unique address.
# token0 name, token1 name, uniswap exchange address, fee amount
# fee is in in basis points. so 3000 = 0.3%
exchanges = (
("0xBTC", "WETH", "0xaFF587846a44aa086A6555Ff69055D3380fD379a", 10000),
)

_TIME_BETWEEN_VOLUME_UPDATES = 60 * 60  # 1 hour. WARNING: don't change this without refactoring hourly volume logic
# if less than this many tokens in pair, don't use it for price
_MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS = 0.1
# if less than this many tokens in pair, don't check its volume
_MINIMUM_ALLOWED_LIQUIDITY_TOKENS_TO_CHECK_VOLUME = 10
# fee to use by defualt, in basis points. 3000 = 0.3%
_DEFAULT_PAIR_FEE = 3000


class PairNotDefinedError(Exception):
    pass

def getExchangeAddressesForToken(name):
    return [i[2] for i in exchanges if i[0].lower() == name.lower() or i[1].lower() == name.lower()]
def getTokensFromExchangeAddress(exchange_address):
    return [(i[0], i[1], i[3]) for i in exchanges if i[2].lower() == exchange_address.lower()][0]
def getExchangeAddressForTokenPair(first_token_name, second_token_name, fee_to_match):
    token_addresses = sorted([Token().from_symbol(first_token_name).address.lower(),
                              Token().from_symbol(second_token_name).address.lower()])
    for token1_name, token2_name, address, fee in exchanges:
        if (token1_name in [first_token_name, second_token_name]
            and token2_name in [first_token_name, second_token_name]
            and fee == fee_to_match):
            return (address,
                    Token().from_address(token_addresses[0]).symbol,
                    Token().from_address(token_addresses[1]).symbol)
    raise PairNotDefinedError(f"No pair {first_token_name}-{second_token_name} found")

def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

def ether_to_wei(amount_in_ether):
    return int(amount_in_ether * 1000000000000000000.0)

def from_u256_twos_complement(twos_complemented_number):
    sign_bit = (1 << 255)
    if twos_complemented_number & sign_bit != 0:
        return twos_complemented_number - (1 << 256)
    else:
        return twos_complemented_number


def get_reserves(web3, token0_name, token1_name, fee):
    """get the reserves, in tokens, of a particular uniswap v3 pool"""
    exchange_address, first_token_name, second_token_name = getExchangeAddressForTokenPair(token0_name, token1_name, fee)

    token0_contract = web3.eth.contract(address=Token().from_symbol(token0_name).address, abi=erc20_abi)
    token0_balance = (token0_contract.functions.balanceOf(exchange_address).call()
                      / 10**Token().from_symbol(token0_name).decimals)

    token1_contract = web3.eth.contract(address=Token().from_symbol(token1_name).address, abi=erc20_abi)
    token1_balance = (token1_contract.functions.balanceOf(exchange_address).call()
                      / 10**Token().from_symbol(token1_name).decimals)

    return token0_balance, token1_balance


def get_price(uniswap_api, token0_name, token1_name, fee):
    """Get the price at a particular uniswap v3 pool, in terms of token0 / token1"""
    if token0_name == "ETH":
        token0_address = "0x0000000000000000000000000000000000000000"
        token0_decimals = 18
    else:
        token0_address = Token().from_symbol(token0_name).address
        token0_decimals = Token().from_symbol(token0_name).decimals

    if token1_name == "ETH":
        token1_address = "0x0000000000000000000000000000000000000000"
        token1_decimals = 18
    else:
        token1_address = Token().from_symbol(token1_name).address
        token1_decimals = Token().from_symbol(token1_name).decimals

    price = (uniswap_api.get_price_input(token1_address,
                                         token0_address,
                                         1 * 10**token1_decimals,
                                         fee)
             / 10 ** token0_decimals)

    return price


class Uniswapv3API(Daily24hChangeTrackedAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        try:
            # self._exchange_addresses = getExchangeAddressesForToken(currency_symbol)
            self._decimals = Token().from_symbol(currency_symbol).decimals
        except IndexError:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to token_class.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "Uniswap v3"
        self.command_names = ["uniswap"]
        self.short_url = "https://bit.ly/35nae4n"  # main uniswap pre-selected to 0xbtc
        self.volume_eth = 0

        self._hourly_volume_tokens = []  # list of volume for each of the last N hours
        self._time_volume_last_updated = 0

        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        self._uniswap_api = Uniswap(address=None, private_key=None, version=3, web3=self._w3)
        # self._exchanges = [self._w3.eth.contract(address=a, abi=exchange_abi) for a in self._exchange_addresses]

    @property
    def number_of_hours_covered_by_volume(self):
        return len(self._hourly_volume_tokens)

    def _is_time_to_update_volume(self):
        return time.time() - self._time_volume_last_updated > _TIME_BETWEEN_VOLUME_UPDATES

    def _mark_volume_as_updated(self):
        self._time_volume_last_updated = time.time()

    async def _get_volume_for_pair(self, token0_address, token1_address, fee, num_hours_into_past=1, current_eth_block=None, timeout=10.0):
        volume_tokens = 0  # volume in units of <self.currency_symbol> tokens
        volume_pair = 0  # volume in units of the paired token

        token0_address, token1_address = sorted([token0_address, token1_address])
        token0_decimals = Token().from_address(token0_address).decimals
        token1_decimals = Token().from_address(token1_address).decimals

        # https://docs.uniswap.org/reference/core/interfaces/pool/IUniswapV3PoolEvents
        swap_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
        collect_topic = "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"
        # this event seems to throw when a collect occurs, but only includes the first 3 parameters?
        cloned_collect_topic = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"

        exchange_address, _, _ = getExchangeAddressForTokenPair(
            Token().from_address(token0_address).symbol,
            Token().from_address(token1_address).symbol,
            fee)

        if current_eth_block is None:
            current_eth_block = self._w3.eth.blockNumber

        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*num_hours_into_past / SECONDS_PER_ETH_BLOCK)),
                'toBlock': current_eth_block - 1,
                'address': exchange_address}):
            topic0 = self._w3.toHex(event['topics'][0])
            if topic0 == swap_topic:
                receipt = self._w3.eth.getTransactionReceipt(event['transactionHash'])
                # address sender (router address ususally)
                router_address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                # address recipient
                buyer_address = self._w3.toChecksumAddress(event['topics'][2][-20:])

                data = event['data'][2:] if event['data'].startswith('0x') else event['data']
                # int256 amount 0 (delta of the token0 balance of the pool)
                amount_0 = from_u256_twos_complement(self._w3.toInt(hexstr=data[0:64])) / 10**token0_decimals
                # int256 amount 1 (delta of the token1 balance of the pool)
                amount_1 = from_u256_twos_complement(self._w3.toInt(hexstr=data[64:128])) / 10**token1_decimals
                # uint160 sqrtPriceX96 unused
                # uint128 liquidity unused
                # int24 tick unused

                # print('swap in tx', self._w3.toHex(event['transactionHash']))
                # print(f'amount_0: {amount_0}, amount_1: {amount_1}')

                if Token().from_address(token0_address).symbol.lower() == self.currency_symbol.lower():
                    # token0 is the tracked currency symbol
                    volume_tokens += abs(amount_0)
                    volume_pair += abs(amount_1)
                elif Token().from_address(token1_address).symbol.lower() == self.currency_symbol.lower():
                    # token1 is the tracked currency symbol
                    volume_tokens += abs(amount_1)
                    volume_pair += abs(amount_0)
                else:
                    raise RuntimeError(f"bad swap in tx {event['transactionHash']}: token0_address:{token0_address} token1_address:{token1_address}")

                continue

            elif topic0 == collect_topic:
                # skip liquidity deposits/withdrawals
                continue
            elif topic0 == cloned_collect_topic:
                # skip liquidity deposits/withdrawals
                continue

            else:
                logging.debug('unknown topic txhash {}'.format(self._w3.toHex(event['transactionHash'])))
                logging.debug('unknown topic topic0 {}'.format(topic0))
                continue

        return volume_tokens, volume_pair

    async def _get_price_and_liquidity_for_pair(self, token0_address, token1_address, fee):
        paired_token_address = token0_address if token1_address.lower() == Token().from_symbol(self.currency_symbol).address.lower() else token1_address
        paired_token_symbol = Token().from_address(paired_token_address).symbol
        liquidity_tokens, liquidity_pair = get_reserves(self._w3, self.currency_symbol, paired_token_symbol, fee)

        # bail early if the number of tokens LPd is very small
        # TODO: this should probably be configurable. Or generated automatically
        #       based on some USD value, not token value
        if liquidity_tokens < _MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS:
            raise NoLiquidityException(f"Less than {_MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS} tokens LP'd for exchange contract.")

        # get price of paired token (in USD) to determine price of 
        # <self.currency_symbol> in USD. Strategy changes depending on pair
        price_in_paired_token = get_price(self._uniswap_api, paired_token_symbol, self.currency_symbol, fee)
        if paired_token_symbol == "WETH":
            paired_token_price_in_usd = self.eth_price_usd
        else:
            # get the paired token's price in Eth. If there is less than $500 in 
            # liquidity to determine this, then skip this pair when determining price.
            liquidity_eth_of_paired_token, _ = get_reserves(self._w3, "WETH", paired_token_symbol, fee)
            if liquidity_eth_of_paired_token < 500 / self.eth_price_usd:
                raise NoLiquidityException(f"Less than {500} USD LP'd for paired token {paired_token_symbol}, pair token price not considered accurate. Skipping pair.")
            else:
                paired_token_price_in_eth = get_price(self._uniswap_api, "WETH", paired_token_symbol)
                paired_token_price_in_usd = paired_token_price_in_eth * self.eth_price_usd

        price_in_usd = price_in_paired_token * paired_token_price_in_usd
        return price_in_usd, liquidity_tokens

    async def _update_all_values(self, timeout=10.0, should_update_volume=False):

        if should_update_volume:
            current_eth_block = self._w3.eth.blockNumber

        self.price_eth = None

        eth_prices = [
            get_price(self._uniswap_api, "DAI", "WETH", _DEFAULT_PAIR_FEE),
            get_price(self._uniswap_api, "USDT", "WETH", _DEFAULT_PAIR_FEE),
            get_price(self._uniswap_api, "USDC", "WETH", _DEFAULT_PAIR_FEE),
        ]
        self.eth_price_usd = sum(eth_prices) / len(eth_prices)  # TODO: should be weighted average

        price_usd_weighted_average = WeightedAverage()
        total_liquidity_tokens = 0
        total_volume_tokens = 0

        for exchange_address in getExchangeAddressesForToken(self.currency_symbol):
            token0_name, token1_name, fee = getTokensFromExchangeAddress(exchange_address)
            token0_address = Token().from_symbol(token0_name).address
            token1_address = Token().from_symbol(token1_name).address
            #paired_token_address = token0_address if token1_address.lower() == Token().from_symbol(self.currency_symbol).address.lower() else token1_address
            #paired_token_symbol = Token().from_address(paired_token_address).symbol

            try:
                price_usd, liquidity_tokens = await self._get_price_and_liquidity_for_pair(token0_address, token1_address, fee)
            except (NoTokenMatchError, PairNotDefinedError) as e:
                logging.warning(f"Failed to update uniswap v2 pair: {str(e)}")
                continue
            except NoLiquidityException:
                # no liquidity is not an error; simply skip this exchange
                continue
            else:
                price_usd_weighted_average.add(price_usd, liquidity_tokens)
                total_liquidity_tokens += liquidity_tokens

                if should_update_volume and liquidity_tokens > _MINIMUM_ALLOWED_LIQUIDITY_TOKENS_TO_CHECK_VOLUME:
                    try:
                        volume_tokens, volume_pair = await self._get_volume_for_pair(token0_address, token1_address, fee, current_eth_block=current_eth_block, timeout=timeout)
                        total_volume_tokens += volume_tokens
                    except requests.exceptions.ReadTimeout:
                        logging.warning(f"Failed to update Uniswapv3API volume: ReadTimeout")

        self.price_usd = price_usd_weighted_average.average()
        self.price_eth = self.price_usd / self.eth_price_usd
        self.liquidity_tokens = total_liquidity_tokens
        self.liquidity_eth = self.liquidity_tokens * self.price_eth

        if should_update_volume:
            self._hourly_volume_tokens.append(total_volume_tokens)
            # trim list to 24 hours
            self._hourly_volume_tokens = self._hourly_volume_tokens[-24:]
            self.volume_tokens = sum(self._hourly_volume_tokens)
            self.volume_eth = self.volume_tokens * self.price_eth
            # NOTE: this sets _time_volume_last_updated even if all volume updates
            #       failed. This is OK for now, it throttles struggling APIs (matic) but
            #       may not be the ideal behavior.
            self._mark_volume_as_updated()

    async def _update(self, timeout=10.0):
        if self._is_time_to_update_volume():
            await self._update_all_values(timeout=timeout, should_update_volume=True)
        else:
            await self._update_all_values(timeout=timeout, should_update_volume=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # get some data from 0xBTC pool via Uniswapv3API
    e = Uniswapv3API('0xBTC')
    e.load_once_and_print_values()
    print()
    print('0xBTC-WETH liquidity in eth', e.liquidity_eth)
    print('0xBTC-WETH liquidity in tokens', e.liquidity_tokens)
    print()

    # # get some data from KIWI pool via Uniswapv3API
    # e = Uniswapv3API('KIWI')
    # e.load_once_and_print_values()
    # print()
    # try:
    #     print('KIWI-WETH liquidity in eth', e.liquidity_eth)
    # except AttributeError:
    #     pass
    # print('KIWI-WETH liquidity in tokens', e.liquidity_tokens)

    # e = Uniswapv3API('DAI')
    # e.load_once_and_print_values()

