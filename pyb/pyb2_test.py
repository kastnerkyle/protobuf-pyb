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

import pyb2  # module under test


class PybTest(unittest.TestCase):

  def testAttrDict(self):
    d = pyb2.AttrDict(a=1)
    print d.a

  def testAttrDictJson(self):
    d = json.loads('{"a":1}', object_hook=pyb2.AttrDict)
    print d.a

    d = json.loads('{"a":{"b":1}}', object_hook=pyb2.AttrDict)
    print d.a
    print d.a.b


if __name__ == '__main__':
  unittest.main()
