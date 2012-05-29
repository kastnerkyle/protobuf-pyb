#!/usr/bin/python
"""
proto2_demo.py
"""

__author__ = 'Andy Chu'


import sys
from pprint import pprint

import addressbook_pb2
import en_pb2


class Error(Exception):
  pass


def main(argv):
  """Returns an exit code."""
  b = addressbook_pb2.AddressBook()
  p = b.person.add()
  p.name = 'yo'
  print p
  q = b.person.add()
  q.name = 'bar'
  print q


  for person in b.person:
    print type(person)
    print person


  t = en_pb2.Test1()
  t.s.append('foo')
  t.s.append('bar')
  print t
  for element in t.s:
    print type(element)
    print dir(element)
    print element

  bytes = t.SerializeToString()
  print 'BYTES', repr(bytes)

  for element in t.s:
    print type(element)
    print dir(element)
    print element

  pprint(sys.modules)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
