#!/bin/bash
s_args=''
for i
do
	s_args+=" $i"
done
cd /opt/billmgr
resp=`python3 wrapper.py commandfile=resume $s_args`

echo "OK"