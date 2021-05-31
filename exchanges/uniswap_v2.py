"""
API for Uniswap v2 distributed exchange (uniswap.exchange)
Price info is pulled from the smart contract
"""
import logging
from web3 import Web3
import time

from .base_exchange import Daily24hChangeTrackedAPI, NoLiquidityException
from .uniswap_v2_abi import exchange_abi
from .uniswap_v2_router_abi import router_abi
from secret_info import ETHEREUM_NODE_URL
from constants import SECONDS_PER_ETH_BLOCK
from token_class import Token, NoTokenMatchError
from weighted_average import WeightedAverage

# list of exchange contract addresses. each pair has a unique address.
# token0 name, token1 name, uniswap exchange address
exchanges = (
("0xBTC", "WETH", "0xc12c4c3E0008B838F75189BFb39283467cf6e5b3"),
("DAI", "0xBTC", "0x095739e9Ea7B0d11CeE1c1134FB76549B610f4F3"),
("USDC", "0xBTC", "0xA99F7Bc92c932A2533909633AB19cD7F04805059"),
("SHUF", "0xBTC", "0x1f9119d778d0B631f9B3b8974010ea2B750e4d33"),
("DAI", "WETH", "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11"),
("USDC", "WETH", "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc"),
("DAI", "USDT", "0xB20bd5D04BE54f870D5C0d3cA85d82b34B836405"),
("DAI", "USDC", "0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5"),
("WETH", "USDT", "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852"),
("MATIC", "WETH", "0x819f3450dA6f110BA6Ea52195B3beaFa246062dE"),
("0xBTC", "USDT", "0x2Fe04156a0b47A8EB6298eEa6A0e00Fe47cb9B3B"),
("KIWI", "WETH", "0x524C8a7563034aA33F8E53A934909929024C3937"),
)










class PairNotDefinedError(Exception):
    pass

def getExchangeAddressesForToken(name):
    return [i[2] for i in exchanges if i[0].lower() == name.lower() or i[1].lower() == name.lower()]
def getTokensFromExchangeAddress(exchange_address):
    return [(i[0], i[1]) for i in exchanges if i[2].lower() == exchange_address.lower()][0]
def getExchangeAddressForTokenPair(first_token_name, second_token_name):
    token_addresses = sorted([Token().from_symbol(first_token_name).address.lower(),
                              Token().from_symbol(second_token_name).address.lower()])
    for token1_name, token2_name, address in exchanges:
        if (token1_name in [first_token_name, second_token_name]
            and token2_name in [first_token_name, second_token_name]):
            return (address,
                    Token().from_address(token_addresses[0]).symbol,
                    Token().from_address(token_addresses[1]).symbol)
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
        amount * 10**Token().from_symbol(token0_name).decimals,
        reserves[0],
        reserves[1])
    # amount_out = self._router.functions.getAmountOut(
    #     amount * 10**token0_decimals, 
    #     reserves[0], 
    #     reserves[1]).call()
    return amount_out / 10**Token().from_symbol(token1_name).decimals

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
    reserves[0] = reserves[0] / 10**Token().from_symbol(first_token_name).decimals
    reserves[1] = reserves[1] / 10**Token().from_symbol(second_token_name).decimals

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


class Uniswapv2API(Daily24hChangeTrackedAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        try:
            self._exchange_addresses = getExchangeAddressesForToken(currency_symbol)
            self._decimals = Token().from_symbol(currency_symbol).decimals
        except IndexError:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to uniswap_v2.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "Uniswap v2"
        self.command_names = ["uniswapv2", "univ2", "uniswap v2", "uni v2"]
        self.short_url = "https://bit.ly/3wPyeu5"  # main uniswap pre-selected to 0xbtc
        self.volume_eth = 0

        self._time_volume_last_updated = 0

        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        self._exchanges = [self._w3.eth.contract(address=a, abi=exchange_abi) for a in self._exchange_addresses]

    async def _get_volume_at_exchange_contract(self, exchange_contract, timeout=10.0):
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

        current_eth_block = self._w3.eth.blockNumber

        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*24 / SECONDS_PER_ETH_BLOCK)),
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

                if Token().from_address(token0_address).symbol.lower() == self.currency_symbol.lower():
                    # token0 is the tracked currency symbol
                    volume_tokens += abs((amount0In - amount0Out) / 10**Token().from_address(token0_address).decimals)
                    volume_pair += abs((amount1In - amount1Out) / 10**Token().from_address(token1_address).decimals)
                elif Token().from_address(token1_address).symbol.lower() == self.currency_symbol.lower():
                    # token1 is the tracked currency symbol
                    volume_tokens += abs((amount1In - amount1Out) / 10**Token().from_address(token1_address).decimals)
                    volume_pair += abs((amount0In - amount0Out) / 10**Token().from_address(token0_address).decimals)

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

    async def _update_24h_volume(self, timeout=10.0):
        total_volume_tokens = 0
        for exchange_contract in self._exchanges:
            volume_tokens, volume_pair = await self._get_volume_at_exchange_contract(exchange_contract)
            total_volume_tokens += volume_tokens

            #print('volume: {} {} was traded for {} tokens of the paired currency'.format(volume_tokens, self.currency_symbol, volume_pair))
        return total_volume_tokens

    async def _update(self, timeout=10.0):
        eth_prices = [
            get_price(self._w3, "DAI", "WETH"),
            get_price(self._w3, "USDT", "WETH"),
            get_price(self._w3, "USDC", "WETH"),
        ]
        # TODO: weighted average would be better than a simple average
        self.eth_price_usd = sum(eth_prices) / len(eth_prices)

        # matic_price_eth = get_price(self._w3, "WETH", "WMATIC")
        # self.matic_price_usd = matic_price_eth * self.eth_price_usd

        # swam_price_eth = get_price(self._w3, "WETH", "SWAM")
        # self.swam_price_usd = swam_price_eth * self.eth_price_usd

        total_liquidity_tokens = 0
        price_usd_weighted_average = WeightedAverage()
        # check each token that <self.currency_symbol> is paired with
        for exchange_contract in self._exchanges:
            token0_address = exchange_contract.functions.token0().call().lower()
            token1_address = exchange_contract.functions.token1().call().lower()
            paired_token_address = token0_address if token1_address.lower() == Token().from_symbol(self.currency_symbol).address.lower() else token1_address
            try:
                paired_token_symbol = Token().from_address(paired_token_address).symbol
            except NoTokenMatchError:
                logging.warning(f"no token with address {paired_token_address} found (need to edit token_class.py); skipping")
                continue

            try:
                liquidity_tokens, liquidity_pair = get_reserves(self._w3, self.currency_symbol, paired_token_symbol)
            except PairNotDefinedError:
                logging.warning(f"pair {self.currency_symbol}-{paired_token_symbol} not found; skipping")
                continue

            if liquidity_tokens < 0.001:
                continue

            total_liquidity_tokens += liquidity_tokens

            if paired_token_symbol == "WETH":
                self.price_eth = get_price(self._w3, paired_token_symbol, self.currency_symbol)
                price_usd_weighted_average.add(self.price_eth * self.eth_price_usd, liquidity_tokens)
                self.liquidity_eth = liquidity_pair
            else:

                # get the paired token's price in Eth. If there is less than $500 in 
                # liquidity to determine this, then skip this pair when determining price.
                try:
                    liquidity_eth, _ = get_reserves(self._w3, "WETH", paired_token_symbol)
                except PairNotDefinedError:
                    logging.warning(f"pair WETH-{paired_token_symbol} not found; skipping")
                    continue

                if liquidity_eth < 500 / self.eth_price_usd:
                    continue

                paired_token_price_in_eth = get_price(self._w3, "WETH", paired_token_symbol)
                paired_token_price_in_usd = paired_token_price_in_eth * self.eth_price_usd

                # get the price <self.currency_symbol> in terms of the paired token
                price_in_paired_token = get_price(self._w3, paired_token_symbol, self.currency_symbol)

                price_usd_weighted_average.add(price_in_paired_token * paired_token_price_in_usd, liquidity_tokens)

        self.liquidity_tokens = total_liquidity_tokens
        self.price_usd = price_usd_weighted_average.average()

        try:
            self.price_eth = get_price(self._w3, "WETH", self.currency_symbol)
        except PairNotDefinedError:
            logging.warning(f"Failed to get WETH pair for {self.currency_symbol}; calculating backwards using average USD price")
            self.price_eth = self.price_usd / self.eth_price_usd

        # update volume once every hour since it (potentially) loads eth api
        if time.time() - self._time_volume_last_updated > 60 * 60:
            self.volume_tokens = await self._update_24h_volume()
            self.volume_eth = self.volume_tokens * self.price_eth
            self._time_volume_last_updated = time.time()


if __name__ == "__main__":
    # run some generic uniswap v2 functions
    web3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
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

    # get some data from 0xBTC pool via Uniswapv2API
    e = Uniswapv2API('0xBTC')
    e.load_once_and_print_values()
    print()
    print('0xBTC-WETH liquidity in eth', e.liquidity_eth)
    print('0xBTC-WETH liquidity in tokens', e.liquidity_tokens)
    print()

    # get some data from KIWI pool via Uniswapv2API
    e = Uniswapv2API('KIWI')
    e.load_once_and_print_values()
    print()
    try:
        print('KIWI-WETH liquidity in eth', e.liquidity_eth)
    except AttributeError:
        pass
    print('KIWI-WETH liquidity in tokens', e.liquidity_tokens)

    # e = Uniswapv2API('DAI')
    # e.load_once_and_print_values()

