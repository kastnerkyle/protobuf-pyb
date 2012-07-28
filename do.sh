#!/bin/bash
#
# To use this, install the protobuf-compiler package in ubuntu.

build-cpp() {
  set -o errexit
  mkdir -p cpp
  protoc --cpp_out cpp "$@"
  tree cpp
}

build-py() {
  set -o errexit
  mkdir -p py
  protoc --python_out py "$@"
  tree py
}

build-java() {
  set -o errexit
  mkdir -p java
  protoc --java_out java "$@"
  tree java
}

# Ubuntu has a package 'protobuf-compiler', which doesn't let you build generate
# C++?  Need 'libprotobuf-dev'.
addr() {
  set -o errexit

  # Output generated code in cpp/ dir
  build-cpp testdata/addressbook/addressbook.proto
  # Compile generated code with demo.  Add cpp to include path, link with
  # libprotobuf.a.
  g++ -o add_person \
    -Icpp \
    -lprotobuf \
    cpp/testdata/addressbook/addressbook.pb.cc \
    examples/add_person.cc

  g++ -o list_people \
    -Icpp \
    -lprotobuf \
    cpp/testdata/addressbook/addressbook.pb.cc \
    examples/list_people.cc
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
  # old for raw_decode, maybe that should be moved
  export PYTHONPATH=pyb:old
  echo foo | bin/pyb_tool.py -d foo:bar encode
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
}

hex() {
  # WTF, hexdump is weird
  # TODO: Make a generic script out of this
  hexdump -v -e '"" 1/1 "%02X" " "' "$@"
  echo
}

bootstrap() {
  export PYTHONPATH=../json-template/python
  local out=pyb/descriptor.py
  cat data/descriptor.proto.json | tools/bootstrap.py | tee $out
  echo "Wrote $out"

}

proto2_demo() {
  build-py testdata/addressbook/addressbook.proto
  # To run with hermetic version:
  # Have to do python -S and add the tar dir
  export PYTHONPATH=py/testdata/addressbook:py #:/home/andy/src/protobuf-2.4.1/python
  scratch/proto2_demo.py "$@"
}

"$@"
