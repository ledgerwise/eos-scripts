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

def getProducerEndpoint(endpoint):
    result = 'https' if endpoint['https'] else 'http'
    result = '{}://{}:{}/v1/producer/'.format(result, endpoint['host'], endpoint['port'])
    return result

def enable_endpoint(endpoint):
    try:
        response = requests.post('{}resume'.format(getProducerEndpoint(endpoint)))
    except:
        return False
    if response.json()['result'] == 'ok':
      return True
    else: 
      return False

def disable_endpoint(endpoint):
    try:
        response = requests.post('{}pause'.format(getProducerEndpoint(endpoint)))
    except:
        return False
    if response.json()['result'] == 'ok':
      return True
    else: 
      return False

def main():
    try:
        config = mpu.io.read(CONFIG_FILE)
    except Exception as e:
        logger.critical('Error opening file: {}'.format(e))
        quit()

    endpoints = config['endpoints']
    working_endpoints = []
    failing_endpoints = []

    for endpoint in endpoints:
        command = [CHECK_COMMAND,
                   '-H', endpoint['host'],
                   '-p', str(endpoint['port']),
                   '-c', 'head',
                   '-i', '6'
                   ]
        p_state, output = exec_command(command)
        if p_state == 0:
            logger.info('{}:{} ({} in {}) is working fine: {}'.format(endpoint['host'], endpoint['port'], endpoint['desc'], endpoint['network'], output))
            working_endpoints.append(endpoint)
        else:
            logger.critical('{}:{} ({} in {}) is not responding: {}'.format(endpoint['host'], endpoint['port'], endpoint['desc'], endpoint['network'], output))
            failing_endpoints.append(endpoint)

    if len(working_endpoints) == 0:
        logger.critical('No active enpoints found!!!!')
        quit()

    working_endpoints = sorted(
        working_endpoints, key=lambda k: k['weight'], reverse=True)
    for endpoint in working_endpoints:
        if enable_endpoint(endpoint):
            logger.info('Active endpoint: {} ({} in {}). weight: {}'.format(
                endpoint['host'], endpoint['desc'], endpoint['network'], endpoint['weight']))
            working_endpoints.remove(endpoint)
            break

    for endpoint in working_endpoints + failing_endpoints:
        if disable_endpoint(endpoint):
            logger.info('Disabled endpoint: {} ({} in {}). weight: {}'.format(
                endpoint['host'], endpoint['desc'], endpoint['network'], endpoint['weight']))
        else:
            logger.info('Error disabling endpoint: {} ({} in {}). weight: {}'.format(
                endpoint['host'], endpoint['desc'], endpoint['network'], endpoint['weight']))


if __name__ == "__main__":
    main()
