#!/bin/bash
# Usage ./prepare.sh <arg>
# Doc under https://github.com/hmeiland/batchprojects

cd application

if [ "$1" == "hpl" ]
then
  echo "cp runscript.sh-working-hpl runscript.sh "
  cp runscript.sh-working-hpl runscript.sh
  cp task.py-working-hpl task.py
  cp prepscript.sh-working-hpl prepscript.sh
  echo "Run this command : python batch_submit.py-hpl -i data/HPL.dat"
  echo "How many nodes? Change POOL_NODE_COUNT in batch_submit.py-hpl "
  echo "Change number of cores in runscript.sh line 38 "
  
  
fi
if [ "$1" == "wrf" ]
then
  echo "cp runscript.sh-working-wrf runscript.sh "
  cp runscript.sh-working-wrf runscript.sh
  cp task.py-working-wrf task.py
  cp prepscript.sh-working-wrf prepscript.sh
  echo "Run this command : python batch_submit.py-wrf -i data/namelist.input"
  echo "How many nodes? Change POOL_NODE_COUNT in batch_submit.py-hpl "
  echo "Change number of cores in runscript.sh line 38 "
fi

if [ "$1" == "abaqus" ]
then
  echo "cp runscript.sh-working-abaqus runscript.sh "
  cp runscript.sh-working-abaqus runscript.sh
  cp task.py-working-abaqus task.py
  cp prepscript.sh-working-abaqus prepscript.sh
  echo "Run this command : python batch_submit.py-abaqus -i data/abaqus_v6.env"
  echo "How many nodes? Change POOL_NODE_COUNT in batch_submit.py-hpl "
  echo "Change number of cores in runscript.sh line 38 "
fi


