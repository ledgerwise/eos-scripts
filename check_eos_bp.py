#!/usr/bin/python3

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
import time

SERVICE_STATUS = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3
}

def get_lpb(lpb_file):
    try:
        result = mpu.io.read(lpb_file)
    except Exception as e:
        print('ERROR: {}'.format(str(e)))
        sys.exit(SERVICE_STATUS['CRITICAL'])

    return result

def get_info(host_port, results = None, i = None):
    try:
        result = requests.get('http://{}/v1/chain/get_info'.format(host_port), verify=False, timeout=0.5).json()
    except:
        result = {'head_block_num': 0}

    if results != None:
        results[i] = result

    return result

def check_api(HOST, PORT, SSL, TIMEOUT, VERBOSE):
    try:
        response = requests.get('{}://{}:{}/v1/chain/get_info'.format('http' if not SSL else 'https', HOST, PORT), timeout=TIMEOUT)
        if response.status_code != 200:
            print('HTTP CRITICAL: The server couldn\'t fulfill the request. Error code: {}'.format(response.status_code))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        j_response = response.json()
    except requests.exceptions.HTTPError as e:
        print('HTTP CRITICAL: The server couldn\'t fulfill the request. Error code: {}'.format(e.response.status_code))
        sys.exit(SERVICE_STATUS['CRITICAL'])
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        print('HTTP CRITICAL: Failed to reach server. Reason: Timeout or Connection Error')
        sys.exit(SERVICE_STATUS['CRITICAL'])
    except requests.exceptions.RequestException as e:
        print('HTTP CRITICAL: Failed to reach server. Reason: {}'.format(e))
        sys.exit(SERVICE_STATUS['CRITICAL'])
    except Exception as e:
        print('HTTP CRITICAL: Failed to reach server. Reason: Unknown')
        if VERBOSE:
            print(e)
        sys.exit(SERVICE_STATUS['CRITICAL'])
    performance_data = response.elapsed.total_seconds()
    return j_response, performance_data

def main(argv):
    parser = argparse.ArgumentParser(description='Check BP status')
    parser.add_argument('-v', '--verbose', action='store_true', help = 'Print verbose logging to stdout')
    parser.add_argument('-H', '--host', default='localhost',
                       help='IP or hostname to check. default = localhost')
    parser.add_argument('-p', '--port', type=int, default=8888,
                       help='Port number. default = 8888')
    parser.add_argument('-s', '--ssl', action='store_true', default=False, help = 'Use ssl to connect to the api endpoint')
    parser.add_argument('-t', '--timeout', type=int, default=3, help = 'Timeout in seconds')
    parser.add_argument('-i', '--head_interval', type=int, default=10, help = 'Time in seconds to check head')
    parser.add_argument('-c', '--check', help='Check to perform [http,head,p2p,nodeos,lpb]')
    parser.add_argument('-lpb', '--lpb_file', default='eos.lpb.json',
                        help='json file with the lpb info. Produced by eoslpb.py')
    parser.add_argument('-bpa', '--bp_account',
                        help='BP accounts to check last block produced')
    
    args = parser.parse_args()
    HOST = args.host
    TIMEOUT = args.timeout
    HEAD_INTERVAL = args.head_interval
    PORT = args.port
    CHECK = args.check
    VERBOSE = args.verbose
    LPB_FILE = args.lpb_file
    BPA = args.bp_account
    SSL = args.ssl

    performance_data = ''
    
    if CHECK == 'http':   
        j_response, performance_data = check_api(HOST, PORT, SSL, TIMEOUT, VERBOSE)
        print('BP API OK | time={}s'.format(performance_data))
        sys.exit(SERVICE_STATUS['OK'])
    
    if CHECK == 'head':
        j_response, performance_data = check_api(HOST, PORT, SSL, TIMEOUT, VERBOSE)
        head_block_num = int(j_response['head_block_num'])
        last_irreversible_block_num = int(j_response['last_irreversible_block_num'])
        
        time.sleep(HEAD_INTERVAL)

        j_response2, performance_data2 = check_api(HOST, PORT, SSL, TIMEOUT, VERBOSE)
        head_block_num2 = int(j_response2['head_block_num'])
        last_irreversible_block_num2 = int(j_response2['last_irreversible_block_num'])

        is_hb_advancing = head_block_num2 > head_block_num
        is_lib_advancing = last_irreversible_block_num2 > last_irreversible_block_num
        
        if is_hb_advancing and is_lib_advancing:
            head_block_time = j_response2['head_block_time']
            head_block_time_dt = datetime.datetime.strptime(head_block_time, "%Y-%m-%dT%H:%M:%S.%f")

            now = datetime.datetime.utcnow()
            secs_diff = int((now - head_block_time_dt).total_seconds())
            if secs_diff > 30:
                print('BP seems to be syncing. Last block: {}. Last block time: {}'.format(head_block_num, head_block_time))
                sys.exit(SERVICE_STATUS['WARNING'])

            print('BP HEAD OK - LB: {}, LIB {} | time={}s'.format(head_block_num2, last_irreversible_block_num2, performance_data))
            sys.exit(SERVICE_STATUS['OK'])
        elif not is_hb_advancing:
            print('BP HEAD BLOCK not advancing. Last block {}'.format(head_block_num2))
            sys.exit(SERVICE_STATUS['CRITICAL'])
        elif not is_lib_advancing:
            print('BP LIB not advancing. Last block {}'.format(last_irreversible_block_num2))
            sys.exit(SERVICE_STATUS['CRITICAL'])

    elif CHECK == 'p2p':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        result = sock.connect_ex((HOST, PORT))
        if result != 0:
            print('P2P CRITICAL')
            sys.exit(SERVICE_STATUS['CRITICAL'])
        performance_data = time.time() - start
        print('BP P2P OK | time={}s'.format(performance_data))
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
        print('BP nodeos running OK')
        sys.exit(SERVICE_STATUS['OK'])

    elif CHECK == 'lpb':
        lpb = get_lpb(LPB_FILE)

        if not BPA in lpb['producers']:
            print('{} is not in top 21'.format(BPA))
            sys.exit(SERVICE_STATUS['OK'])
        else:
            if not BPA:
                print('LPB CRITICAL: No BP account specified')
                sys.exit(SERVICE_STATUS['CRITICAL'])

            last_block_produced_time = lpb[BPA]['last_block_produced_time']
            last_block_produced_time_dt = datetime.datetime.strptime(last_block_produced_time, "%Y-%m-%dT%H:%M:%S.%f")
            now = datetime.datetime.utcnow()
            secs_diff = int((now - last_block_produced_time_dt).total_seconds())
            if secs_diff > 150:
                print('LPB CRITICAL: {} last produced {} seconds ago. '.format(BPA, secs_diff))
                sys.exit(SERVICE_STATUS['CRITICAL'])
            print('{} produced {} secs ago'.format(BPA, secs_diff))
            sys.exit(SERVICE_STATUS['OK'])
    else:
        print('Unknown check')
        parser.print_help()
        sys.exit(SERVICE_STATUS['WARNING'])
if __name__ == "__main__":
    main(sys.argv)
