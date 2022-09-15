#!/bin/bash
s_args=''
for i
do
	s_args+=" $i"
done
resp=`python3 /opt/billmgr/wrapper.py commandfile=open $s_args`
IFS=' '
#read -a strarr <<< $resp
#r=`python3 /opt/billmgr/callback.py --request_id=${strarr[0]}`
r=1243
echo "OK $r"