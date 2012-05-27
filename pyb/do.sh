#!/bin/bash
#
# To use this, install the protobuf-compiler package in ubuntu.

build-cpp() {
  set -o errexit
  mkdir -p cpp
  protoc --cpp_out cpp "$@"
  tree cpp
}

# damnit, this fails on ubuntu
build-py() {
  set -o errexit
  mkdir -p py
  protoc --py_out py "$@"
  tree py
}

build-java() {
  set -o errexit
  mkdir -p java
  protoc --java_out java "$@"
  tree java
}

addr() {
  build-cpp testdata/addressbook/addressbook.proto
}

"$@"
