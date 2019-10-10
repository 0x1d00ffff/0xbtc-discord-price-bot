
import unittest
import time
import datetime

from mock_discord_classes import MockClient, MockMessage

import configuration as config


def generate_command_list():
    return ([cmd_def.keywords[0] for cmd_def in (config.GLOBAL_COMMANDS 
                                                 + config.TRADING_COMMANDS)]
             + [entry[1][0] for entry in config.EXPENSIVE_STUFF]
             + ['bettervolume',
                'price all',
                'price enclaves',
                'price fd',
                'price idex',
                'price merc',
                'price ethex',
                'price eth',
                'mine test 0x0 0x0 0x0'])

def get_fuzzing_iterator(seed=None):
    import random
    import string

    myrandom = random.Random(seed)
    command_strings = generate_command_list()
    idx = 0

    while(True):
        # generate numbers/bytes to mix in with the commands which are 
        # changed every 128 iterations
        if idx % 128 == 0:
            # create a few random floats
            numbers = ([myrandom.uniform(-1e30, 1e30) for _ in range(5)]
                       + [myrandom.uniform(-100, 100) for _ in range(5)])
            # add the integer versions also
            numbers += [int(i) for i in numbers]
            printable = [''.join(myrandom.choices(string.printable, k=8)) for _ in range(20)]
            garbage = [''.join(chr(myrandom.randint(0,255)) for _ in range(8)) for _ in range(20)]
            full_chunk_set = (command_strings 
                              + [str(i) for i in numbers]
                              + printable
                              + garbage)

        # number of pieces to combine to create a command (2-5)
        num_chunks = (idx % 4) + 2
        yield ' '.join(myrandom.choices(full_chunk_set, k=num_chunks))
        idx += 1

def run_command_blocking(apis, command_str, add_command_char=True):
    import asyncio
    from commands import handle_global_command, handle_trading_command

    if add_command_char:
        command_str = config.COMMAND_CHARACTER + command_str
    response = asyncio.get_event_loop().run_until_complete(handle_global_command(command_str, MockMessage(), apis))
    if response is None:
        response = asyncio.get_event_loop().run_until_complete(handle_trading_command(command_str, MockMessage(), apis))
    return response

def run_and_log_command(apis, command_str):
    import logging
    try:       
        response = run_command_blocking(apis, command_str)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        logging.exception("Exception running command '{}'".format(repr(command_str)))
    else:
        if isinstance(response, str) or response is None:
            pass
        else:
            logging.exception("Response '{}' while running command '{}'".format(repr(response), repr(command_str)))
        if response == "":
            logging.exception("Response '{}' while running command '{}'".format(repr(response), repr(command_str)))

class TestPriceCommand(unittest.TestCase):

    # def __init__(self, methodName='runTest', use_real_randomness=False, fuzz_iterations=None):
    #     # calling the super class init varies for different python versions.  This works for 2.7
    #     super(TestPriceCommand, self).__init__(methodName)
    #     self._use_real_randomness = use_real_randomness
    #     self._fuzz_iterations = use_real_randomness

    # def setUp(self):
    #     pass

    @classmethod
    def setUpClass(cls):
        from main import apis, manual_api_update
        import asyncio
        asyncio.get_event_loop().run_until_complete(manual_api_update())
        cls.apis = apis

    def run_and_verify_command(self, command_str, add_command_char=True, check_for_errors=True):
        response = run_command_blocking(self.apis, command_str, add_command_char)

        if check_for_errors:
            for error_string in [':shrug:', 
                                 'not sure yet... waiting on my APIs',
                                 'Something went wrong',
                                 'Bad currency',
                                 'Bad command',
                                 'Bad nonce',
                                 'Bad hashrate',
                                 'Bad address',
                                 'Error']:
                with self.subTest(error_string=error_string):
                    self.assertFalse(error_string in response)

        return response

    def test_that_all_commands_run(self):
        command_strings = generate_command_list()

        for command_str in command_strings:
            with self.subTest(command_str=command_str):
                # commands that we expect to fail - the first couple need args
                if ( 'convert' in command_str
                     or 'income' in command_str
                     or 'mine' in command_str
                     or 'set address' in command_str
                     or 'setath' in command_str
                     or 'setathfilename' in command_str
                     or 'setbestshare' in command_str
                     or 'balance' in command_str
                     # individual exchange apis may fail; so we don't care what
                     # the response is - only that is does not throw an exception
                     or 'price all' in command_str
                     or 'price enclaves' in command_str
                     or 'price fd' in command_str
                     or 'price idex' in command_str
                     or 'price merc' in command_str
                     or 'price ethex' in command_str):
                    response = self.run_and_verify_command(command_str, check_for_errors=False)
                else:
                    response = self.run_and_verify_command(command_str)
            
                self.assertIsNotNone(response)
                self.assertTrue(isinstance(response, str))
                self.assertTrue(len(response) > 0)

    def test_specific_commands(self):
        command_str='price'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
        command_str='price all'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
            self.assertTrue("Fork Delta" in response 
                            or "Mercatox" in response 
                            or "Fork Delta" in response 
                            or "IDEX" in response)
            self.assertTrue(len(response.split('\n')) > 1)
        command_str='price forkdelta'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str, check_for_errors=False)
            self.assertTrue("Fork Delta" in response or "not sure yet" in response)
            self.assertTrue(len(response.split('\n')) == 1)
        command_str='price enclaves'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str, check_for_errors=False)
            self.assertTrue("Enclaves DEX" in response or "not sure yet" in response)
            self.assertTrue(len(response.split('\n')) == 1)

        command_strings = ['price eth', 'eth']
        for command_str in command_strings:
            with self.subTest(command_str=command_str):
                response = self.run_and_verify_command(command_str, check_for_errors=False)
                self.assertTrue("Ethereum price" in response)
                self.assertTrue("$" in response)
                self.assertTrue(len(response.split('\n')) == 1)

        command_strings = ['price btc', 'btc']
        for command_str in command_strings:
            with self.subTest(command_str=command_str):
                response = self.run_and_verify_command(command_str, check_for_errors=False)
                self.assertTrue("Bitcoin price" in response)
                self.assertTrue("$" in response)
                self.assertTrue(len(response.split('\n')) == 1)

        command_str='volume'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
            self.assertTrue("Total:" in response)
        command_str='bettervolume'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue(":star2:" in response)
            self.assertTrue("Total:" in response)
        command_str='marketcap'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Marketcap:" in response)
            self.assertTrue("Circulating Supply:" in response)
        command_str='difficulty'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("difficulty:" in response)
        command_str='hashrate'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("hashrate" in response)
            self.assertTrue("/s" in response)
        command_str='era'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Current era:" in response)
        command_str='ath'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("All time high" in response)
        command_str='convert 1 eth to usd'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("1.000 eth =" in response)
            self.assertTrue("usd" in response)
        command_str='convert 0,89 eth to usd'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("0.89 eth =" in response)
            self.assertTrue("usd" in response)
        command_str='income 3'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Income for 3.0 Gh/s:" in response)
            self.assertTrue(" tokens/" in response)
            self.assertTrue("per block solo" in response)
        command_str='income 3.5mh'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Income for 3.5 Mh/s:" in response)
            self.assertTrue(" tokens/" in response)
            self.assertTrue("per block solo" in response)
        command_str='income 3,5mh'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Income for 3.5 Mh/s:" in response)
            self.assertTrue(" tokens/" in response)
            self.assertTrue("per block solo" in response)
        command_str='balance 0x0000000000000000000000000000000000000000'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("0xBitcoin balance:" in response)
        command_str='setaddress dontcare'
        with self.subTest(command_str=command_str):
            # this one doesn't respond, it just adds a reaction. could check log
            response = self.run_and_verify_command(command_str)
        command_str='setaddress 0x0000000000000000000000000000000000000000'
        with self.subTest(command_str=command_str):
            # this one doesn't respond, it just adds a reaction. could check log
            response = self.run_and_verify_command(command_str)
        command_str='setath 0.0 2000-01-01 0.0 2000-01-01'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("New ATH set!" in response)
            response = self.run_and_verify_command('ath')
            self.assertTrue("All time high: **0Ξ** **$0** (Sat January 1 2000)" in response)
        command_str='setath 0.001 2001-02-03 4.05 2006-07-08'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("New ATH set!" in response)
            response = self.run_and_verify_command('ath')
            self.assertTrue("All time high: \n**0.001Ξ** (Sat February 3 2001)  **$4.050** (Sat July 8 2006)" in response)
        command_str='setbestshare Username1 2 0x3 45'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("New best share set!" in response)
            response = self.run_and_verify_command('bestshare')
            self.assertTrue("Best share digest: `0x03...` (Difficulty: 45.00) by Username1" in response)
        command_str='setbestshare Username0 0 0x00 0'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("New best share set!" in response)
            response = self.run_and_verify_command('bestshare')
            self.assertTrue("Best share digest: `0x00...` (Difficulty: 0) by Username0" in response)
        command_str='mine 123'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("New best share!" in response)
            self.assertTrue("Previous was" in response)
            self.assertTrue("Difficulty: 0" in response)
            self.assertTrue("by Username0" in response)
            self.assertTrue("Nonce" in response)
            self.assertTrue("Digest" in response)
            self.assertTrue("Diff" in response)
            self.assertTrue("solution" in response)
        command_str='bestshare'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Best share digest" in response)
            self.assertTrue("by Test Name" in response)
        command_str='pools'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Token Mining Pool" in response)
            self.assertTrue("mike.rs" in response)
            self.assertTrue(len(response.split('\n')) > 1)
        command_str='hug'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("SQUEE" in response)
        command_str='hi'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("Sup" in response)
        command_str='lambo'
        with self.subTest(command_str=command_str):
            response = self.run_and_verify_command(command_str)
            self.assertTrue("1 lambo =" in response)
            self.assertTrue("$" in response)

    def test_fuzzing_commands(self):
        import logging
        # iterations: seconds on i7-5700HQ
        # 256:  13, 12
        # 512:  14, 12
        # 1024: 35, 35, 37, 43
        # 2048: 58
        # 8192: 217
        # 32768: 759
        try: 
            self._fuzz_iterations
        except AttributeError:
            iterations = 512
        else:
            iterations = self._fuzz_iterations

        # fixed seed so randomness is repeatable
        for idx, command_str in enumerate(get_fuzzing_iterator(seed="myseed")):
            with self.subTest(command_str=command_str):
                response = self.run_and_verify_command(command_str, check_for_errors=False)
                self.assertTrue(isinstance(response, str) or response is None)
                self.assertTrue(response != "")
            if idx >= iterations - 1:
                break

class TestDecimalFormatting(unittest.TestCase):
    def test_round_to_n(self):
        from formatting_helpers import round_to_n_decimals
        self.assertEqual(round_to_n_decimals(0.00000012345),    0.0000001)
        self.assertEqual(round_to_n_decimals(0.00012345),       0.0001)
        self.assertEqual(round_to_n_decimals(1234567),          1000000)

        self.assertEqual(round_to_n_decimals(0.00000012345, 3), 0.000000123)
        self.assertEqual(round_to_n_decimals(1234567, 3),       1230000)

    def test_prettify_decimals(self):
        from formatting_helpers import prettify_decimals
        self.assertEqual(prettify_decimals(0),   '0')
        self.assertEqual(prettify_decimals(0.0032),           '0.0032')
        self.assertEqual(prettify_decimals(0.00160),          '0.0016')

        self.assertEqual(prettify_decimals(0.00000000000000123456), '1.23e-15')
        self.assertEqual(prettify_decimals(0.0000000000000123456),  '1.23e-14')
        self.assertEqual(prettify_decimals(0.000000000000123456),   '1.23e-13')
        self.assertEqual(prettify_decimals(0.00000000000123456),    '0.00000000000123')
        self.assertEqual(prettify_decimals(0.0000000000123456),     '0.0000000000123')
        self.assertEqual(prettify_decimals(0.000000000123456),      '0.000000000123')
        self.assertEqual(prettify_decimals(0.00000000123456),       '0.00000000123')
        self.assertEqual(prettify_decimals(0.0000000123456),        '0.0000000123')
        self.assertEqual(prettify_decimals(0.000000123456),         '0.000000123')
        self.assertEqual(prettify_decimals(0.00000123456),          '0.00000123')
        self.assertEqual(prettify_decimals(0.0000123456),           '0.0000123')
        self.assertEqual(prettify_decimals(0.000123456),            '0.000123')
        self.assertEqual(prettify_decimals(0.00123456),             '0.00123')
        self.assertEqual(prettify_decimals(0.012345678),            '0.0123')
        self.assertEqual(prettify_decimals(0.12345678),             '0.123')
        self.assertEqual(prettify_decimals(1.2345678),              '1.235')
        self.assertEqual(prettify_decimals(12.345678),              '12.35')
        self.assertEqual(prettify_decimals(123.45678),              '123.46')
        self.assertEqual(prettify_decimals(1234.5678),              '1234.57')
        self.assertEqual(prettify_decimals(12345.6789),             '12,346')
        self.assertEqual(prettify_decimals(12345),                  '12,345')
        self.assertEqual(prettify_decimals(123456789),              '123,456,789')
        self.assertEqual(prettify_decimals(1234567890),             '1.2 billion')
        self.assertEqual(prettify_decimals(12345678901),            '12.3 billion')
        self.assertEqual(prettify_decimals(123456789012),           '123.5 billion')
        self.assertEqual(prettify_decimals(12345678901234),         '12.3 trillion')
        self.assertEqual(prettify_decimals(123456789012345),        '123.5 trillion')
        self.assertEqual(prettify_decimals(1234567890123456),       '1.23e15')
        self.assertEqual(prettify_decimals(12345678901234567),      '1.23e16')
        self.assertEqual(prettify_decimals(123456789012345678),     '1.23e17')

    def test_fuzzing_prettify_decimals(self):
        from formatting_helpers import prettify_decimals
        import random
        iterations = 100000  # 4 seconds on an i7-5700HQ
        min_value, max_value = -1e30, 1e30
        # fixed seed so randomness is repeatable
        myrandom = random.Random("myseed")
        # test formatting integers
        for _ in range(iterations):
            number = myrandom.randint(min_value, max_value)
            with self.subTest(number=number):
                formatted = prettify_decimals(number)
                self.assertTrue(isinstance(formatted, str))
                self.assertTrue(len(formatted) <= 16)
        # test formatting floats
        for _ in range(iterations):
            number = myrandom.uniform(min_value, max_value)
            with self.subTest(number=number):
                formatted = prettify_decimals(number)
                self.assertTrue(isinstance(formatted, str))
                self.assertTrue(len(formatted) <= 16)

    def test_str_to_float(self):
        from formatting_helpers import string_to_float

        self.assertEqual(string_to_float('0.89'),           0.89)
        self.assertEqual(string_to_float('1000.5'),         1000.5)
        self.assertEqual(string_to_float('0,89'),           0.89)
        self.assertEqual(string_to_float('1,000.5'),        1000.5)

        self.assertEqual(string_to_float('0.00000012345'),  0.00000012345)
        self.assertEqual(string_to_float('0.00012345'),     0.00012345)
        self.assertEqual(string_to_float('1234567'),        1234567)

class TestMineableTokenInfo(unittest.TestCase):
    
    def setUp(self):
        from mineable_token_info import MineableTokenInfo
        from web3 import Web3
        self.m = MineableTokenInfo(config.TOKEN_ETH_ADDRESS)
        self.m.update()

    @unittest.skipIf(config.TOKEN_SYMBOL != "0xBTC",
                     "This test assumes 0xBTC and must be modified for other currencies")
    def test_reading_0xbtc_values(self):
        m = self.m

        self.assertIsNotNone(m.symbol)
        self.assertIsNotNone(m.total_supply)
        self.assertIsNotNone(m.last_difficulty_start_block)
        self.assertIsNotNone(m.mining_target)
        self.assertIsNotNone(m.difficulty)
        self.assertIsNotNone(m.tokens_minted)
        self.assertIsNotNone(m.addr_0_balance)
        self.assertIsNotNone(m.seconds_since_readjustment)
        self.assertIsNotNone(m.seconds_per_reward)
        self.assertIsNotNone(m.era)
        self.assertIsNotNone(m.estimated_hashrate_since_readjustment)
        # this test fails - infura v3 api does not support the calls necessary
        #self.assertIsNotNone(m.estimated_hashrate_24h)
        self.assertIsNotNone(m.max_supply_for_era)
        self.assertIsNotNone(m.reward)
        self.assertIsNotNone(m.seconds_remaining_in_era)

        self.assertTrue(m.symbol == "0xBTC")
        self.assertTrue(19000000 < m.total_supply < 20999983.97)
        self.assertTrue(6560003 < m.last_difficulty_start_block < 1e10)

        self.assertTrue(m.min_target <= m.mining_target <= m.max_target)

        self.assertTrue(0 < m.difficulty < 1e30)
        self.assertTrue(3302800 < m.tokens_minted < 21000000.1)
        self.assertTrue(0 < m.addr_0_balance < 2000000)
        self.assertTrue(0 < m.seconds_since_readjustment < 60*60*24*31*12)
        self.assertTrue(0 < m.seconds_per_reward < 60*60*24*31)
        self.assertTrue(0 < m.seconds_until_readjustment < 60*60*24*31*12)
        self.assertTrue(0 <= m.era < 40)
        self.assertTrue(0 < m.max_supply_for_era < 10500001)
        self.assertTrue(0 < m.reward <= 50.0)
        self.assertTrue(0 <= m.seconds_remaining_in_era < 1e30)

        self.assertTrue(100000 < m.estimated_hashrate_since_readjustment < 1e30)

        # these tests fail - infura v3 api does not support the calls necessary
        # to support 24-hour average hashrate anymore, unfortunately
        ## self.assertTrue(100000 < m.estimated_hashrate_24h < 1e30)
        ## hashrate_over_2_days = m._estimated_hashrate_n_days(2)
        ## self.assertTrue(100000 < hashrate_over_2_days < 1e30)
        ## # this check technically could fail, but it should be unlikely enough
        ## self.assertTrue(m.estimated_hashrate_24h != hashrate_over_2_days)

        events_in_last_2_days = m.get_events_last_n_days(2)
        self.assertIsNotNone(events_in_last_2_days)
        self.assertTrue(len(events_in_last_2_days) > 0)
        self.assertTrue(events_in_last_2_days[-1]['type'] in ['mint', 'transfer', 'approve'])

    def test_hashing_nonces(self):
        from web3 import Web3
        nonces = [b'\x00', b'\x00\x0F', b'test']
        for n in nonces:
            with self.subTest(nonce=n):
                nonce, digest = self.m.get_digest_for_nonce(n, "0x0000000000000000000000000000000000000000")
                self.assertIsNotNone(nonce)
                self.assertEqual(len(nonce), 32)
                self.assertIsNotNone(digest)
                self.assertTrue(self.m.min_target < Web3.toInt(digest))

        nonces = ["0x41", "65", "A"]
        digests = []
        for n in nonces:
            with self.subTest(nonce=n):
                nonce, digest = self.m.get_digest_for_nonce_str(n, "0x0000000000000000000000000000000000000000")
                self.assertIsNotNone(nonce)
                self.assertEqual(len(nonce), 32)
                self.assertIsNotNone(digest)
                self.assertNotEqual(digest, b'\x00')
                self.assertNotEqual(digest, b'')
                self.assertTrue(self.m.min_target < Web3.toInt(digest))

                digests.append(digest)

        self.assertEqual(digests[0], digests[1])
        self.assertEqual(digests[1], digests[2])

        nonce, digest_short = self.m.get_digest_for_nonce_str("0xFF1234",
                                                              "0x0000000000000000000000000000000000000000")
        self.assertEqual(nonce, Web3.toBytes(hexstr='0xff12340000000000000000000000000000000000000000000000000000000000'))
        self.assertIsNotNone(digest_short)
        self.assertTrue(self.m.min_target < Web3.toInt(digest_short))

        nonce, digest_long = self.m.get_digest_for_nonce_str("0xff12340000000000000000000000000000000000000000000000000000000000ab",
                                                             "0x0000000000000000000000000000000000000000")
        self.assertEqual(nonce, Web3.toBytes(hexstr="0xff12340000000000000000000000000000000000000000000000000000000000"))
        self.assertIsNotNone(digest_long)
        self.assertTrue(self.m.min_target < Web3.toInt(digest_long))

        self.assertEqual(digest_short, digest_long)

        nonce, digest = self.m.get_digest_for_nonce_str("0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74",
                                                        "0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6",
                                                        "0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a")

        self.assertEqual(nonce, Web3.toBytes(hexstr="0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74"))
        self.assertEqual(digest, Web3.toBytes(hexstr="0x000000000a7ddfa621b3a1aa9605da95185cb75a6a91bafb2976f36606c4d5e2"))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestDecimalFormatting("test_prettify_decimals"))
    suite.addTest(TestDecimalFormatting("test_fuzzing_prettify_decimals"))
    suite.addTest(TestDecimalFormatting("test_round_to_n"))
    suite.addTest(TestDecimalFormatting("test_str_to_float"))

    suite.addTest(TestMineableTokenInfo("test_reading_0xbtc_values"))
    suite.addTest(TestMineableTokenInfo("test_hashing_nonces"))

    suite.addTest(TestPriceCommand('test_that_all_commands_run'))
    suite.addTest(TestPriceCommand('test_specific_commands'))
    suite.addTest(TestPriceCommand('test_fuzzing_commands'))

    return suite

def run_all():
    runner = unittest.TextTestRunner()
    runner.run(suite())

def run_command_fuzzer():
    import logging
    import asyncio
    import time
    from main import apis, manual_api_update
    from formatting_helpers import prettify_decimals
    commands_per_log_message = 150000  # about 1 hour on a 4th gen i7

    logging.info("Starting fuzz test. Ctrl+C to exit. Errors are logged to console.")

    asyncio.get_event_loop().run_until_complete(manual_api_update())
    time_last = time.time()

    # no seed; each run should be unique
    for idx, command_str in enumerate(get_fuzzing_iterator()):
        run_and_log_command(apis, command_str)

        if idx != 0 and idx % commands_per_log_message == 0:

            time_now = time.time()
            time_delta = time_now - time_last
            time_per_command = time_delta / commands_per_log_message
            commands_per_second = 1 / time_per_command
            time_last = time_now

            fmt_str = "{:>14} commands {:>14} cmds/sec"
            logging.info(fmt_str.format(idx,
                                        prettify_decimals(commands_per_second)))
