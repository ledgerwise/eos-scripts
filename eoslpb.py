#!/usr/bin/env python
import requests
import time
import mpu.io
import optparse
import json
from tendo import singleton

def get_info(endpoint):
    return requests.get('{}/v1/chain/get_info'.format(endpoint)).json()

def make_request(endpoint, function, data):
    return requests.post('{}/v1/chain/{}'.format(endpoint, function), timeout=2.0, data=json.dumps(data)).json()['rows']

def get_producers(endpoint, limit = 1000):
    return requests.get('{}/v1/chain/get_producer_schedule'.format(endpoint)).json()['active']['producers']

def main():
    #me = singleton.SingleInstance()

    parser = optparse.OptionParser()
    parser.add_option("-e", '--endpoint-list', dest="endpoints", default="https://nodes.get-scatter.com",
                    help="Coma separated list of API nodes. Defaults to https://nodes.get-scatter.com")
    parser.add_option("-n", '--network', dest="network", default="eos",
                    help="Network name. Defaults to eos")
    options, args = parser.parse_args()

    endpoints = options.endpoints.split(',')
    network = options.network

    json_file = '{}.lbp.json'.format(network)
    try:
        eoslbp = mpu.io.read(json_file)
    except:
        eoslbp = {
        }
        mpu.io.write(json_file, eoslbp)

    while True:
        for endpoint in endpoints: 
            try:
                info = get_info(endpoint)
            except:
                print('Error getting info from endpoint {}'.format(endpoint))
                continue
            try:    
                if not info['head_block_producer'] in eoslbp:
                    eoslbp[info['head_block_producer']] = {}
                eoslbp[info['head_block_producer']]['last_block_produced_time'] = info['head_block_time']
            except:
                print('Error getting head_block_producer from endpoint {}'.format(endpoint))
                continue

            try:
                producers = get_producers(endpoint)
            except:
                print('Error getting producers from endpoint {}'.format(endpoint))
                continue
            eoslbp['producers'] = [ p['producer_name'] for p in producers ]
            mpu.io.write(json_file, eoslbp)
            break
        time.sleep(1)

if __name__ == "__main__":
    main()
