#!/bin/bash

if [[ ! -f $1 ]]; then
    echo "Cant find config file: $1"
    echo "Usage: "
    echo "  ./filter_peers.sh <config_file>"
    echo
    exit 1
fi

function check_peer {
    eval nc -z -w 1 "$@" > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        echo "p2p-peer-address = ${1/ /:}"
    fi
}

grep -E "p2p-peer-address" $1 | sed -E "s/^p2p-peer-address *= *//" | sed -E "s/:/ /" | while read -r line ; do
    check_peer "$line"
done