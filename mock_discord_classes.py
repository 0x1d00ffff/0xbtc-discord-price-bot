
import datetime
import logging


class MockClient():
    def __init__(self):
        self.is_closed = False

    def wait_until_ready(self):
        pass

    async def change_presence(self, game=None, status=None, afk=None):
        args = {'game': game, 'status': status, 'afk': afk}
        #logging.debug('Call to change_presence: {}'.format(args))

    async def add_reaction(self, discord_message=None, emoji=None):
        args = {'discord_message': discord_message, 'emoji': emoji}
        #logging.debug('Call to add_reaction: {}'.format(args))

    async def send_file(self, channel=None, filename=None):
        args = {'channel': channel, 'filename': filename}
        #logging.debug('Call to send_file: {}'.format(args))


class MockAuthor():
    def __init__(self):
        self.name = "Test Name"
        self.id = '0'


class MockMessage():
    def __init__(self):
        self.channel = None
        self.author = MockAuthor()
        #self.timestamp = datetime.datetime.utcnow()
        self.created_at = datetime.datetime.utcnow()
    async def add_reaction(self, emoji=None):
        args = {'emoji': emoji}
        #logging.debug('Call to add_reaction: {}'.format(args))
