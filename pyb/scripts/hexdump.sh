#!/bin/bash
#
# hexdump.sh
# Author: Andy Chu

# WTF, hexdump is weird
# TODO: Make a generic script out of this
hexdump -v -e '"" 1/1 "%02X" " "' "$@"
