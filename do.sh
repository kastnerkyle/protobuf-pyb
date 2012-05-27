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
  wc -l pyb/*.py
}

# Tried out tool, doesn't quite work yet
tool-test() {
  echo foo | ./pyb_tool.py -d foo:bar encode
}

# This is a proto2 example, requiring generated code
add_person() {
  examples/add_person.py "$@"
}

# pyb example
list_people() {
  examples/list_people.py testdata/addressbook/addressbook.encoded
}

protoc-decode() {
  local filename=$1
  echo 'decode_raw:'
  echo '-----'
  cat $filename | protoc --decode_raw
  echo
  echo 'decode:'
  echo '-----'
  if true; then
    cat $filename | protoc --decode tutorial.AddressBook \
      testdata/addressbook/addressbook.proto
  fi
}

# TODO: pyb should do the equivalent of this.
decode-descriptor() {
  cat testdata/addressbook/addressbook.desc.encoded | protoc \
      --decode google.protobuf.FileDescriptorSet \
      data/descriptor.proto
}

# Make the tiny protobuf as in:
# http://code.google.com/apis/protocolbuffers/docs/encoding.html

maketest() {
  set -o errexit

  echo 'a: 150' | protoc --encode Test1 testdata/trivial/test.proto > test.bin
  echo 'Wrote file "test"'

  # WTF, hexdump is weird
  hex test.bin
  echo
}

hex() {
  # WTF, hexdump is weird
  # TODO: Make a generic script out of this
  hexdump -v -e '"" 1/1 "%02X" " "' "$@"
}

"$@"
