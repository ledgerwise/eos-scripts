![EOSMetal](./logo-text-grey.jpg "EOSMetal")

[https://eosmetal.io](https://eosmetal.io)

# eos-scripts
Collection of EOS Scripts

## check\_eos\_bp.py
BP Health check plugin. It follows the [Nagios plugin guidelines](https://nagios-plugins.org/doc/guidelines.html) so it can be used with [Nagios](https://www.nagios.org/
) or any other compatible monitoring software like [Icinga](https://www.icinga.com/
) or [Consul](https://www.consul.io
).

### Dependencies
* Python3

### Usage

```bash
./check_eos_bp.py --help
usage: check_eos_bp.py [-h] [-v] [-H HOST] [-p HTTP_PORT] [-p2 P2P_PORT]
                       [-cf CONFIG_FILE] [-n NUM_BLOCKS_THRESHOLD]
                       [-c CHECK_LIST]

Check BP status

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Print verbose logging to stdout
  -H HOST, --host HOST  IP or hostname to check. default = localhost
  -p HTTP_PORT, --http_port HTTP_PORT
                        HTTP port number. default = 8888
  -p2 P2P_PORT, --p2p_port P2P_PORT
                        P2P port number. default = 9876
  -cf CONFIG_FILE, --config-file CONFIG_FILE
                        Config file to get the RPC endpoints (One host:port
                        per line)
  -n NUM_BLOCKS_THRESHOLD, --num-blocks-threshold NUM_BLOCKS_THRESHOLD
                        Threshold to consider that head is forked or not
                        working
  -c CHECK_LIST, --check_list CHECK_LIST
                        Comma separated list of checks to perform. Choices:
                        [http,p2p,nodeos,head]. If not set it performs all the
                        checks sequentially
```


## eoslpb.py
Checks API nodes every second to get the last produced block time and the producer and stores that information in a json file. 

### Dependencies
* Python

### Usage

```bash
./eoslpb.py --help
Usage: eoslpb.py [options]

Options:
  -h, --help            show this help message and exit
  -e ENDPOINTS, --endpoint-list=ENDPOINTS
                        Coma separated list of API nodes. Defaults to
                        https://nodes.get-scatter.com
  -n NETWORK, --network=NETWORK
                        Network name. Defaults to eos
```
