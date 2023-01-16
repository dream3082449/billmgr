#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "No arguments provided"
    exit 1
fi

s_args=''

for i
do
	s_args+=" $i"
done
cd /opt/billmgr
resp=`python3 wrapper.py commandfile=resume $s_args`
read -a strarr <<< $resp
r=`python3 callback.py --request_id=${strarr[0]}`
echo "$r"