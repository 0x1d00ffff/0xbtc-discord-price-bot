# Wrappers to interact with etherscan data
import logging
import math
import os

import datetime
import time

import socket
try:
    from urllib.request import urlopen, Request
except:
    from urllib import urlopen, Request

from urllib.error import URLError

from bs4 import BeautifulSoup

from matplotlib import pyplot
import matplotlib
import numpy  # presumably numpy comes with matplotlib
import random

import configuration as config


saved_holders_chart_filename = os.path.join(config.DATA_FOLDER, 'holders_chart.png')
_known_addresses = {
    "0xc91795a59f20027848bc785678b53875934792a1" : "Mercatox",  # merc cold storage source https://digitexfutures.com/news/a-message-from-the-team-addressing-the-recent-activity-with-dgtx/
    "0x8d12a197cb00d4747a1fe03395095ce2a5cc6819" : "EtherDelta",
    "0xbf45f4280cfbe7c2d2515a7d984b8c71c15e82b7" : "Enclaves",
    "0x2a0c0dbecc7e4d658f48e01e3fa353f44050c208" : "IDEX",
    "0xe03c23519e18d64f144d2800e30e81b0065c48b5" : "Mercatox",
    "0x701564aa6e26816147d4fa211a0779f1b774bb9b" : "Uniswap",
}

def update_saved_holders_chart(token_name, token_address, total_supply):
    try:
        holders = _get_top_1000_token_holders(token_address)
    except (TimeoutError,
            ConnectionResetError,
            ConnectionRefusedError,
            socket.gaierror,
            socket.timeout,
            URLError):
        raise TimeoutError('Failed to get holders info')
    _generate_holders_chart(token_name, holders, total_supply, saved_holders_chart_filename)

def _generate_holders_chart(token_name, holders, total_supply, output_filename):
    supply_included = 0  # percentage of the pie chart as it fills up
    labels = []
    slices = []
    colors = []

    # TODO: should call chart_helpers.generate_pie_chart(values, labels, output_filename)
    # instead of doing the low-level matplotlib charting here. that would simplify
    # the code here and make it easier to eventually move it to the token library

    for holder in holders:
        rank, address, amount = holder

        if address in _known_addresses:
            address = "{} ({})".format(address, _known_addresses[address])

        supply_included += amount

        slices.append(amount)
        if amount/total_supply > 0.6/100:
            labels.append("{}: {} {:.02%}".format(rank, address, amount/total_supply))
        else:
            labels.append("")

    if supply_included < total_supply:
        supply_remaining = total_supply - supply_included
        labels.append("Other Addresses")
        #labels.append("At least {} other addresses".format(math.ceil(supply_remaining / slices[-1])))
        slices.append(supply_remaining)

    def are_colors_different(a, b, min_distance=0.2):
        return (abs(a - b) > min_distance
                and abs(a - b) < (1-min_distance))

    color_numbers = [random.random()]
    while len(color_numbers) < len(slices):
        color = random.random()

        # when generating the last color in the list, also compare it to the
        # first color
        if len(color_numbers) + 1 == len(slices):
            if not are_colors_different(color, color_numbers[0]):
                continue

        if are_colors_different(color, color_numbers[-1]):
            color_numbers.append(color)

    # Set3 is a color space with pastel-ish colors
    colors = pyplot.cm.Set3(color_numbers)

    fig, ax = pyplot.subplots(figsize=(18, 9), subplot_kw=dict(aspect="equal"))
    wedges, texts = ax.pie(slices, labels=labels,
                           labeldistance=1.05,
                           #autopct='%1.1f%%', pctdistance=0.7
                           shadow=False, startangle=90, colors=colors)

    for wedge in wedges:
        wedge.set_edgecolor('white')
        wedge.set_linewidth(0.04)
    
    fmt_str = "{} Distribution as of {}"
    ax.set_title(fmt_str.format(token_name, datetime.datetime.now(tz=datetime.timezone.utc).strftime("%c UTC")));

    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    pyplot.tight_layout()

    pyplot.savefig(fname=output_filename, dpi=None, quality=None, format='png',
                   facecolor='#a9a9a9', transparent=False)
    pyplot.close()

# get a single page of token holders from etherscan (50 per page)
def get_page_of_token_holders(address, etherscan_page, timeout=10.0):
    holders = []
    url_template = "https://etherscan.io/token/generic-tokenholders2?a={}&s=21000&p={}"
    req = Request(
        url_template.format(address, etherscan_page),
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    response = urlopen(req, timeout=timeout)
    page_contents = response.read()
    soup = BeautifulSoup(page_contents, 'html.parser')
    main_table = soup.find(id='maintable')
    rows = main_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) == 0:
            continue
        rank, address, amount, _ = cells
        rank = int(rank.string)
        address = address.find('a').string
        amount = float(amount.string.replace(',', ''))
        holders.append((rank, address, amount))

    return holders

def _get_top_1000_token_holders(address, timeout=10.0):
    holders = []
    for page_num in range(20):
        page_num = page_num+1  # page is one-indexed
        holders += get_page_of_token_holders(address, page_num, timeout=timeout)
    return holders

def main():
    logging.basicConfig(level=logging.INFO)

    #import test_data
    #_generate_holders_chart('0xBitcoin', test_data.top_1000_holders, 3307650, './holders_chart.png')
    #return

    holders = _get_top_1000_token_holders("0xB6eD7644C69416d67B522e20bC294A9a9B405B31")
    logging.info('first holder: {}'.format(holders[0]))
    logging.info('1000th holder: {}'.format(holders[999]))


if __name__ == "__main__":
    main()
