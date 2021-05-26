"""
API for Uniswap v2 distributed exchange (uniswap.exchange)
Price info is pulled from the smart contract
"""
import logging
from web3 import Web3
import time
import requests

from .base_exchange import Daily24hChangeTrackedAPI, NoLiquidityException
from .uniswap_v2_abi import exchange_abi
from .uniswap_v2_router_abi import router_abi
from secret_info import MATIC_NODE_URL
from constants import SECONDS_PER_MATIC_BLOCK
from token_class import MaticToken, NoTokenMatchError
from weighted_average import WeightedAverage

# list of exchange contract addresses. each pair has a unique address.
# token0 name, token1 name, uniswap exchange address
exchanges = (

# WETH pairs
("USDC", "WETH", "0x853Ee4b2A13f8a742d64C8F088bE7bA2131f670d"),
("WETH", "DAI", "0x4A35582a710E1F4b2030A3F826DA20BfB6703C09"),
("WETH", "USDT", "0xF6422B997c7F54D1c6a6e103bcb1499EeA0a7046"),
("WMATIC", "WETH", "0xadbF1854e5883eB8aa7BAf50705338739e558E5b"),
("maWETH", "WETH", "0x587381961298A6019926329468f2dB73C414cf68"),
("WETH", "SWAM", "0xe3aD20db6f1B061024F4dF761DEB80bCd3e3E2a7"),
# 0xBTC pairs
#("maWETH", "0xBTC", "0x83Eaa0dD0146fb2494eDb1b260eC7C830d356AF7"),  # removed 5/26/21; no liquidity
("WMATIC", "0xBTC", "0x74FE2ea44ACe1AEee9937A2FDc7554CFC9288964"),
("0xBTC", "WETH", "0x58BBC687Ad7113e46D35314776FAd9c4B73e200C"),
#("USDC", "0xBTC", "0x19FcFD016a5Fa35286C1FBb3F96Fe9b3fF44530e"),  # removed 5/26/21; no liquidity
#("0xBTC", "USDT", "0xa3F3b3ad33C233633242bd1236072355a8af6f52"),  # removed 5/26/21; no liquidity
#("KIWI", "0xBTC", "0xf115308E8347E816D23566EAafB4C0BCb1349432"),  # removed 5/26/21; no liquidity
#("0xBTC", "DAI", "0xc5e5208A9544Bd0589063D4670E9747535127E16"),  # removed 5/26/21; no liquidity
# KIWI pairs
("KIWI", "SWAM", "0x0cD19Fb530D0ff9caB6F233d61dE6240E7f4660F"),
("WMATIC", "KIWI", "0xb97759d3b6210F2b7Af081E023Db972856523A5a"),
("KIWI", "SWAM", "0x6233132c03DAC2Af6495A9dAB02DF18b2A9DA892"),

)

_TIME_BETWEEN_VOLUME_UPDATES = 60 * 60  # 1 hour
# if less than this many tokens in pair, don't use it for price
_MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS = 0.1
# if less than this many tokens in pair, don't check its volume
_MINIMUM_ALLOWED_LIQUIDITY_TOKENS_TO_CHECK_VOLUME = 10

class PairNotDefinedError(Exception):
    pass

def getExchangeAddressesForToken(name):
    return [i[2] for i in exchanges if i[0].lower() == name.lower() or i[1].lower() == name.lower()]
def getTokensFromExchangeAddress(exchange_address):
    return [(i[0], i[1]) for i in exchanges if i[2].lower() == exchange_address.lower()][0]
def getExchangeAddressForTokenPair(first_token_name, second_token_name):
    token_addresses = sorted([MaticToken().from_symbol(first_token_name).address.lower(),
                              MaticToken().from_symbol(second_token_name).address.lower()])
    for token1_name, token2_name, address in exchanges:
        if (token1_name in [first_token_name, second_token_name]
            and token2_name in [first_token_name, second_token_name]):
            return (address,
                    MaticToken().from_address(token_addresses[0]).symbol,
                    MaticToken().from_address(token_addresses[1]).symbol)
    raise PairNotDefinedError(f"No pair {first_token_name}-{second_token_name} found")

def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

def ether_to_wei(amount_in_ether):
    return int(amount_in_ether * 1000000000000000000.0)

# HACK
# python implementation of uniswap router contract's getAmountOut function. Once web3.py
# supports solidity >= 0.6, we should be able to use the real getAmountOut function.
#
#     function getAmountOut(uint amountIn, uint reserveIn, uint reserveOut) internal pure returns (uint amountOut) {
#         require(amountIn > 0, 'UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT');
#         require(reserveIn > 0 && reserveOut > 0, 'UniswapV2Library: INSUFFICIENT_LIQUIDITY');
#         uint amountInWithFee = amountIn.mul(997);
#         uint numerator = amountInWithFee.mul(reserveOut);
#         uint denominator = reserveIn.mul(1000).add(amountInWithFee);
#         amountOut = numerator / denominator;
#     }
def get_amount_out__uniswap_router(amountIn, reserveIn, reserveOut):
    amountIn = int(amountIn)
    reserveIn = int(reserveIn)
    reserveOut = int(reserveOut)
    if amountIn <= 0 or reserveIn <= 0 or reserveOut <= 0:
        return None
    amountInWithFee = amountIn * 997
    numerator = amountInWithFee * reserveOut
    denominator = (reserveIn * 1000) + amountInWithFee
    return numerator / denominator

def get_swap_amount(web3, amount, token0_name, token1_name):
    """Returns the number of token1 tokens you can buy for a given number of 
    token0 tokens"""
    exchange_address, first_token_name, second_token_name = getExchangeAddressForTokenPair(token0_name, token1_name)
    exchange = web3.eth.contract(address=exchange_address, abi=exchange_abi)
    reserves = exchange.functions.getReserves().call()
    if token0_name == second_token_name:
        reserves[0], reserves[1] = reserves[1], reserves[0]

    if reserves[0] == 0 or reserves[1] == 0:
        return 0

    # TODO: replace this with the real function (commented below) once web3.py
    # supports solidity >= 0.6
    amount_out = get_amount_out__uniswap_router(
        amount * 10**MaticToken().from_symbol(token0_name).decimals,
        reserves[0],
        reserves[1])
    # amount_out = self._router.functions.getAmountOut(
    #     amount * 10**token0_decimals, 
    #     reserves[0], 
    #     reserves[1]).call()
    return amount_out / 10**MaticToken().from_symbol(token1_name).decimals

def get_pooled_balance_for_address(web3, token0_name, token1_name, owner_address):
    """get the balance of a particular address in a uniswap v2 pool"""
    exchange_address, _, _ = getExchangeAddressForTokenPair(token0_name, token1_name)
    exchange = web3.eth.contract(address=exchange_address, abi=exchange_abi)

    all_ownership_tokens = exchange.functions.totalSupply().call()
    if all_ownership_tokens == 0:
        ownership_tokens_in_address = exchange.functions.balanceOf(owner_address).call()
        ownership_percentage = ownership_tokens_in_address / all_ownership_tokens
    else:
        ownership_tokens_in_address = 0
        ownership_percentage = 0

    reserves = get_reserves(web3, token0_name, token1_name)

    return reserves[0] * ownership_percentage, reserves[1] * ownership_percentage

def get_reserves(web3, token0_name, token1_name):
    """get the reserves, in tokens, of a particular uniswap v2 pool"""
    exchange_address, first_token_name, second_token_name = getExchangeAddressForTokenPair(token0_name, token1_name)
    exchange = web3.eth.contract(address=exchange_address, abi=exchange_abi)
    reserves = exchange.functions.getReserves().call()
    reserves[0] = reserves[0] / 10**MaticToken().from_symbol(first_token_name).decimals
    reserves[1] = reserves[1] / 10**MaticToken().from_symbol(second_token_name).decimals

    if token0_name == second_token_name:
        reserves[0], reserves[1] = reserves[1], reserves[0]

    return reserves[0], reserves[1]

def get_price(web3, token0_name, token1_name):
    """Get the price at a particular uniswap v2 pool, in terms of token0 / token1"""
    reserves = get_reserves(web3, token0_name, token1_name)
    if reserves[1] == 0:
        return 0
    else:
        return reserves[0] / reserves[1]


class QuickSwapAPI(Daily24hChangeTrackedAPI):
    def __init__(self, currency_symbol, timeout=10.0):
        super().__init__()
        try:
            self._exchange_addresses = getExchangeAddressesForToken(currency_symbol)
            self._decimals = MaticToken().from_symbol(currency_symbol).decimals
        except IndexError:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to token_class.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "QuickSwap"
        self.command_names = ["quickswap"]
        self.short_url = "https://bit.ly/2R42MbO"  # main quickswap pre-selected to 0xbtc
        self.volume_eth = 0

        self._time_volume_last_updated = 0

        self._w3 = Web3(Web3.HTTPProvider(MATIC_NODE_URL, request_kwargs={'timeout': timeout}))
        self._exchanges = [self._w3.eth.contract(address=a, abi=exchange_abi) for a in self._exchange_addresses]

    def _is_time_to_update_volume(self):
        return time.time() - self._time_volume_last_updated > _TIME_BETWEEN_VOLUME_UPDATES

    def _mark_volume_as_updated(self):
        self._time_volume_last_updated = time.time()

    async def _get_volume_at_exchange_contract(self, exchange_contract, current_eth_block=None, timeout=10.0):
        volume_tokens = 0  # volume in units of <self.currency_symbol> tokens
        volume_pair = 0  # volume in units of the paired token

        swap_topic = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
        sync_topic = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
        burn_topic = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        approval_topic = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
        mint_topic = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"

        token0_address = exchange_contract.functions.token0().call()
        token1_address = exchange_contract.functions.token1().call()

        if current_eth_block is None:
            current_eth_block = self._w3.eth.blockNumber

        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*24 / SECONDS_PER_MATIC_BLOCK)),
                'toBlock': current_eth_block - 1,
                'address': exchange_contract.address}):
            topic0 = self._w3.toHex(event['topics'][0])
            if topic0 == swap_topic:
                #print('swap in tx', self._w3.toHex(event['transactionHash']))
                receipt = self._w3.eth.getTransactionReceipt(event['transactionHash'])
                parsed_logs = exchange_contract.events.Swap().processReceipt(receipt)

                correct_log = None
                for log in parsed_logs:
                    if log.address.lower() == exchange_contract.address.lower():
                        correct_log = log
                if correct_log is None:
                    logging.warning('bad swap transaction {}'.format(self._w3.toHex(event['transactionHash'])))
                    continue

                #sender_address = correct_log.args.sender
                #to_address = correct_log.args.to
                amount0In = correct_log.args.amount0In
                amount1In = correct_log.args.amount1In
                amount0Out = correct_log.args.amount0Out
                amount1Out = correct_log.args.amount1Out
                #block_number = correct_log.blockNumber

                if MaticToken().from_address(token0_address).symbol.lower() == self.currency_symbol.lower():
                    # token0 is the tracked currency symbol
                    volume_tokens += abs((amount0In - amount0Out) / 10**MaticToken().from_address(token0_address).decimals)
                    volume_pair += abs((amount1In - amount1Out) / 10**MaticToken().from_address(token1_address).decimals)
                elif MaticToken().from_address(token1_address).symbol.lower() == self.currency_symbol.lower():
                    # token1 is the tracked currency symbol
                    volume_tokens += abs((amount1In - amount1Out) / 10**MaticToken().from_address(token1_address).decimals)
                    volume_pair += abs((amount0In - amount0Out) / 10**MaticToken().from_address(token0_address).decimals)

                # print('    token', getTokenNameFromAddress(token0_address), 'send to exchange', (amount0In - amount0Out) / 10**getTokenDecimalsFromAddress(token0_address), getTokenNameFromAddress(token0_address))
                # print('    token', getTokenNameFromAddress(token1_address), 'send to exchange', (amount1In - amount1Out) / 10**getTokenDecimalsFromAddress(token1_address), getTokenNameFromAddress(token1_address))

                continue

            elif topic0 == mint_topic:
                # skip liquidity deposits/withdrawals
                continue
            elif topic0 == sync_topic:
                continue
            elif topic0 == burn_topic:
                continue
            elif topic0 == transfer_topic:
                continue
            elif topic0 == approval_topic:
                continue
            else:
                logging.debug('unknown topic txhash {}'.format(self._w3.toHex(event['transactionHash'])))
                logging.debug('unknown topic topic0 {}'.format(topic0))

        return volume_tokens, volume_pair

    async def _get_price_and_liquidity_at_exchange_contract(self, exchange_contract):
        token0_address = exchange_contract.functions.token0().call().lower()
        token1_address = exchange_contract.functions.token1().call().lower()
        paired_token_address = token0_address if token1_address.lower() == MaticToken().from_symbol(self.currency_symbol).address.lower() else token1_address
        paired_token_symbol = MaticToken().from_address(paired_token_address).symbol
        liquidity_tokens, liquidity_pair = get_reserves(self._w3, self.currency_symbol, paired_token_symbol)

        # bail early if the number of tokens LPd is very small
        # TODO: this should probably be configurable. Or generated automatically
        #       based on some USD value, not token value
        if liquidity_tokens < _MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS:
            raise NoLiquidityException(f"Less than {_MINIMUM_ALLOWED_LIQUIDITY_IN_TOKENS} tokens LP'd for exchange contract.")

        # get price of paired token (in USD) to determine price of 
        # <self.currency_symbol> in USD. Strategy changes depending on pair
        price_in_paired_token = get_price(self._w3, paired_token_symbol, self.currency_symbol)
        if paired_token_symbol == "WETH":
            paired_token_price_in_usd = self.eth_price_usd
        else:
            # get the paired token's price in Eth. If there is less than $500 in 
            # liquidity to determine this, then skip this pair when determining price.
            liquidity_eth_of_paired_token, _ = get_reserves(self._w3, "WETH", paired_token_symbol)
            if liquidity_eth_of_paired_token < 500 / self.eth_price_usd:
                raise NoLiquidityException(f"Less than {500} USD LP'd for paired token {paired_token_symbol}, pair token price not considered accurate. Skipping pair.")
            else:
                paired_token_price_in_eth = get_price(self._w3, "WETH", paired_token_symbol)
                paired_token_price_in_usd = paired_token_price_in_eth * self.eth_price_usd

        price_in_usd = price_in_paired_token * paired_token_price_in_usd
        return price_in_usd, liquidity_tokens

    async def _update_all_values(self, should_update_volume=False, timeout=10):
        if should_update_volume:
            current_eth_block = self._w3.eth.blockNumber

        # get price of eth
        eth_prices = [
            get_price(self._w3, "DAI", "WETH"),
            get_price(self._w3, "USDT", "WETH"),
            get_price(self._w3, "USDC", "WETH"),
        ]
        self.eth_price_usd = sum(eth_prices) / len(eth_prices)  # TODO: should be weighted average

        # get token price (in USD), liquidity (in tokens), and volume (in tokens) for
        # each pair. Note if liquidity is low for a pair, its voluem is not checked.
        price_usd_weighted_average = WeightedAverage()
        total_liquidity_tokens = 0
        total_volume_tokens = 0
        for exchange_contract in self._exchanges:
            try:
                price_usd, liquidity_tokens = await self._get_price_and_liquidity_at_exchange_contract(exchange_contract)
            except (NoTokenMatchError, PairNotDefinedError) as e:
                logging.warning(f"Failed to update quickswap exchange: {str(e)}")
                continue
            except NoLiquidityException:
                # no liquidity is not an error; simply skip this exchange
                continue
            else:
                price_usd_weighted_average.add(price_usd, liquidity_tokens)
                total_liquidity_tokens += liquidity_tokens

                if should_update_volume and liquidity_tokens > _MINIMUM_ALLOWED_LIQUIDITY_TOKENS_TO_CHECK_VOLUME:
                    try:
                        volume_tokens, volume_pair = await self._get_volume_at_exchange_contract(exchange_contract, current_eth_block=current_eth_block, timeout=timeout)
                        total_volume_tokens += volume_tokens
                    except requests.exceptions.ReadTimeout:
                        logging.warning(f"Failed to update QuickSwapAPI volume: ReadTimeout")

        self.price_usd = price_usd_weighted_average.average()
        self.price_eth = self.price_usd / self.eth_price_usd
        self.liquidity_tokens = total_liquidity_tokens
        self.liquidity_eth = self.liquidity_tokens * self.price_eth
        if should_update_volume:
            self.volume_tokens = total_volume_tokens
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
    # run some generic uniswap v2 functions
    web3 = Web3(Web3.HTTPProvider(MATIC_NODE_URL))
    print('$1 in USDC will swap for {} 0xBTC tokens'.format(get_swap_amount(web3, 1, "USDC", "0xBTC")))
    print('$1 in DAI will swap for {} 0xBTC tokens'.format(get_swap_amount(web3, 1, "DAI", "0xBTC")))
    print('1 0xBTC token will swap for {} DAI'.format(get_swap_amount(web3, 1, "0xBTC", "DAI")))
    print('100 0xBTC tokens will swap for {} DAI'.format(get_swap_amount(web3, 100, "0xBTC", "DAI")))
    print('1 ETH will swap for {} DAI'.format(get_swap_amount(web3, 1, "WETH", "DAI")))
    print('230 DAI will swap for {} ETH'.format(get_swap_amount(web3, 230, "DAI", "WETH")))
    print('0xbtc and ETH balances:', get_reserves(web3, "0xBTC", "WETH"))
    # print('0xbtc and ETH price:', e.get_price("0xBTC", "WETH"), "0xBTC per ETH")
    # print('0xbtc and ETH price:', e.get_price("WETH", "0xBTC"), "ETH per 0xBTC")
    print()
    print('eth usdc reserves ', get_reserves(web3, "WETH", "USDC"))
    print('1 in ETH will swap for {} USDC '.format(get_swap_amount(web3, 1, "WETH", "USDC")))
    print('1 in ETH will swap for {} USDT '.format(get_swap_amount(web3, 1, "WETH", "USDT")))
    print('1 in ETH will swap for {} DAI '.format(get_swap_amount(web3, 1, "WETH", "DAI")))
    print()

    # get some data from 0xBTC pool via QuickSwapAPI
    e = QuickSwapAPI('0xBTC')
    e.load_once_and_print_values()
    print()
    try:
        print('0xBTC-WETH liquidity in eth', e.liquidity_eth)
    except AttributeError:
        pass
    print('0xBTC-WETH liquidity in tokens', e.liquidity_tokens)

    # get some data from KIWI pool via QuickSwapAPI
    # e = QuickSwapAPI('KIWI')
    # e.load_once_and_print_values()
    # print()
    # try:
    #     print('KIWI-WETH liquidity in eth', e.liquidity_eth)
    # except AttributeError:
    #     pass
    # print('KIWI-WETH liquidity in tokens', e.liquidity_tokens)

    # e = QuickSwapAPI('DAI')
    # e.load_once_and_print_values()

