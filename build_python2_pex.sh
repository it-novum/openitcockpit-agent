#!/bin/bash

cd "$(dirname "$0")"

pip install pex

pex . --python=python2 -r requirements_python2.txt -c oitc_agent.py -o openitcockpit-agent_python2.pex

rm -r openitcockpit_agent.egg-info

echo "$(dirname "$0")/openitcockpit-agent_python2.pex"
 
