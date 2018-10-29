import shelve
import os


class KeyValueStore():
    def __init__(self, db_file):
        self._db_file = db_file

    def get(self, key):
        with shelve.open(self._db_file) as db:
            return db[str(key)]

    def set(self, key, value):
        with shelve.open(self._db_file) as db:
            db[str(key)] = value

class SingleValueStore():
    def __init__(self, database_folder, identifier, default=None):
        self.identifier = identifier
        self._db_file = os.path.join(database_folder, "single_value_store.db")
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

# Class to provide a view into all persistent data available to the bot.
class Storage:
    def __init__(self, database_folder):
        self._database_folder = database_folder
        if not os.path.exists(self._database_folder):
            os.makedirs(self._database_folder)

        self.user_addresses = KeyValueStore(os.path.join(self._database_folder,
                                                         'user_addresses.db'))

        self.last_holders_update_timestamp = SingleValueStore(self._database_folder,"last_holders_update_timestamp", 0)

        self.top_miner_name = SingleValueStore(self._database_folder,"top_miner_name", "Nobody")
        self.top_miner_id = SingleValueStore(self._database_folder,"top_miner_id", 0)
        self.top_miner_difficulty = SingleValueStore(self._database_folder,"top_miner_difficulty", 0)
        self.top_miner_digest = SingleValueStore(self._database_folder,"top_miner_digest", b'\x00')

        # 0xBitcoin ATH Notes as of Oct 27 2018:
        # $4.66 on June 6 2018  https://www.coingecko.com/en/price_charts/0xbitcoin/usd
        # $4.57 on June 6 2018  https://coinmarketcap.com/currencies/0xbtc/historical-data/?start=20130428&end=20181027
        # $4.68  https://www.livecoinwatch.com/price/0xBitcoin-0xBTC
        # $4.655 on June 6 2018 06:00 UTC  https://coinlib.io/coin/0xBTC/0xBitcoin
        #
        # Price of Ethereum on June 6 2018 Min: 596.40  Max: 616.14 -> 606.27 Average
        # according to https://coinmarketcap.com/currencies/ethereum/
        # So this suggests the 0xBTC ATH in ETH is 4.68/606.27 = 0.007719
        #
        # BUT according to the 0xBitcoin discord, it hit 0.00849 eth on Mercatox.
        # @Azlehria even took a screenshot of the 0.00849 order in the books.
        # 
        #   https://cdn.discordapp.com/attachments/412483801265078273/453875157392687126/unknown.png
        # 
        #   0xbtc-price-bot BOT 06/06/2018
        #     Enclaves DEX 1m ago: $2.838 (0.00470 Ξ) +63.50% :chart_with_upwards_trend: [https://bit.ly/2rnYA7b]
        #     Fork Delta 1m ago: $4.595 (0.00761 Ξ) +0.00%  (ETH: $532) [https://bit.ly/2xr7AO4]
        #     Mercatox 1m ago: $5.127 (0.00849 Ξ) +173.99% :chart_with_upwards_trend: [http://bitly.com/2LvDE6u]
        #     IDEX 1m ago: $3.753 (0.00622 Ξ) +64.89% :chart_with_upwards_trend: [https://bit.ly/2stRdvt]
        #
        # So ATH in ETH/USD both were on June 6 2018
        #   USD: $4.68 (trackers) OR $5.13 (exchange apis)
        #   ETH: 0.007719 (trackers) OR 0.00849Ξ (exchange apis)
        #
        # Probably OK to use $4.68, 0.007719Ξ, timestamp 1528286400.0 (Noon GMT on June 6 2018)
        # `!setath 0.007719 2018-06-06 4.68 2018-06-06`

        self.all_time_high_usd_price = SingleValueStore(self._database_folder,"all_time_high_usd_price", 4.68)
        self.all_time_high_usd_timestamp = SingleValueStore(self._database_folder,"all_time_high_usd_timestamp", 1528286400.0)
        self.all_time_high_eth_price = SingleValueStore(self._database_folder,"all_time_high_eth_price", 0.007719)
        self.all_time_high_eth_timestamp = SingleValueStore(self._database_folder,"all_time_high_eth_timestamp", 1528286400.0)


if __name__ == "__main__":
    s = Storage('./databases')