import unittest
import time
import datetime

from mock_discord_classes import MockClient, MockMessage

import configuration as config


class TestPriceCommand(unittest.TestCase):
    def setUp(self):
        pass

    @classmethod
    def setUpClass(cls):
        from main import apis, manual_api_update
        manual_api_update()
        cls.apis = apis

    def run_command(self, command_str, add_command_char=True, check_for_errors=True):
        import asyncio
        from commands import handle_global_command, handle_trading_command

        if add_command_char:
            command_str = config.COMMAND_CHARACTER + command_str
        response = asyncio.get_event_loop().run_until_complete(handle_global_command(command_str, MockMessage(), self.apis))
        if response is None:
            response = asyncio.get_event_loop().run_until_complete(handle_trading_command(command_str, MockMessage(), self.apis))
        
        if check_for_errors:
            for error_string in [':shrug:', 
                                 'not sure yet... waiting on my APIs',
                                 'Something went wrong',
                                 'Bad currency',
                                 'Bad command',
                                 'Bad nonce',
                                 'Bad hashrate',
                                 'Error parsing']:
                with self.subTest(error_string=error_string):
                    self.assertFalse(error_string in response)

        return response

    def test_that_all_commands_run(self):
        command_strings = [cmd_def.keywords[0] for cmd_def in config.GLOBAL_COMMANDS + config.TRADING_COMMANDS]
        # add some commands not found by automatically scanning the command list
        command_strings += ['bettervolume',
                            'price enclaves',
                            'price fd',
                            'price idex',
                            'price merc',
                            'price ethex',
                            'price eth',
                            'mine test 0x0 0x0 0x0']

        for command_str in command_strings:
            with self.subTest(command_str=command_str):
                # commands that we expect to fail - the first couple need args
                if ( 'convert' in command_str
                     or 'income' in command_str
                     or 'mine' in command_str
                     or 'set address' in command_str
                     or 'setath' in command_str
                     or 'setbestshare' in command_str
                     # individual exchange apis may fail; so we don't care what
                     # the response is - only that is does not throw an exception
                     or 'price enclaves' in command_str
                     or 'price fd' in command_str
                     or 'price idex' in command_str
                     or 'price merc' in command_str
                     or 'price ethex' in command_str):
                    response = self.run_command(command_str, check_for_errors=False)
                else:
                    response = self.run_command(command_str)
            
                self.assertIsNotNone(response)
                self.assertTrue(isinstance(response, str))
                self.assertTrue(len(response) > 0)

    def test_specific_commands(self):
        command_str='price'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
        command_str='price forkdelta'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
        command_str='volume'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Ξ" in response)
            self.assertTrue("Total:" in response)
        command_str='bettervolume'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue(":star2:" in response)
            self.assertTrue("Total:" in response)
        command_str='marketcap'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("$" in response)
            self.assertTrue("." in response)
            self.assertTrue("Marketcap:" in response)
            self.assertTrue("Circulating Supply:" in response)
        command_str='difficulty'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("difficulty:" in response)
        command_str='hashrate'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("hashrate" in response)
            self.assertTrue("/s" in response)
        command_str='era'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("Current era:" in response)
        command_str='ath'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("All time high" in response)
        command_str='convert 1 eth to usd'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("1.000 eth =" in response)
            self.assertTrue("usd" in response)
        command_str='income 3'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("Income for 3.0 Gh/s:" in response)
            self.assertTrue(" tokens/" in response)
            self.assertTrue("per block solo" in response)
        command_str='setaddress 0x0000000000000000000000000000000000000000'
        with self.subTest(command_str=command_str):
            # this one doesn't respond, it just adds a reaction. could check log
            response = self.run_command(command_str)
        command_str='setath 0.0 2000-01-01 0.0 2000-01-01'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("New ATH set!" in response)
            response = self.run_command('ath')
            self.assertTrue("All time high: **0Ξ** **$0** (Sat January 1 2000)" in response)
        command_str='setath 0.001 2001-02-03 4.05 2006-07-08'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("New ATH set!" in response)
            response = self.run_command('ath')
            self.assertTrue("All time high: \n**0.001Ξ** (Sat February 3 2001)  **$4.050** (Sat July 8 2006)" in response)
        command_str='setbestshare Username1 2 0x3 45'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("New best share set!" in response)
            response = self.run_command('bestshare')
            self.assertTrue("Best share digest: `0x03...` (Difficulty: 45.00) by Username1" in response)
        command_str='setbestshare Username0 0 0x00 0'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
            self.assertTrue("New best share set!" in response)
            response = self.run_command('bestshare')
            self.assertTrue("Best share digest: `0x00...` (Difficulty: 0) by Username0" in response)
        command_str='mine 123'
        with self.subTest(command_str=command_str):
            response = self.run_command(command_str)
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
            response = self.run_command(command_str)
            self.assertTrue("Best share digest" in response)
            self.assertTrue("by Test Name" in response)

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

        self.assertIsNotNone(m.total_supply)
        self.assertIsNotNone(m.last_difficulty_start_block)
        self.assertIsNotNone(m.mining_target)
        self.assertIsNotNone(m.difficulty)
        self.assertIsNotNone(m.tokens_minted)
        self.assertIsNotNone(m.addr_0_balance)
        self.assertIsNotNone(m.seconds_since_readjustment)
        self.assertIsNotNone(m.seconds_per_reward)
        self.assertIsNotNone(m.era)
        self.assertIsNotNone(m.estimated_hashrate)
        self.assertIsNotNone(m.max_supply_for_era)
        self.assertIsNotNone(m.reward)
        self.assertIsNotNone(m.seconds_remaining_in_era)

        self.assertTrue(19000000 < m.total_supply < 20999983.97)
        self.assertTrue(6560003 < m.last_difficulty_start_block < 1e10)

        self.assertTrue(self.m.MIN_TARGET <= m.mining_target <= m.MAX_TARGET)

        self.assertTrue(0 < m.difficulty < 1e30)
        self.assertTrue(3302800 < m.tokens_minted < 21000000.1)
        self.assertTrue(0 < m.addr_0_balance < 2000000)
        self.assertTrue(0 < m.seconds_since_readjustment < 60*60*24*31*12)
        self.assertTrue(0 < m.seconds_per_reward < 60*60*24*31)
        self.assertTrue(0 < m.seconds_until_readjustment < 60*60*24*31*12)
        self.assertTrue(0 <= m.era < 40)
        self.assertTrue(100000 < m.estimated_hashrate < 1e30)
        self.assertTrue(0 < m.max_supply_for_era < 10500001)
        self.assertTrue(0 < m.reward < 51)
        self.assertTrue(0 <= m.seconds_remaining_in_era < 1e30)

    def test_hashing_nonces(self):
        from web3 import Web3
        nonces = [b'\x00', b'\x00\x0F', b'test']
        for n in nonces:
            with self.subTest(nonce=n):

                nonce, digest = self.m.get_digest_for_nonce(n,
                                                            "0x0000000000000000000000000000000000000000")
                self.assertIsNotNone(nonce)
                self.assertEqual(len(nonce), 32)
                self.assertIsNotNone(digest)
                self.assertTrue(self.m.MIN_TARGET < Web3.toInt(digest))

        nonces = ["0x41", "65", "A"]
        digests = []
        for n in nonces:
            with self.subTest(nonce=n):
                nonce, digest = self.m.get_digest_for_nonce_str(n,
                                                                "0x0000000000000000000000000000000000000000")
                self.assertIsNotNone(nonce)
                self.assertEqual(len(nonce), 32)
                self.assertIsNotNone(digest)
                self.assertNotEqual(digest, b'\x00')
                self.assertNotEqual(digest, b'')
                self.assertTrue(self.m.MIN_TARGET < Web3.toInt(digest))

                digests.append(digest)

        self.assertEqual(digests[0], digests[1])
        self.assertEqual(digests[1], digests[2])

        nonce, digest_short = self.m.get_digest_for_nonce_str("0xFF1234",
                                                              "0x0000000000000000000000000000000000000000")
        self.assertEqual(nonce, Web3.toBytes(hexstr='0xff12340000000000000000000000000000000000000000000000000000000000'))
        self.assertIsNotNone(digest_short)
        self.assertTrue(self.m.MIN_TARGET < Web3.toInt(digest_short))

        nonce, digest_long = self.m.get_digest_for_nonce_str("0xff12340000000000000000000000000000000000000000000000000000000000ab",
                                                             "0x0000000000000000000000000000000000000000")
        self.assertEqual(nonce, Web3.toBytes(hexstr="0xff12340000000000000000000000000000000000000000000000000000000000"))
        self.assertIsNotNone(digest_long)
        self.assertTrue(self.m.MIN_TARGET < Web3.toInt(digest_long))

        self.assertEqual(digest_short, digest_long)

        nonce, digest = self.m.get_digest_for_nonce_str("0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74",
                                                        "0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6",
                                                        "0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a")

        self.assertEqual(nonce, Web3.toBytes(hexstr="0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74"))
        self.assertEqual(digest, Web3.toBytes(hexstr="0x000000000a7ddfa621b3a1aa9605da95185cb75a6a91bafb2976f36606c4d5e2"))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestDecimalFormatting("test_prettify_decimals"))
    suite.addTest(TestDecimalFormatting("test_round_to_n"))

    suite.addTest(TestMineableTokenInfo("test_reading_0xbtc_values"))
    suite.addTest(TestMineableTokenInfo("test_hashing_nonces"))

    suite.addTest(TestPriceCommand('test_that_all_commands_run'))
    suite.addTest(TestPriceCommand('test_specific_commands'))
    return suite

def run_all():
    runner = unittest.TextTestRunner()
    runner.run(suite())
    