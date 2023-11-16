#!/usr/bin/python3

import sys
import argparse
import requests

SERVICE_STATUS = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3
}

def get_health(HOST, PORT, SSL, TIMEOUT, VERBOSE):
    try:
        response = requests.get('{}://{}:{}/health'.format('http' if not SSL else 'https', HOST, PORT), timeout=TIMEOUT)
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
    parser.add_argument('-p', '--port', type=int, default=80,
                       help='Port number. default = 9000')
    parser.add_argument('-s', '--ssl', action='store_true', default=False, help = 'Use ssl to connect to the api endpoint')
    parser.add_argument('-t', '--timeout', type=int, default=3, help = 'Timeout in seconds')
    parser.add_argument('-w', '--warning', type=int, default='10',
                        help='warning threshold of head block - last indexed block. default 10')
    parser.add_argument('-c', '--critical', type=int, default='100',
                        help='critical threshold of head block - last indexed block. default 100')
    
    args = parser.parse_args()
    HOST = args.host
    TIMEOUT = args.timeout
    PORT = args.port
    SSL = args.ssl
    VERBOSE = args.verbose
    W_THRESHOLD = args.critical
    C_THRESHOLD = args.warning

    output_message = ''
    output_status = SERVICE_STATUS['OK']
    response, http_query_time = get_health(HOST, PORT, SSL, TIMEOUT, VERBOSE)
    
    #services = response['health']
    #elastic_service = list(filter(lambda service: service['service'] == 'Elasticsearch', services))[0]
    #nodeos_service = list(filter(lambda service: service['service'] == 'NodeosRPC', services))[0]
    head_block = response['data']['chain']['head_block']
    last_indexed_block = int(response['data']['postgres']['readers'][0]['block_num'])
    
    #Check last indexed block vs head_block
    index_gap = abs(head_block - last_indexed_block)
    if index_gap > W_THRESHOLD:
        output_message += "{} blocks gap between head and last indexed block. ".format(index_gap)
        output_status = SERVICE_STATUS['WARNING']
        if index_gap > C_THRESHOLD:
            output_status = SERVICE_STATUS['CRITICAL']

    #Check services status
    services = [response['data']['postgres'], response['data']['redis'], response['data']['chain']]
    if not all(map(lambda x: x['status'] == 'OK', services)):
        services_not_ok = ([y['service'] for y in (filter(lambda x: x['status'] != 'OK', services))])
        output_message += "Services not OK: {}. ".format(services_not_ok)
        output_status = SERVICE_STATUS['CRITICAL']

    if not output_message: 
        output_message = 'Everything Ok'
    print('{} | http_query_time={}s'.format(output_message.rstrip(), http_query_time))
    sys.exit(output_status)

if __name__ == "__main__":
    main(sys.argv)
