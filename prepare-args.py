#!/usr/bin/env python3

import argparse
import csv
import time
from datetime import date
from pathlib import Path
from typing import Any, List, Union
import dominate
from dominate.tags import *

import requests

EMOON_ADDRESS = "erd1w9mmxz6533m7cf08gehs8phkun2x4e8689ecfk3makk3dgzsgurszhsxk4"
DEAD_RARE_ADDRESS = "erd1qqqqqqqqqqqqqpgqd9rvv2n378e27jcts8vfwynpx0gfl5ufz6hqhfy0u0"
TRUST_WALLET_ADDRESS = "erd1qqqqqqqqqqqqqpgq6wegs2xkypfpync8mn2sa5cmpqjlvrhwz5nqgepyg8"
FRAMEIT_WALLET_ADDRESS = "erd1qqqqqqqqqqqqqpgq705fxpfrjne0tl3ece0rrspykq88mynn4kxs2cg43s"
ELROND_NFT_SWAP_WALLET_ADDRESS = "erd1qqqqqqqqqqqqqpgq8xwzu82v8ex3h4ayl5lsvxqxnhecpwyvwe0sf2qj4e"
ISENGARD_WALLET_ADDRESS="erd1qqqqqqqqqqqqqpgqy63d2wjymqergsxugu9p8tayp970gy6zlwfq8n6ruf"


class AddressESDT:
    def __init__(self, address, esdtsum):
        self.address = address
        self.esdtsum = esdtsum

    def __str__(self):
        return self.address + "-" + str(self.esdtsum)


def get_addresses_for_distro(args: Any) -> str:
    '''
    Gets addresses to send tokens to.
    :param args: Contains a collection identifier, owner address and smart-contract address
    :return: A string with empty spaces to form an array in sh script
    '''

    p = Path('output')
    p.mkdir(parents=True, exist_ok=True)

    nft_collection_name = args["collection"]
    sc_address = args["sc_address"]
    token = args["token"]
    proxy_prefix = args["proxy_prefix"]

    ## reproduce the response from the old elrond api point
    all_collection_with_owner = []
    i = 0
    while i < 10000:
        nfts = requests.get(f'https://{proxy_prefix}api.elrond.com/collections/{nft_collection_name}/nfts?from='+str(i)+'&size=100&withOwner=true').json()
        for nft in nfts:
            all_collection_with_owner.append(nft["owner"])
        i = i + 100
        time.sleep(0.1)

    unique_holders = []
    values = []
    for holder in all_collection_with_owner:
        if holder not in unique_holders:
            unique_holders.append(holder)
            balance = all_collection_with_owner.count(holder)
            value = {"address": holder, "balance": balance}
            values.append(value)

    # creating a black listed array so that these addresses won't get the token
    black_listed_addresses = [EMOON_ADDRESS,
                              DEAD_RARE_ADDRESS,
                              TRUST_WALLET_ADDRESS,
                              FRAMEIT_WALLET_ADDRESS,
                              ELROND_NFT_SWAP_WALLET_ADDRESS,
                              ISENGARD_WALLET_ADDRESS,
                              args["owner_address"]]
    if sc_address != "null":
        black_listed_addresses.append(sc_address)

    today = date.today()
    html_file = today.strftime("%b-%d-%Y.html")
    txt_file = today.strftime("%b-%d-%Y.txt")
    func_html = open("output/unique-{}".format(html_file), "w")
    func_txt = open("output/total-{}".format(txt_file), "w")

    addresses_return_to_sh = ""
    unique_addresses_list = []
    unique_addresses_list_esdt = []
    count = 0
    for value in values:
        address = value["address"]
        if address not in black_listed_addresses:
            addresses_return_to_sh += address + " "
            count = count + 1
            # txt writing
            func_txt.write(address + "\n")

            # unique addresses for html
            if address not in unique_addresses_list:
                unique_addresses_list.append(address)

    # forming HTML file
    doc = dominate.document(title='%s distribution for %s' % (token, nft_collection_name))
    # TODO: add ability to add your website stuff below
    # with doc.head:
    # link(rel='stylesheet', href='/style.css')
    # script(type='text/javascript', src='/script.js')
    # TODO: add your website stuff and important links here
    # with doc:
    # with div(id='header').add(ol()):
    # for i in ['link-1', 'link-2', 'link-3']:
    # li(a(i.title(), href='/%s.html' % i))
    token_total = int(args["token_total"])
    token_per_address = int(token_total / count)
    token_dec = int(args["token_decimals"])
    per_wallet = int(token_per_address * (10 ** token_dec))

    # new optimized writing

    for value in values:
        address = value["address"]
        if address not in black_listed_addresses:
            found = next((x for x in unique_addresses_list_esdt if x.address == address), None)
            if found is None:
                unique_addresses_list_esdt.append(AddressESDT(address, per_wallet))
            else:
                found.esdtsum = found.esdtsum + per_wallet

    with open(f"output/{nft_collection_name}-esdt-per-address.csv", "wt") as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerow(
            ["Wallet address", "ESDT value per address", "Random value for bash correctness"])  # write header
        for output in unique_addresses_list_esdt:
            # adding random value as a last one, because of bash reading issues.
            writer.writerow([output.address, hex(int(output.esdtsum)), "random"])

    with doc:
        h1('%s distribution for %s' % (token, nft_collection_name))
        h4('Total addresses: %s' % count)
        h4('Unique addresses: %s' % len(unique_addresses_list))
        h4('Token value per address: %s' % token_per_address)
        h2('Addresses:')
        ul()
        for unique_address in unique_addresses_list:
            explorer_url = f"https://{proxy_prefix}explorer.elrond.com/accounts/{unique_address}"
            li(a(unique_address, href=explorer_url))
    func_html.write(str(doc))
    func_html.close()
    func_txt.write("Total count is " + str(count) + "\n")
    func_txt.close()

    # calculating token amount to distribute to each wallet address
    token = hex_encode_string(token)
    quantity_in_hex = hex(per_wallet)
    # attaching to returned string as first argument
    addresses_return_to_sh = quantity_in_hex + " " + token + " " + addresses_return_to_sh
    print(addresses_return_to_sh)
    return addresses_return_to_sh


def pad_even(arg: str) -> str:
    '''
    Pads the argument with a zero, if needed, so that the number of hex-digits is even.

>>> pad_even('4d2b3')
'04d2b3'
>>> pad_even('c0ffee')
'c0ffee'
    '''
    new_length = len(arg) + len(arg) % 2
    return arg.rjust(new_length, '0')


def hex_encode_int(arg: int) -> str:
    '''
    Hex-encodes an int.

>>> hex_encode_int(1234)
'04d2'
    '''
    return pad_even(f'{arg:x}')


def hex_encode_string(arg: str) -> str:
    '''
    Hex-encodes a string.

>>> hex_encode_string('\\ntest')
'0a74657374'
    '''
    return ''.join(f'{ord(c):02x}' for c in arg)


def join_arguments(args: List[str]) -> str:
    return '@'.join(args)


def hex_encode(arg: Union[str, int]) -> str:
    '''
    Hex-encodes an argument or a list of arguments.

>>> hex_encode('\\ntest')
'0a74657374'
>>> hex_encode(1234)
'04d2'
>>> hex_encode([1234, 'test'])
'04d2@74657374'
>>> hex_encode([10, 11, [12, 13]])
'0a@0b@0c@0d'
    '''
    if isinstance(arg, int):
        return hex_encode_int(arg)
    elif isinstance(arg, str):
        return hex_encode_string(arg)
    else:
        raise Exception(f'Invalid argument: {arg}')


def prepare_args(args: Any) -> str:
    return get_addresses_for_distro(args)


parser = argparse.ArgumentParser(description='Prepare the data field for a given command from a JSON.')
parser.add_argument('command', help='Command to prepare', nargs='?',
                    choices=('get-addresses', 'hex_encode', 'get_duration_of_holding'))
parser.add_argument('collection', type=str, help='NFT collection name')
parser.add_argument('sc_address', type=str, help='Smart contract wallet address', default=None)
parser.add_argument('owner_address', type=str, help='Owner wallet address')
parser.add_argument("token", type=str, help="Token identifier")
parser.add_argument("token_nonce", type=str, help="Token nonce identifier")
parser.add_argument("token_decimals", type=str, help="Token decimals")
parser.add_argument('token_total', type=str, help='Total token value in decimal, natural numbers only')
parser.add_argument('proxy_prefix', type=str, help='Proxy prefix for urls')
cli_args = parser.parse_args()
tx_args = {"collection": cli_args.collection,
           "sc_address": cli_args.sc_address,
           "owner_address": cli_args.owner_address,
           "token": cli_args.token,
           "token_nonce": cli_args.token_nonce,
           "token_decimals": cli_args.token_decimals,
           "token_total": cli_args.token_total,
           "proxy_prefix": cli_args.proxy_prefix.replace("&", "")}
tx_data = prepare_args(tx_args)
