#
#
# 'total supply' is at index 5 (0x5)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x5", "latest"]'
# 'last difficulty period started' is at index 6 (0x6)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x6", "latest"]'
# 'mining target' is at index 11 (0xB)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0xB", "latest"]'
# 'challenge number' is at index 12 (0xC)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0xC", "latest"]'
# 'tokens minted' is at index 20 (0x14)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x14", "latest"]'
#
#
import logging

import mineable_token_abis

import json
import binascii
import web3
from web3 import Web3
from web3.exceptions import ValidationError

try:
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.parse import urlencode
    from urllib.parse import quote
except:
    from urllib import urlopen
    from urllib import urlencode
    from urllib import quote

from urllib.error import URLError


_SECONDS_PER_ETH_BLOCK = 15.0

class MineableTokenInfo():
    def __init__(self, token_address):
        self._SERVER_URL = "https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt"

        self.address = token_address

        if self.address == "0xB6eD7644C69416d67B522e20bC294A9a9B405B31":
            self.SYMBOL = "0xBTC"
            self.MIN_TARGET = 2**16
            self.MAX_TARGET = Web3.toInt(hexstr="0x40000000000000000000000000000000000000000000000000000000000")
            self._BLOCKS_PER_READJUSTMENT = 1024
            self._DECIMALS = 8
            self._DIVISOR = 10 ** self._DECIMALS
            self._ETH_BLOCKS_PER_REWARD = 60
            self._IDEAL_BLOCK_TIME_SECONDS = self._ETH_BLOCKS_PER_REWARD * _SECONDS_PER_ETH_BLOCK;

            abi = mineable_token_abis.abis[self.SYMBOL]
        else:
            raise RuntimeError("constants for this contract address are missing")

        # TODO: change this out with a different one, this is used on the stats
        # site
        self._w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/MnFOXCPE2oOhWpOCyEBT"))

        self._contract = self._w3.eth.contract(address=self.address, abi=abi)

        self.total_supply = None
        self.last_difficulty_start_block = None
        self.mining_target = None
        self.difficulty = None
        self.challenge_number = None
        self.tokens_minted = None
        self.addr_0_balance = None

    def _read_contract_variable_at_index(self, index, convert_to_int=True, divisor=1, timeout=10.0):
        try:
            index = "{:#x}".format(index)
        except ValueError:
            pass

        try:
            # '["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x5", "latest"]'

            infura_parameters = '["{}", "{}", "latest"]'.format(self.address, 
                                                                index)

            #logging.info('infura_parameters:{}'.format(infura_parameters))
            # query_data = [
            #     ('params', quote(infura_parameters)),
            # ]
            #encoded_query_data = urlencode(query_data, encoding=None)
            #logging.info('encoded_query_data:{}'.format(quote(infura_parameters)))

            r = Request(self._SERVER_URL + '?params=' + quote(infura_parameters),
                        #data=encoded_query_data,
                        method="GET")
            #logging.info('r.method {}'.format(r.method))
            #logging.info('r.data {}'.format(r.data))
            #logging.info('r.full_url {}'.format(r.full_url))

            response = urlopen(r, timeout=timeout).read().decode("utf-8")
            try:
                data = json.loads(response)
            except json.decoder.JSONDecodeError:
                if "be right back" in response:
                    raise TimeoutError("infura is down - got 404 page")
                else:
                    raise TimeoutError("api sent bad data ({})".format(repr(response)))

            try:
                error = data['error']
                code = int(error['code'])
                message = error['message']
                logging.error('Got error {} from infura: {}'.format(code, message))
            except KeyError:
                pass

            try:
                result = data['result']
                if convert_to_int:
                    result = Web3.toInt(hexstr=result) / divisor
                return result
            except KeyError:
                pass

            logging.warning('Failed to update contract variable, bad data from infura? {}'.format(data))
            return None

        except:
            logging.exception("failed to load contract value from infura")
            return None

    def _read_contract_map_location(self, key, map_position, convert_to_int=True, divisor=1, timeout=10.0):
        # todo: fix; this doesn't' seem to produce the correct keccack hashes
        logging.warning("_read_contract_map_location probably doesn't work")

        try:
            key = "{:0>32x}".format(key)
        except ValueError:
            pass
        try:
            map_position = "{:0>32x}".format(map_position)
        except ValueError:
            pass

        if key[:2] == '0x':
            key = key[2:]
        if map_position[:2] == '0x':
            map_position = map_position[2:]


        digest = "{:0>32}{:0>32}".format(key, map_position)
        logging.info('digest:{}'.format(digest))
        location = Web3.toWeb3.sha3(hexstr=digest)
        logging.info('digest2:{}'.format(digest))
        logging.info('location:{}'.format(location))
        return self._read_contract_variable_at_index(location, convert_to_int=convert_to_int, divisor=divisor, timeout=timeout)


    def _update(self):
        self.total_supply = self._contract.functions.totalSupply().call() / self._DIVISOR
        self.last_difficulty_start_block = self._contract.functions.latestDifficultyPeriodStarted().call()
        self.mining_target = self._contract.functions.getMiningTarget().call()

        #self.difficulty = self._contract.functions.getMiningDifficulty().call()
        self.difficulty = int(self.MAX_TARGET / self.mining_target)

        self.challenge_number = Web3.toHex(self._contract.functions.getChallengeNumber().call())
        self.tokens_minted = self._contract.functions.tokensMinted().call() / self._DIVISOR
        self.addr_0_balance = self._contract.functions.balanceOf('0x0000000000000000000000000000000000000000').call() / self._DIVISOR
        self._epoch_count = self._contract.functions.epochCount().call()
        self._current_eth_block = self._w3.eth.blockNumber
        eth_blocks_since_last_difficulty_period = self._current_eth_block - self.last_difficulty_start_block;
        self.seconds_since_readjustment = eth_blocks_since_last_difficulty_period * _SECONDS_PER_ETH_BLOCK
        rewards_since_readjustment = self._epoch_count % self._BLOCKS_PER_READJUSTMENT
        self.seconds_per_reward = self.seconds_since_readjustment / rewards_since_readjustment;
        rewards_left = self._BLOCKS_PER_READJUSTMENT - rewards_since_readjustment
        self.seconds_until_readjustment = rewards_left * self.seconds_per_reward

        # estimated hashrate
        # TODO: calculate this equation from max_target (https://en.bitcoin.it/wiki/Difficulty)
        # uses current reward rate in hashrate calculation
        self.estimated_hashrate = self.difficulty * 2**22 / self.seconds_per_reward;
        self.era = self._contract.functions.rewardEra().call()
        self.max_supply_for_era = self._contract.functions.maxSupplyForEra().call() / self._DIVISOR
        # TODO: probably need to round to current mining reward
        supply_remaining_in_era = self.max_supply_for_era - self.tokens_minted
        self.reward = 50 / 2**self.era
        rewards_blocks_remaining_in_era = supply_remaining_in_era / self.reward;
        self.seconds_remaining_in_era = rewards_blocks_remaining_in_era * self._IDEAL_BLOCK_TIME_SECONDS

    def update(self):
        try:
            return self._update()
        except (requests.exceptions.ConnectionError,
                URLError):
            raise RuntimeError("Could not connect to infura.io")


    def get_digest_for_nonce_str(self, nonce_as_str, address, challenge_number=None):
        if not Web3.isAddress(address):
            raise RuntimeError("Bad address")

        if len(nonce_as_str) == 0:
            raise RuntimeError("Empty nonce")

        if nonce_as_str[:2] == "0x" or nonce_as_str[:2] == "0X":
            try:
                return self.get_digest_for_nonce(Web3.toBytes(hexstr=nonce_as_str),
                                                 address,
                                                 challenge_number=challenge_number)
            except (ValidationError, binascii.Error):
                pass

        try:
            return self.get_digest_for_nonce(Web3.toBytes(int(nonce_as_str)),
                                             address,
                                             challenge_number=challenge_number)
        except (ValueError, ValidationError):
            pass

        try: 
            return self.get_digest_for_nonce(Web3.toBytes(text=nonce_as_str),
                                             address,
                                             challenge_number=challenge_number)
        except (ValueError, ValidationError):
            pass

        raise RuntimeError("Couldn't parse nonce {}".format(nonce[:36]))


    def get_digest_for_nonce(self, nonce, address, challenge_number=None):
        if challenge_number is None:
            challenge_number = self.challenge_number

        try:
            challenge_number = Web3.toBytes(hexstr=challenge_number)
        except ValidationError:
            raise RuntimeError("Bad challenge_number")

        if len(nonce) == 0:
            raise RuntimeError("Empty nonce")

        if not Web3.isAddress(address):
            raise RuntimeError("Bad address")

        # pad front with 32 bytes of zeros, then drop all but first 32 bytes
        challenge_number = ((b'\x00' * 32) + challenge_number)[-32:]
        # pad front with 32 bytes of zeros, then drop all but first 20 bytes
        #address = ((b'\x00' * 32) + address)[-20:]
        # pad end with 32 bytes of zeros, then drop all but first 32 bytes
        nonce = (nonce + (b'\x00' * 32))[:32]

        # logging.info('challenge_number: {}'.format(challenge_number.hex()))
        # logging.info('address: {}'.format(address))
        # logging.info('nonce: {}'.format(nonce.hex()))
        digest = Web3.sha3(Web3.toBytes(hexstr="3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a540d752a388b4fc1c9deeb1cd3716a2b7875d8a603000000000000000440a2682657259316000000e87905d96943030a90de3e74"))

        #import pdb; pdb.set_trace()

        digest = Web3.soliditySha3(['bytes32', 'address', 'uint256'], 
                                   [challenge_number, address, Web3.toInt(nonce)])

        return nonce, digest


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    m = MineableTokenInfo('0xB6eD7644C69416d67B522e20bC294A9a9B405B31')

    m.update()

    logging.info('m.total_supply: {}'.format(m.total_supply))
    logging.info('m.last_difficulty_start_block: {}'.format(m.last_difficulty_start_block))
    logging.info('m.mining_target: {}'.format(m.mining_target))
    logging.info('m.difficulty: {}'.format(m.difficulty))
    logging.info('m.challenge_number: {}'.format(m.challenge_number))
    logging.info('m.tokens_minted: {}'.format(m.tokens_minted))
    logging.info('m.addr_0_balance: {}'.format(m.addr_0_balance))
    logging.info('m.seconds_since_readjustment: {}'.format(m.seconds_since_readjustment))
    logging.info('m.seconds_per_reward: {}'.format(m.seconds_per_reward))
    logging.info('m.seconds_until_readjustment: {}'.format(m.seconds_until_readjustment))
    logging.info('m.estimated_hashrate: {}'.format(m.estimated_hashrate))
    logging.info('m.era: {}'.format(m.era))
    logging.info('m.max_supply_for_era: {}'.format(m.max_supply_for_era))
    logging.info('m.reward: {}'.format(m.reward))
    logging.info('m.seconds_remaining_in_era: {}'.format(m.seconds_remaining_in_era))

    nonce, digest = m.get_digest_for_nonce_str("0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74",
                                               "0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6",
                                               "0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a")
    logging.info('m.get_digest_for_nonce_str(...):')
    logging.info(' Nonce : 0x{}'.format(nonce.hex()))
    logging.info(' Digest: {}'.format(digest.hex()))
