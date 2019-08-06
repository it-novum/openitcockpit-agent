#!/bin/bash

cd "$(dirname "$0")"

pip install pex

pex . --python=python3 -r requirements.txt -c oitc_agent.py -o openitcockpit-agent.pex

rm -r openitcockpit_agent.egg-info

echo "$(dirname "$0")/openitcockpit_agent.pex"
