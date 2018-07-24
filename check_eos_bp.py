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
import datetime
import mpu.io

SERVICE_STATUS = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3
}

def get_lbp(lbp_file):
    try:
        result = mpu.io.read(lbp_file)
    except Exception as e:
        print('ERROR: {}'.format(str(e)))
        sys.exit(SERVICE_STATUS['CRITICAL'])

    return result

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
    parser.add_argument('-p', '--port', type=int, default=8888,
                       help='Port number. default = 8888')
    parser.add_argument('-s', '--ssl', action='store_true', default=False, help = 'Use ssl to connect to the api endpoint')
    parser.add_argument('-t', '--timeout', type=int, default=3, help = 'Timeout in seconds')
    parser.add_argument('-cf', '--config-file', default='peers.ini',
                       help='Config file to get the RPC endpoints (One host:port per line)')
    parser.add_argument('-n', '--num-blocks-threshold', default=120,
                       help='Threshold to consider that head is forked or not working')
    parser.add_argument('-c', '--check', help='Check to perform [http,p2p,nodeos,lbp]')
    parser.add_argument('-lbp', '--lbp_file', default='eos.lbp.json',
                        help='json file with the lbp info. Produced by eoslpb.py')
    parser.add_argument('-bpa', '--bp_account',
                        help='BP accounts to check last block produced')
    
    args = parser.parse_args()
    HOST = args.host
    TIMEOUT = args.timeout
    PORT = args.port
    CONFIG_FILE = args.config_file
    NUM_BLOCKS_THRESHOLD = args.num_blocks_threshold
    CHECK = args.check
    VERBOSE = args.verbose
    LBP_FILE = args.lbp_file
    BPA = args.bp_account
    SSL = args.ssl

    performance_data = ''
    
    if CHECK == 'http':
        try:
            response = requests.get('{}://{}:{}/v1/chain/get_info'.format('http' if not SSL else 'https', HOST, PORT), timeout=TIMEOUT)
            if response.status_code != 200:
                print('HTTP CRITICAL: The server couldn\'t fulfill the request. Error code: {}'.format(response.status_code))
                sys.exit(SERVICE_STATUS['CRITICAL'])
            j_response = response.json()
        except requests.exceptions.HTTPError as e:
            print('HTTP CRITICAL: The server couldn\'t fulfill the request. Error code: {}'.format(e.response.status_code))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        except requests.exceptions.Timeout:
            print('HTTP CRITICAL: Failed to reach server. Reason: Timeout')
            sys.exit(SERVICE_STATUS['CRITICAL'])
        except requests.exceptions.RequestException as e:
            print('HTTP CRITICAL: Failed to reach server. Reason: {}'.format(e))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        except Exception as e:
            print('HTTP CRITICAL: Failed to reach server. Reason: Unknown')
            if VERBOSE:
                print(e)
            sys.exit(SERVICE_STATUS['CRITICAL'])

        print('BP API OK {}'.format(performance_data))
        sys.exit(SERVICE_STATUS['OK'])

    elif CHECK == 'p2p':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        result = sock.connect_ex((HOST, PORT))
        if result != 0:
            print('P2P CRITICAL')
            sys.exit(SERVICE_STATUS['CRITICAL'])
        print('BP P2P OK {}'.format(performance_data))
        sys.exit(SERVICE_STATUS['OK'])

    elif CHECK == 'nodeos':
        process_found = False
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
            except:
                continue
            if p.name() == "nodeos":
                process_found = True
        if not process_found:
            print('nodeos CRITICAL: Process not running')
            sys.exit(SERVICE_STATUS['CRITICAL'])

        print('BP nodeos running OK {}'.format(performance_data))
        sys.exit(SERVICE_STATUS['OK'])

    elif CHECK == 'lbp':
        lbp = get_lbp(LBP_FILE)

        if not BPA in lbp['producers']:
            print('{} is not in top 21'.format(BPA))
            sys.exit(SERVICE_STATUS['OK'])
        else:
            if not BPA:
                print('LBP CRITICAL: No BP account specified')
                sys.exit(SERVICE_STATUS['CRITICAL'])

            last_block_produced_time = lbp[BPA]['last_block_produced_time']
            last_block_produced_time_dt = datetime.datetime.strptime(last_block_produced_time, "%Y-%m-%dT%H:%M:%S.%f")
            now = datetime.datetime.utcnow()
            secs_diff = int((now - last_block_produced_time_dt).total_seconds())
            if secs_diff > 126:
                print('LBP CRITICAL: {} last produced {} seconds ago. '.format(BPA, secs_diff))
                sys.exit(SERVICE_STATUS['CRITICAL'])
            print('{} produced {} secs ago'.format(BPA, secs_diff))
            sys.exit(SERVICE_STATUS['OK'])

if __name__ == "__main__":
    main(sys.argv)
