#!/bin/bash
#
# To use this, install the protobuf-compiler package in ubuntu.

build-cpp() {
  set -o errexit
  mkdir -p cpp
  protoc --cpp_out cpp "$@"
  tree cpp
}

addr() {
  build-cpp testdata/addressbook/addressbook.proto
}

"$@"
