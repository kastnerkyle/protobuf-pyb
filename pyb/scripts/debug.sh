#!/bin/bash
#
# debug.sh
# Author: Andy Chu

filename=$1
cat $filename | protoc --decode_raw
echo '-----'
if [ $filename = "addressbook" ]; then 
  cat $filename | protoc --decode tutorial.AddressBook addressbook.proto
fi
