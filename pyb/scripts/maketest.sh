#!/bin/bash
#
# maketest.sh
# Author: Andy Chu

# Make the tiny protobuf as in:
# http://code.google.com/apis/protocolbuffers/docs/encoding.html

echo 'a: 150' | protoc --encode Test1 test.proto > test
echo 'Wrote file "test"'

# WTF, hexdump is weird
./hexdump.sh test
echo
