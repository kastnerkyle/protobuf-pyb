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



if __name__ == '__main__':
  unittest.main()
