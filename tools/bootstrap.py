#!/usr/bin/python -S
"""
bootstrap.py

Generate a small enum from descriptor.proto.json.

The real bootstrap is "dynamic", but this part generates code so we can reuse
type_checkers.py.  Don't want to create unnecessary diffs.
"""

__author__ = 'Andy Chu'


import json
import sys

import jsontemplate


class Error(Exception):
  pass


def PrintEnums(d):
  for f in d['file']:
    for m in f['message_type']:
      name = m['name']
      if name == 'FieldDescriptorProto':
        #print m['enum_type']
        for t in m['enum_type']:
          enum_name = t['name']
          if enum_name == 'Type':
            value = t['value']
            print TEMPLATE.expand(value)


def main(argv):
  """Returns an exit code."""
  descriptor_proto = json.load(sys.stdin)
  #from pprint import pprint
  #pprint(descriptor_proto)
  PrintEnums(descriptor_proto)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
