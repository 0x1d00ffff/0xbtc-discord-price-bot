import configuration as config

# look through an input_string, return True if it looks like a match for command
# if exhaustive_search is true, look in the middle of string for commands - otherwise only check beginning
# if permute_whitespace is true, replace spaces with dashes etc and also match those
# if require_cmd_char is true, search only for `!command` - otherwise allow `command`
def string_contains_command(input_string, command, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True):
    possible_commands = [command]
    if permute_whitespace:
        possible_commands.append(command.replace(' ', '-'))
        possible_commands.append(command.replace(' ', '_'))
        possible_commands.append(command.replace(' ', ''))

    if exhaustive_search:
        for possible_command in possible_commands:
            if require_cmd_char:
                possible_command = config.COMMAND_CHARACTER+possible_command
            if possible_command in input_string:
                return True
    else:
        for possible_command in possible_commands:
            if require_cmd_char:
                possible_command = config.COMMAND_CHARACTER+possible_command
            if input_string.startswith(possible_command):
                return True

    return False

# similar to string_contains_command but accepts a list of multiple command synonyms
def string_contains_any(input_string, command_list, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True):
    for command in command_list:
        if string_contains_command(input_string, command, exhaustive_search, permute_whitespace, require_cmd_char):
            return True

    return False