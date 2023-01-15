#!/bin/bash
if not $i:
	echo "parameter not found"
	exit 0
fi
s_args=''
for i
do
	s_args+=" $i"
done
cd /opt/billmgr
resp=`python3 wrapper.py commandfile=open $s_args`
#read -a strarr <<< $resp
r=`python3 callback.py --request_id=${strarr[0]}`
echo "OK $r"