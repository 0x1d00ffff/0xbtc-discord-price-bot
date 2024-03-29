
import collections

import configuration as config


CmdDef = collections.namedtuple('CmdDef', ['keywords', 'response'])


def string_contains_command(input_string, command, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True, ignore_matches_containing=None):
    """Look through an input_string, return True if it looks like a match for command
          - if exhaustive_search is true, look in the middle of string for commands - otherwise only check beginning
          - if permute_whitespace is true, replace spaces with dashes etc and also match those
          - if require_cmd_char is true, search only for `!command` - otherwise allow `command`
          - if ignore_matches_containing is a string, we will ignore any matches containing that string
    """
    if require_cmd_char:
        command = config.COMMAND_CHARACTER + command

    if ignore_matches_containing is not None and ignore_matches_containing in input_string:
        return False

    possible_commands = [command]
    if permute_whitespace:
        possible_commands.append(command.replace(' ', '-'))
        possible_commands.append(command.replace(' ', '_'))
        possible_commands.append(command.replace(' ', ''))

    if exhaustive_search:
        for possible_command in possible_commands:
            if possible_command in input_string:
                return True
    else:
        for possible_command in possible_commands:
            if input_string.startswith(possible_command):
                return True

    return False


def string_contains_any(input_string, command_list, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True, ignore_matches_containing=None, ignore_case=False):
    """similar to string_contains_command but accepts a list of multiple command synonyms"""
    if ignore_case:
        input_string = input_string.lower()
    for command in command_list:
        if ignore_case:
            command = command.lower()
        if string_contains_command(input_string, command, exhaustive_search, permute_whitespace, require_cmd_char, ignore_matches_containing):
            return True
    return False


def preprocess_message(message):
    """Pre-process a discord message to allow common typos and normalize input commands"""
    message = message.lower().strip()

    # allow '! command' since some platforms autocorrect to add a space
    if message.startswith(config.COMMAND_CHARACTER + ' '):
        message = config.COMMAND_CHARACTER + message[2:]

    # allow '!!command', its a common typo
    if message.startswith(config.COMMAND_CHARACTER + config.COMMAND_CHARACTER):
        message = config.COMMAND_CHARACTER + message[2:]

    # allow unicode ! (replace with ascii version)
    if config.COMMAND_CHARACTER == '!':
        if message.startswith('！'):
            message = '!' + message[1:]

    return message
