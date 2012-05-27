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

# bash completion
unit() {
  export PYTHONPATH=../../taste/taste
  "$@"
}

count() {
  wc -l *.py
}

# Tried out tool, doesn't quite work yet
tool-test() {
  echo foo | ./pyb_tool.py -d foo:bar encode
}

"$@"
