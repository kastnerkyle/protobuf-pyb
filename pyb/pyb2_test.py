#!/usr/bin/python
"""
pyb2_test.py: Tests for pyb2.py
"""

__author__ = 'Andy Chu'


from pprint import pprint
import sys
import unittest

try:
  import json
except ImportError:
  import simplejson as json

import pyb2 as pyb # module under test

TEST_PROTO = 'testdata/trivial/test.desc.json-from-pyb'
ADDRESS_BOOK_PROTO = 'testdata/addressbook/addressbook.desc.json-from-protoc'

class PybTest(unittest.TestCase):

  def testMakeTypes(self):
    d = pyb._LoadDescriptorProto()

    desc_set = pyb.DescriptorSet(d)
    decoder = desc_set.GetDecoder('proto2.EnumOptions')
    pprint(decoder)

    decoder = desc_set.GetDecoder('proto2.FileOptions')
    pprint(decoder)

    decoder = desc_set.GetDecoder('proto2.DescriptorProto')
    print 'DESCRIPTOR'
    #pprint(decoder)

    #pprint(desc_set.type_index.keys())

  def testAddressBook(self):
    # This isn't bootstrapped -- this is just a small test
    f = open(ADDRESS_BOOK_PROTO)
    d = json.load(f)
    f.close()

    desc_set = pyb.DescriptorSet(d)
    decode = desc_set.GetDecoder('.tutorial.AddressBook')
    print decode

    f = open('testdata/addressbook/addressbook.encoded')
    buf = f.read()
    print decode(buf)

  def testTrivial(self):
    # This isn't bootstrapped -- this is just a small test
    f = open(TEST_PROTO)
    d = json.load(f)
    f.close()
    print d
    desc_set = pyb.DescriptorSet(d)
    decode = desc_set.GetDecoder('Test1')

    f = open('test.bin')
    buf = f.read()
    result = decode(buf)
    print 'RESULT', result

  def testIndexTypes(self):
    f = open(TEST_PROTO)
    d = json.load(f)
    f.close()

    type_index = {}
    root = pyb.IndexTypes(d, type_index)
    pyb.PrintSubtree(root)
    pprint(type_index)

    f = open(ADDRESS_BOOK_PROTO)
    d = json.load(f)
    f.close()

    type_index = {}
    root = pyb.IndexTypes(d, type_index)
    pyb.PrintSubtree(root)
    pprint(type_index)



if __name__ == '__main__':
  unittest.main()
