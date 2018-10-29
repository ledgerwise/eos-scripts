#!/usr/bin/env python3

import argparse
import requests
import os
import sys
import mpu
import subprocess
import logging
import colorlog
import inspect

SCRIPT_PATH = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))

parser = argparse.ArgumentParser(description='Handle BP failover')
parser.add_argument("-v", '--verbose', action="store_true",
                    dest="verbose", help='Print logged info to screen')
parser.add_argument("-d", '--debug', action="store_true",
                    dest="debug", help='Print debug info')
parser.add_argument('-l', '--log_file', default='{}/{}.log'.format(SCRIPT_PATH,
                                                                   os.path.basename(__file__).split('.')[0]), help='Log file')
parser.add_argument('-c', '--config_file', default='{}/{}'.format(SCRIPT_PATH, 'failover_config.json'),
                    help='json file with the check configuration. Defaults to failover_config.json')
parser.add_argument('-b', '--check_command', default='{}/{}'.format(SCRIPT_PATH, 'check_eos_bp.py'),
                    help='path of check_eos_bp.py command. Defaults to .')

args = parser.parse_args()
VERBOSE = args.verbose
DEBUG = args.debug
LOG_FILE = args.log_file
CONFIG_FILE = args.config_file
CHECK_COMMAND = args.check_command

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s%(reset)s')
if DEBUG:
    logger.setLevel(logging.DEBUG)
if VERBOSE:
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

fh = logging.FileHandler(LOG_FILE)
logger.addHandler(fh)
fh.setFormatter(formatter)


def exec_command(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    return (p_status, output)


def enable_endpoint(endpoint):
    return True


def disable_endpoint(endpoint):
    return True


def main():
    try:
        config = mpu.io.read(CONFIG_FILE)
    except Exception as e:
        print('Error opening file: {}'.format(e))
        quit()

    endpoints = config['endpoints']
    working_endpoints = []
    failing_endpoints = []

    for endpoint in endpoints:
        command = [CHECK_COMMAND,
                   '-H', endpoint['host'],
                   '-p', str(endpoint['port']),
                   '-c', 'http'
                   ]
        p_state, output = exec_command(command)
        if p_state == 0:
            working_endpoints.append(endpoint)
        else:
            failing_endpoints.append(endpoint)

    if len(working_endpoints) == 0:
        print('No active enpoints found!!!!')
        quit()

    working_endpoints = sorted(
        working_endpoints, key=lambda k: k['weight'], reverse=True)
    for endpoint in working_endpoints:
        if enable_endpoint(endpoint):
            print('Active endpoint: {}. weight: {}'.format(
                endpoint['url'], endpoint['weight']))
            working_endpoints.remove(endpoint)
            break

    for endpoint in working_endpoints + failing_endpoints:
        if disable_endpoint(endpoint):
            print('Disabled endpoint: {}. weight: {}'.format(
                endpoint['url'], endpoint['weight']))
        else:
            print('Error disabling endpoint: {}. weight: {}'.format(
                endpoint['url'], endpoint['weight']))


if __name__ == "__main__":
    main()
