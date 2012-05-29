#!/usr/bin/python
"""
pyb_test.py: Tests for pyb.py
"""

__author__ = 'Andy Chu'


from pprint import pprint
import sys
import unittest

try:
  import json
except ImportError:
  import simplejson as json

import pyb  # module under test


TEST_PROTO = 'testdata/trivial/test.desc.json-from-pyb'
ADDRESS_BOOK_PROTO = 'testdata/addressbook/addressbook.desc.json-from-protoc'


class PybTest(unittest.TestCase):

  def setUp(self):
    f = open(TEST_PROTO)
    d = json.load(f)
    f.close()
    print d
    self.trivial = pyb.DescriptorSet(d)

    # This isn't bootstrapped -- this is just a small test
    f = open(ADDRESS_BOOK_PROTO)
    d = json.load(f)
    f.close()
    self.address_book = pyb.DescriptorSet(d)

    d = pyb._LoadDescriptorProto()

    self.descriptor_proto = pyb.DescriptorSet(d)

  def testDescriptorProto(self):
    desc_set = self.descriptor_proto

    decode = desc_set.GetDecoder('.proto2.EnumOptions')
    pprint(decode)

    decode = desc_set.GetDecoder('.proto2.FileOptions')
    pprint(decode)

    decode = desc_set.GetDecoder('.proto2.DescriptorProto')
    print 'DESCRIPTOR'
    #pprint(decode)

    # decode a descriptor

    decode = desc_set.GetDecoder('.proto2.FileDescriptorSet')
    print 'DESCRIPTOR'
    #pprint(decode)

    #pprint(desc_set.type_index.keys())

    f = open('testdata/addressbook/addressbook.desc.encoded')
    buf = f.read()
    f.close()

    # Bootstrapping test.    We got a dictionary that represents the
    # address book descriptor.
    # Now instantiate another DescriptorSet, and use that to decode address book
    # protocol buffers.

    # Bug: deoding needs to handle enums.  11 -> TYPE_MESSAGE, etc.
    address_desc_dict = decode(buf)
    pprint(address_desc_dict)

    address_desc = pyb.DescriptorSet(address_desc_dict)
    decode = address_desc.GetDecoder('.tutorial.AddressBook')
    print decode

  def testAddressBookDecode(self):

    decode = self.address_book.GetDecoder('.tutorial.AddressBook')
    print decode

    f = open('testdata/addressbook/addressbook.encoded')
    buf = f.read()
    result = decode(buf)
    print 'RESULT'
    pprint(result)

  def testAddressBookEncodePerson(self):
    encode = self.address_book.GetEncoder('.tutorial.Person')
    bytes = encode({'name': 'Jill'})
    print 'BYTES', repr(bytes)

  def testAddressBookEncode(self):

    encode = self.address_book.GetEncoder('.tutorial.AddressBook')

    # TODO: Have to test for required fields?
    bytes = encode({'person': [{'name': 'Jill'}]})
    print 'BYTES', repr(bytes)

  def testTrivialDecode(self):
    # This isn't bootstrapped -- this is just a small test

    # TODO: Fix this -- if there's no package
    decode = self.trivial.GetDecoder('.Test1')

    f = open('test.bin')
    buf = f.read()
    result = decode(buf)
    print 'RESULT', result

  def testTrivialEncode(self):
    # This isn't bootstrapped -- this is just a small test

    encode = self.trivial.GetEncoder('.Test1')
    bytes = encode({'a': 150})
    print 'BYTES', repr(bytes)
    f = open('test2.bin', 'w')
    f.write(bytes)
    f.close()

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

  def testMakeDescriptors(self):
    ds = self.address_book  # DescriptorSet

    descriptors = pyb._MakeDescriptors(
        ds.type_index, ds.descriptor_index, '.tutorial.AddressBook')
    print descriptors

    # Make sure we have all 3
    self.assertEqual(
        set(['.tutorial.AddressBook', 
          '.tutorial.Person',
          '.tutorial.Person.PhoneNumber']),
        set(ds.descriptor_index.keys()))

    print 'DESCRIPTORS'
    pyb.PrintSubtree(ds.descriptor_index)
    print


    print ds.descriptor_index['.tutorial.AddressBook']['person'].fields

    return
    ds = self.descriptor_proto
    descriptors = pyb._MakeDescriptors(
        ds.type_index, ds.descriptor_index, '.proto2.FileDescriptorSet')

    print 'DESCRIPTORS'
    pyb.PrintSubtree(ds.descriptor_index)
    print

  def testMakeTree(self):
    ds = self.address_book  # DescriptorSet
    descriptors = pyb._MakeDescriptors(
        ds.type_index, ds.descriptor_index, '.tutorial.AddressBook')
    t = pyb._MakeTree({'person': [{'name': 'Jill'}]}, descriptors)

    print '---'
    print t
    print '---'
    print 'person'
    print t.value['person']
    print
    print t.descriptors['person']
    print '---'
    print 'person[0]'
    print t.value['person'].value[0]
    print
    print t.value['person'].descriptors
    print '---'
    print "person[0]['name']"
    print t.value['person'].value[0].value['name']
    print
    print t.value['person'].value[0].descriptors


if __name__ == '__main__':
  unittest.main()
