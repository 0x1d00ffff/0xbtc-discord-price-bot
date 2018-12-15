# Ping a server (or list of servers) and return the latency to each
#
# WARNING: do not name this file ping.py, it will not work
#

import re
import multiprocessing

import subprocess
import platform

# a number too high may affect ping times
_MAX_THREADS = 5

def ping(ip, count=1):
    """Ping a specified ip, return text output.

    Raises Exception if no response."""
    if platform.system().lower()=="windows":
        ping_params = "-n {} -w 2000".format(count)
    else:
        ping_params = "-c {} -W 2".format(count)

    cmd = "ping {} {}".format(ping_params, ip)
    try:
        complete_proc = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        raise Exception("bad response from ping: server probably down")

    return complete_proc.stdout.decode("utf-8")

def get_ping_time(ip, count=4):
    try:
        output = ping(ip, count=count)
    except:
        return None

    values = []
    lines = re.split('\n', output)
    for l in lines:
        l = l.strip()
        if l == "":
            continue
        # should match both unix/win ping: "time=1.0ms", "time=1.0 ms", "time<1ms"
        match = re.search("time=?([<\d.]+) ?ms", l)
        if match:
            values.append(match.group(1))
        else:
            continue

    if len(values) != count:
        #raise Exception("bad response from ping: wrong number of matches: {}".format(repr(lines)))
        return None

    total = 0.0
    for val in values:
        # Windows shows all values lower than 1ms as "<1ms"
        if val == "<1":
            val = 0.5
        total += float(val)
    return total / count

def ping_list(ip_list, count=4):
    """Check latencies using threads"""
    try:
        ping_list.pool
    except AttributeError:
        ping_list.pool = multiprocessing.Pool(_MAX_THREADS)

    raw_results = ping_list.pool.map_async(get_ping_time, ip_list, count).get(999)
    return list(zip(ip_list, raw_results))

if __name__ == "__main__":

    ping('8.8.8.8')

    print("ping_list(['10.0.0.1','8.8.8.8']) = {}".format(ping_list(['10.0.0.1','8.8.8.8'])))

    ping_times = ping_list(['api.infura.io', 'etherscan.io'])
    print(ping_times)

