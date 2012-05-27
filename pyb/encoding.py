#!/usr/bin/python -S
"""
encoding.py

pyb2 encoding.
"""

__author__ = 'Andy Chu'


import sys


class MessageEncoder(object):

  def __init__(self):
    # These are "compiled" from the schema.
    self.encoders = []

  def __call__(self, obj):
    chunks = []
    for encoder in self.encoders:
      c = encoder(self.obj)
      if c:
        chunks.append(c)
    return ''.join(chunks)


class Error(Exception):
  pass


def main(argv):
  """Returns an exit code."""
  print 'Hello from encoding.py'
  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
