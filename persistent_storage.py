import shelve
import os

_DATABASE_FOLDER = './databases'

if not os.path.exists(_DATABASE_FOLDER):
    os.makedirs(_DATABASE_FOLDER)


class KeyValueStore():
    def __init__(self, db_file):
        self._db_file = os.path.join(_DATABASE_FOLDER, db_file)

    def get(self, key):
        with shelve.open(self._db_file) as db:
            return db[str(key)]

    def set(self, key, value):
        with shelve.open(self._db_file) as db:
            db[str(key)] = value


class SingleValueStore():
    def __init__(self, identifier, default=None):
        self.identifier = identifier
        self._db_file = os.path.join(_DATABASE_FOLDER, "single_value_store.db")
        self._default = default

    def get(self):
        with shelve.open(self._db_file) as db:
            try:
                return db[self.identifier]
            except KeyError:
                if self._default is not None:
                    return self._default
                else:
                    raise

    def set(self, value):
        with shelve.open(self._db_file) as db:
            db[self.identifier] = value


user_addresses = KeyValueStore("user_addresses.db")

top_miner_name = SingleValueStore("top_miner_name", default="Nobody")
top_miner_id = SingleValueStore("top_miner_id", 0)
top_miner_difficulty = SingleValueStore("top_miner_difficulty", 0)
top_miner_digest = SingleValueStore("top_miner_digest", b'\x00')

all_time_high_usd_price = SingleValueStore("all_time_high_usd_price", 0)
all_time_high_usd_timestamp = SingleValueStore("all_time_high_usd_timestamp", 0)
all_time_high_eth_price = SingleValueStore("all_time_high_eth_price", 0)
all_time_high_eth_timestamp = SingleValueStore("all_time_high_eth_timestamp", 0)
