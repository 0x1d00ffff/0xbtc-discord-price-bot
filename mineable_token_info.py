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

class MineableTokenInfo():
    def __init__(self, token_address):
        self.address = token_address

        if self.address = "0xb6ed7644c69416d67b522e20bc294a9a9b405b31":
            self._MAX_TARGET = "27606985387162255149739023449108101809804435888681546220650096895197184"
            self._BLOCKS_PER_READJUSTMENT = 1024

        self.total_supply = None
        self.last_difficulty_start = None
        self.mining_target = None
        #self.challenge_number = None
        self.tokens_minted = None

    def _update_index(self, index):
        try:
            # todo: fetch and return index value from blockchain
            return 0
        except:
            logging.exception("failed to load contract value from infura")
            return None

    def update(self):
        self.total_supply = self._update_index(5)
        self.last_difficulty_start = self._update_index(6)
        self.mining_target = self._update_index(11)
        #self.challenge_number = self._update_index(12)
        self.tokens_minted = self._update_index(20)