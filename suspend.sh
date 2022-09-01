#!/bin/bash
s_args=''
for i
do
	s_args+=" $i"
done
resp=`python3 wrapper.py commandfile=suspend $s_args`

echo "OK"