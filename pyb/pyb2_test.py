#!/usr/bin/python
"""
pyb2_test.py: Tests for pyb2.py
"""

__author__ = 'Andy Chu'


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
    type_index = {}
    from pprint import pprint

    #pyb.IndexTypes(d, type_index)
    #import pprint
    #pprint.pprint(type_index)

    desc_set = pyb.DescriptorSet(d)
    decoder = desc_set.GetDecoder('proto2.EnumOptions')
    pprint(decoder)
    pprint(desc_set.type_index)



if __name__ == '__main__':
  unittest.main()
