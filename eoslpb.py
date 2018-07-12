#!/usr/bin/env python
import requests
import time
import mpu.io
import optparse
from tendo import singleton

def get_info(endpoint):
    return requests.get('{}/v1/chain/get_info'.format(endpoint)).json()

def main():
    me = singleton.SingleInstance()

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
            info = get_info(endpoint)
            if not info['head_block_producer'] in eoslbp:
                eoslbp[info['head_block_producer']] = {}
            eoslbp[info['head_block_producer']]['last_block_produced_time'] = info['head_block_time']
            print(info)

            mpu.io.write(json_file, eoslbp)
            time.sleep(1)

if __name__ == "__main__":
    main()