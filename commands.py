

import configuration as config
import util


async def handle_global_command(command_str, discord_message, apis):
    for cmd_def in config.GLOBAL_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            if isinstance(cmd_def.response, str):
                return cmd_def.response
            else:
                return await cmd_def.response(command_str, discord_message, apis)
    return None

async def handle_trading_command(command_str, discord_message, apis):
    msg = None

    for cmd_def in config.TRADING_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            if isinstance(cmd_def.response, str):
                return cmd_def.response
            else:
                return await cmd_def.response(command_str, discord_message, apis)

    # TODO: move this into _TRADING_COMMANDS somehow
    for price, names in config.EXPENSIVE_STUFF:
        if util.string_contains_any(command_str, names, exhaustive_search=True):
            correct_name = names[0]
            msg = cmd_compare_price_vs(apis, correct_name, price)
            break

    return msg
