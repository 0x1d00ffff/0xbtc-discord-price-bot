#
#
# 'total supply' is at index 5 (0x5)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x5", "latest"]'
# 'last difficulty period started' is at index 6 (0x6)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x6", "latest"]'
# 'mining epoch' is at index 7 (0x7)
# curl -G https://api.infura.io/v1/jsonrpc/mainnet/eth_getStorageAt --data-urlencode 'params=["0xb6ed7644c69416d67b522e20bc294a9a9b405b31", "0x7", "latest"]'
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

import requests

from urllib.error import URLError

from constants import SECONDS_PER_ETH_BLOCK
import configuration as config


class MineableTokenInfo():
    def __init__(self, token_address):
        self._w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_NODE_URL))

        self.address = self._w3.toChecksumAddress(token_address)

        if self.address == "0xB6eD7644C69416d67B522e20bC294A9a9B405B31":
            self._ETH_BLOCKS_PER_REWARD = 60
            abi = mineable_token_abis.abis["0xBTC"]
        else:
            fmt_str = "constants for contract {} are missing, need to edit mineable_token_info.py"
            raise RuntimeError(fmt_str.format(token_address))


        self._contract = self._w3.eth.contract(address=self.address, abi=abi)

        self.symbol = self._contract.functions.symbol().call()
        self.min_target = self._contract.functions._MINIMUM_TARGET().call()
        self.max_target = self._contract.functions._MAXIMUM_TARGET().call()
        self.blocks_per_readjustment = self._contract.functions._BLOCKS_PER_READJUSTMENT().call()
        self.decimals = self._contract.functions.decimals().call()
        self.decimal_divisor = 10 ** self.decimals
        self.ideal_block_time_seconds = self._ETH_BLOCKS_PER_REWARD * SECONDS_PER_ETH_BLOCK

        self.total_supply = None
        self.last_difficulty_start_block = None
        self.mining_target = None
        self.difficulty = None
        self.challenge_number = None
        self.tokens_minted = None
        self.addr_0_balance = None

    def _read_contract_variable_at_index(self, index, convert_to_int=True, divisor=1, timeout=10.0):
        # UNUSED
        # TODO: remove this if it is not necessary
        return self._w3.eth.getStorageAt(self.address, index, 'latest')

    def _read_contract_map_location(self, key, map_position, convert_to_int=True, divisor=1, timeout=10.0):
        # UNUSED
        # TODO: remove this if it is not necessary
        # TODO: fix; this doesn't' seem to produce the correct keccack hashes
        logging.exception("_read_contract_map_location probably doesn't work")

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
        return self._read_contract_variable_at_index(location, convert_to_int=convert_to_int, divisor=divisor)

    def get_events_last_n_days(self, days):
        """Get all events sent from the contract in the last N days.

        TODO: there is a OwnershipTransferred event, but for 0xBTC ownership is
        burned so this does not matter. This event should be handled to make
        this library more generic."""
        event_types = {
            "0xcf6fbb9dcea7d07263ab4f5c3a92f53af33dffc421d9d121e1c74b307e68189d": "mint",
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "transfer",
            "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925": "approve",
        }
        logs = []
        for event in self._w3.eth.getLogs({
                'fromBlock': self._current_eth_block - (days * int(60*60*24 / SECONDS_PER_ETH_BLOCK)),
                'toBlock': self._current_eth_block - 1,
                'address': self.address}):
            topic0 = self._w3.toHex(event['topics'][0])
            try:
                event_type = event_types[topic0]
            except KeyError:
                print('unknown topic', topic0, 'tx_hash', self._w3.toHex(event['transactionHash']))
                event_type = "unknown"

            new_entry = {
                'type': event_type,
                'hash': self._w3.toHex(event['transactionHash']),
                'from_address': self._w3.toChecksumAddress(event['topics'][1][-20:]),
                'block_number': event['blockNumber'],
            }

            if event_type == "mint":
                new_entry['amount'] = self._w3.toInt(hexstr=event['data'][2:64+2]) / self.decimal_divisor
                new_entry['epoch_count'] = self._w3.toInt(hexstr=event['data'][64+2:128+2])
                new_entry['new_challenge'] = self._w3.toHex(hexstr=event['data'][128+2:192+2])
            elif event_type == "transfer":
                new_entry['to_address'] = self._w3.toChecksumAddress(event['topics'][2][-20:])
                new_entry['amount'] = self._w3.toInt(hexstr=event['data']) / self.decimal_divisor
            elif event_type == "approve":
                new_entry['spender_address'] = self._w3.toChecksumAddress(event['topics'][2][-20:])
                new_entry['amount'] = self._w3.toInt(hexstr=event['data']) / self.decimal_divisor
            else:
                new_entry['data'] = event['data']

            logs.append(new_entry)

        return logs

    def balance_of(self, address):
        return self._contract.functions.balanceOf(address).call() / self.decimal_divisor
        
    def _estimated_hashrate_n_days(self, days):
        eth_blocks_in_window = int(days * 60*60*24 / SECONDS_PER_ETH_BLOCK)
        eth_block_at_start = self._current_eth_block - eth_blocks_in_window
        epoch_at_start = self._contract.functions.epochCount().call(block_identifier=-eth_blocks_in_window)
        #epoch_at_start = self._w3.toInt(self._w3.eth.getStorageAt(self.address, 0x7, eth_block_at_start))
        epochs_in_window = self._epoch_count - epoch_at_start
        epochs_per_eth_block = epochs_in_window / eth_blocks_in_window
        epochs_per_second = epochs_per_eth_block / SECONDS_PER_ETH_BLOCK
        seconds_per_reward = 1 / epochs_per_second

        # if current diff started before beginning of the window, the math is
        # simple - one difficulty only
        if self.last_difficulty_start_block <= eth_block_at_start:
            estimated_hashrate_24h = self.difficulty * 2**22 / seconds_per_reward
        else:
            # difficulty changed within the window - so calculation must
            # consider multiple difficulties
            previous_mining_target = self._contract.functions.getMiningTarget().call(block_identifier=self.last_difficulty_start_block-1)
            previous_difficulty = int(self.max_target / previous_mining_target)

            # load the eth block where the difficulty changed to the *previous*
            # difficulty. If it is inside the window, exit completely, because
            # it means the window contains 3 or more difficulties.
            eth_block_two_readjustments_ago = self._contract.functions.latestDifficultyPeriodStarted().call(block_identifier=self.last_difficulty_start_block-1)
            if eth_block_two_readjustments_ago >= eth_block_at_start:
                raise RuntimeError("Average window too large: this function only supports at most two difficulty periods.")

            from weighted_average import WeightedAverage
            wa = WeightedAverage()
            # add hashrate based on current difficulty weighted by how many eth
            # blocks occured during that difficulty
            wa.add(self.difficulty * 2**22 / seconds_per_reward,
                   self._current_eth_block - self.last_difficulty_start_block)
            # add hashrate based on last difficulty weighted by how many eth
            # blocks occured during that difficulty
            wa.add(previous_difficulty * 2**22 / seconds_per_reward,
                   self.last_difficulty_start_block - eth_block_at_start)
            estimated_hashrate_24h = wa.average()

        return estimated_hashrate_24h
        
    def _estimated_hashrate_24h(self):
        return self._estimated_hashrate_n_days(1)

    def _update(self):
        self.total_supply = self._contract.functions.totalSupply().call() / self.decimal_divisor
        self.last_difficulty_start_block = self._contract.functions.latestDifficultyPeriodStarted().call()
        self.mining_target = self._contract.functions.getMiningTarget().call()

        self.difficulty = int(self.max_target / self.mining_target)

        self.challenge_number = Web3.toHex(self._contract.functions.getChallengeNumber().call())
        self.tokens_minted = self._contract.functions.tokensMinted().call() / self.decimal_divisor
        self.addr_0_balance = self.balance_of('0x0000000000000000000000000000000000000000')
        self._epoch_count = self._contract.functions.epochCount().call()
        self._current_eth_block = self._w3.eth.blockNumber
        eth_blocks_since_last_difficulty_period = self._current_eth_block - self.last_difficulty_start_block
        self.seconds_since_readjustment = eth_blocks_since_last_difficulty_period * SECONDS_PER_ETH_BLOCK
        rewards_since_readjustment = self._epoch_count % self.blocks_per_readjustment
        if rewards_since_readjustment == 0:
            self.seconds_per_reward = float('inf')
        else:
            self.seconds_per_reward = self.seconds_since_readjustment / rewards_since_readjustment
        rewards_left = self.blocks_per_readjustment - rewards_since_readjustment
        self.seconds_until_readjustment = rewards_left * self.seconds_per_reward

        # estimated hashrate
        # TODO: calculate this equation from max_target (https://en.bitcoin.it/wiki/Difficulty)
        # uses current reward rate in hashrate calculation
        self.estimated_hashrate_since_readjustment = self.difficulty * 2**22 / self.seconds_per_reward
        self.era = self._contract.functions.rewardEra().call()
        self.max_supply_for_era = self._contract.functions.maxSupplyForEra().call() / self.decimal_divisor
        # TODO: probably need to round to current mining reward
        supply_remaining_in_era = self.max_supply_for_era - self.tokens_minted
        self.reward = 50 / 2**self.era
        rewards_blocks_remaining_in_era = supply_remaining_in_era / self.reward
        self.seconds_remaining_in_era = rewards_blocks_remaining_in_era * self.ideal_block_time_seconds

        # catch error thrown by new infura v3 api since it does not support this
        # anymore, unfortunately
        try:
            self.estimated_hashrate_24h = self._estimated_hashrate_24h()
        except (ValueError, requests.exceptions.HTTPError):
            self.estimated_hashrate_24h = None

    def update(self):
        try:
            return self._update()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
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

        digest = Web3.soliditySha3(['bytes32', 'address', 'uint256'], 
                                   [challenge_number, address, Web3.toInt(nonce)])
        return nonce, digest

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    # digest = Web3.sha3(Web3.toBytes(hexstr="3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a540d752a388b4fc1c9deeb1cd3716a2b7875d8a603000000000000000440a2682657259316000000e87905d96943030a90de3e74"))

    m = MineableTokenInfo('0xB6eD7644C69416d67B522e20bC294A9a9B405B31')

    m.update()

    import pprint
    recent_events = m.get_events_last_n_days(1)
    logging.info('m.get_events_last_n_days(1)[-2:]: {}'.format(pprint.pprint(recent_events[-2:])))
    logging.info('len(m.get_events_last_n_days(1)): {}'.format(len(recent_events)))

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
    logging.info('m.estimated_hashrate_since_readjustment: {}'.format(m.estimated_hashrate_since_readjustment))
    logging.info('m.estimated_hashrate_24h: {}'.format(m.estimated_hashrate_24h))
    logging.info('m.era: {}'.format(m.era))
    logging.info('m.max_supply_for_era: {}'.format(m.max_supply_for_era))
    logging.info('m.reward: {}'.format(m.reward))
    logging.info('m.seconds_remaining_in_era: {}'.format(m.seconds_remaining_in_era))

    nonce, digest = m.get_digest_for_nonce_str("0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74",
                                               "0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6",
                                               "0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a")
    logging.info('m.get_digest_for_nonce_str(...):')
    logging.info('  nonce : 0x{}'.format(nonce.hex()))
    logging.info('  digest: {}'.format(digest.hex()))
