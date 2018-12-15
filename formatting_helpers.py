import datetime
import platform

def unix_timestamp_to_readable_date(timestamp):
    time = datetime.datetime.fromtimestamp(timestamp)

    if platform.system() == "Linux":
        return time.strftime("%a %B %-e %Y")
    else:
        return time.strftime("%a %B %#e %Y")

def unix_timestamp_to_readable_date_time(timestamp):
    time = datetime.datetime.fromtimestamp(timestamp)

    if platform.system() == "Linux":
        return time.strftime("%a %B %-e %Y")
    else:
        return time.strftime("%a %B %#e %Y")

def string_to_float(value):
    """custom version of float() that supports commas as decimal separators
    when the input contains no periods"""
    # if no periods (.) then assume commas are decimal separators
    if '.' not in value:
        value = value.replace(',', '.')
    # if decimals exist then simply remove commas
    else:
        value = value.replace(',', '')

    return float(value)

def percent_change_to_emoji(percent_change):
    values = [
        # [0.3, ":arrow_up:"],
        # [0.1, ":arrow_upper_right:"],
        # [-0.1, ":arrow_right:"],
        # [-0.3, ":arrow_lower_right:"],
        # [-1, ":arrow_down:"],
        [0.3, ":chart_with_upwards_trend:"],
        [0.1, ""],
        [-0.1, ""],
        [-0.3, ""],
        [-1, ":chart_with_downwards_trend:"],
    ]
    for v in values:
        if percent_change > v[0]:
            return v[1]
    # return the last option as fallback
    return values[-1:][0][1]

def round_to_n_decimals(x, n=1):
    from math import log10, floor
    assert n >= 1
    return round(x, -int(floor(log10(abs(x))))+n-1)

def prettify_decimals(number):
    if number == 0:
        return "0"
    if number < 1e-12:
        rounded = round_to_n_decimals(number, 3)
        return "{:.2e}".format(rounded)
    if number < 1.0:
        rounded = round_to_n_decimals(number, 3)
        return "{:.14f}".format(rounded).rstrip("0")
    if number < 10.0:
        rounded = round_to_n_decimals(number, 4)
        return "{:.3f}".format(rounded)
    if number < 10000.0:
        return "{:.2f}".format(number)
    if number < 1e9:
        return "{:,.0f}".format(number)
    if number < 1e15:
        return to_readable_thousands(number, unit_type='long')

    return "{:.2e}".format(number).replace("+", "")

def to_readable_thousands(value, unit_type='short', decimals=1):
    if unit_type == "long":
        units = ['', ' thousand', ' million', ' billion', ' trillion', ' quadrillion', ' sextillion', ' septillion', ' octillion', ' nonillion']
    if unit_type == "short":
        units = ['', 'k', 'm', 'b', 't', 'p', 's']
    if unit_type == "hashrate":
        units = ['H/s', ' Kh/s', ' Mh/s', ' Gh/s', ' Th/s', ' Ph/s', ' Eh/s', ' Zh/s', ' Yh/s']
    if unit_type == "short_hashrate":
        units = ['H', ' Kh', ' Mh', ' Gh', ' Th', ' Ph', ' Eh', ' Zh', ' Yh']

    for unit in units:
        if value < 1000:
            return "{:.1f}{}".format(value, unit)
        value /= 1000

    fmt_str = "{:." + str(decimals) + "f}{}"
    return fmt_str.format(value*1000, units[-1])

def seconds_to_n_time_ago(seconds):
    if seconds < 60:
        return 'now'

    minutes = seconds / 60
    if minutes < 60:
        return "{:.0f}m ago".format(minutes)

    return "{:.0f}h ago".format(minutes / 60)

def seconds_to_time(seconds, granularity=2):
    result = []
    intervals = (
        ('centuries', 60*60*24*7*4.34524*12*10*10),
        ('decades',   60*60*24*7*4.34524*12*10),
        ('years',     60*60*24*7*4.34524*12),
        ('months',    60*60*24*7*4.34524),
        ('weeks',     60*60*24*7),
        ('days',      60*60*24),
        ('hours',     60*60),
        ('minutes',   60),
        ('seconds',   1),
    )

    if seconds == 0:
        return '0 seconds'

    for name, multiplier in intervals:
        value = seconds // multiplier
        if value > 0:
            seconds -= value * multiplier
            if value == 1:
                name = name.rstrip('s')
            result.append("{:.0f} {}".format(value, name))
    return ', '.join(result[:granularity])

    