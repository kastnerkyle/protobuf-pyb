#!/usr/bin/python -S
"""
pyb_tool.py
"""

__author__ = 'Andy Chu'


import codecs
import os
import sys

from pan.core import cmdapp
from pan.core import json
from pan.core import params

import pyb
import raw_decode


class Error(Exception):
  pass

# This can be used with DoWork and num_threads
PARAMS = [
    params.RequiredString('action',
        choices=['encode', 'decode', 'decode-raw', 'decode-desc'], pos=1),
    params.OptionalString(
        'input', shortcut='i', pos=2, help='Input data filename'),
    params.OptionalString(
        'descriptor', shortcut='d',
        help='Descriptor (filename:message-type-name)'),
    ]


def ParseDescriptor(desc):
  """Validate and convert descriptor.

  TODO: In params.py, need to be able to specify parser=ParseDescriptor.
  The parser can raise some exception like ValidationError too do cause a
  UsageError.
  """
  try:
    filename, type_name = desc.split(':', 1)
  except ValueError:
    raise Error('Descriptor must be of the form filename:message-type-name')
  return filename, type_name


def main(argv):
  """Returns success/failure."""

  # TODO: Distinguish between actions that share the same flag namespace, and
  # ones that have their own.

  # Maybe parse all flags first.  And then based on argv[0], choose which
  # schema to use.  params.py doesn't support this now.  Or it is awkward, you
  # have to do params.UNDECLARED

  options = cmdapp.ParseArgv(argv, PARAMS)

  if options.input and options.input != '-':
    infile = open(options.input, 'rb')
  else:
    # On Windows, set stdin to binary mode.
    if sys.platform == 'win32':
      import msvcrt
      msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    infile = sys.stdin

  s = infile.read()
  infile.close()

  try:
    if options.action == 'encode':
      if options.descriptor:
        filename, type_name = ParseDescriptor(options.descriptor)
      else:
        raise Error('A descriptor is required for encoding')
      data = open(filename).read()
      desc_set = json.loads(data)

    elif options.action == 'decode':
      if options.descriptor:
        filename, type_name = ParseDescriptor(options.descriptor)
      else:
        raise Error('A descriptor is required for decoding')

      db = pyb.DescriptorSet.FromJsonFile(filename)
      message_type = db.Type(type_name)
      message = message_type(s)
      print pyb.EncodeJson(message, indent=2, sort_keys=True)

    elif options.action == 'decode-desc':
      desc = pyb.FileDescriptorSet(s)
      print pyb.EncodeJson(desc, indent=2, sort_keys=True)

    elif options.action == 'decode-raw':
      message = raw_decode.DecodeWithoutDescriptor(s)
      print json.dumps(message, indent=2, sort_keys=True)

    else:
      raise AssertionError

  except (pyb.Error, raw_decode.Error), e:
    print >> sys.stderr, e
    return False

  return True


if __name__ == '__main__':
  try:
    success = main(sys.argv[1:])
    sys.exit(not success)
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
