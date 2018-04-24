#!/usr/bin/env python3

import sys
import argparse
import urllib.request
from urllib.error import URLError, HTTPError
import socket
import psutil
import re
import requests
import threading

SERVICE_STATUS = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3
}

def get_peers(config_file):
    try:
        with open(config_file) as f:
            peers = f.readlines()
    except Exception as e:
        print('ERROR: {}'.format(str(e)))
        sys.exit(SERVICE_STATUS['CRITICAL'])

    return [peer.strip() for peer in peers]

def get_heads(peers):
    threads = [None] * len(peers)
    results = [None] * len(peers)

    for i, peer in enumerate(peers):
        threads[i] = threading.Thread(target=get_info, args=(peer, results, i))
        threads[i].start()

    for i in range(len(peers)):
        threads[i].join()

    return [result['head_block_num'] for result in results]

def get_info(host_port, results = None, i = None):
    try:
        result = requests.get('http://{}/v1/chain/get_info'.format(host_port), verify=False, timeout=0.5).json()
    except:
        result = {'head_block_num': 0}

    if results != None:
        results[i] = result

    return result
    

def main(argv):
    parser = argparse.ArgumentParser(description='Check BP status')
    parser.add_argument('-v', '--verbose', action='store_true', help = 'Print verbose logging to stdout')
    parser.add_argument('-H', '--host', default='localhost',
                       help='IP or hostname to check. default = localhost')
    parser.add_argument('-p', '--http_port', type=int, default=8888,
                       help='HTTP port number. default = 8888')
    parser.add_argument('-p2', '--p2p_port', type=int, default=9876,
                       help='P2P port number. default = 9876')
    parser.add_argument('-cf', '--config-file', default='peers.ini',
                       help='Config file to get the RPC endpoints (One host:port per line)')
    parser.add_argument('-n', '--num-blocks-threshold', default=120,
                       help='Threshold to consider that head is forked or not working')
    parser.add_argument('-c', '--check_list', help='Comma separated list of checks to perform. Choices: [http,p2p,nodeos,head]. If not set it performs all the checks sequentially')
    args = parser.parse_args()
    HOST = args.host
    HTTP_PORT = args.http_port
    P2P_PORT = args.p2p_port
    CONFIG_FILE = args.config_file
    NUM_BLOCKS_THRESHOLD = args.num_blocks_threshold
    CHECK_LIST = args.check_list.split(',') if args.check_list else None
    VERBOSE = args.verbose

    if not CHECK_LIST or 'http' in CHECK_LIST:
        try:
            response = urllib.request.urlopen('http://{}:{}/v1/chain/get_info'.format(HOST, HTTP_PORT))
            j_response = response.read()
            if VERBOSE:
                print('HTTP response is OK')
        except HTTPError as e:
            print('HTTP CRITICAL: The server couldn\'t fulfill the request. Error code: {}'.format(e.code))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        except URLError as e:
            print('HTTP CRITICAL: Failed to reach server. Reason: {}'.format(e.reason))
            sys.exit(SERVICE_STATUS['CRITICAL'])

    if not CHECK_LIST or 'p2p' in CHECK_LIST:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((HOST, P2P_PORT))
        if result != 0:
            print('P2P CRITICAL: P2P service DOWN')
            sys.exit(SERVICE_STATUS['CRITICAL'])
        if VERBOSE:
                print('P2P response is OK')

    if not CHECK_LIST or 'nodeos' in CHECK_LIST:
        process_found = False
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
            except:
                cotinue
            if p.name() == "nodeos":
                process_found = True
        if not process_found:
            print('nodeos CRITICAL: Process not running')
            sys.exit(SERVICE_STATUS['CRITICAL'])
        elif VERBOSE:
                print('nodeos process is running')

    if not CHECK_LIST or 'head' in CHECK_LIST:
        peers = get_peers(CONFIG_FILE)
        if len(peers) == 0:
            print('HEAD ERROR: No peers found')
            sys.exit(SERVICE_STATUS['CRITICAL'])

        heads = get_heads(peers)
        node_head = get_info('{}:{}'.format(HOST, HTTP_PORT))['head_block_num']
        head_diff = abs(node_head- max(heads))

        if head_diff > NUM_BLOCKS_THRESHOLD:
            print('head block CRITICAL: {} blocks difference. There might be a fork'.format(head_diff))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        if VERBOSE:
                print('head block OK: {} blocks of difference'.format(head_diff))

    print('BP Services OK')
    sys.exit(SERVICE_STATUS['OK'])

if __name__ == "__main__":
    main(sys.argv)