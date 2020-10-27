

import configuration as config
import util

from command_handlers import cmd_compare_price_vs


async def handle_global_command(command_str, discord_message, apis):
    if command_str[0] != config.COMMAND_CHARACTER:
        return None

    for cmd_def in config.GLOBAL_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            if isinstance(cmd_def.response, str):
                return cmd_def.response
            else:
                return await cmd_def.response(command_str, discord_message, apis)
    return None

async def handle_trading_command(command_str, discord_message, apis):
    msg = None

    # Check price comparision commands (defined in EXPENSIVE_STUFF in configuration.py)
    # TODO: move this into _TRADING_COMMANDS somehow
    for price, names in config.EXPENSIVE_STUFF:
        if util.string_contains_any(
                command_str,
                (name.lower() for name in names),
                exhaustive_search=True):
            correct_name = names[0]
            msg = await cmd_compare_price_vs(apis, correct_name, price)
            break

    if command_str[0] != config.COMMAND_CHARACTER:
        return None

    for cmd_def in config.TRADING_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            if isinstance(cmd_def.response, str):
                return cmd_def.response
            else:
                return await cmd_def.response(command_str, discord_message, apis)



    return msg
