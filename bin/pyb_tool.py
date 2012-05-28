#!/usr/bin/python -S
"""
pyb_tool.py

TODO: I got rid of the crappy pan.core.cmdapp.  But it might be good to revive
your schema for command line tools.
"""

__author__ = 'Andy Chu'


import codecs
import optparse
import os
import sys
import json


import pyb
import raw_decode


class Error(Exception):
  pass


def CreateOptionsParser():
  parser = optparse.OptionParser()

  parser.add_option(
      '-d', '--descriptor', dest='descriptor', type='str', default='',
      help='Descriptor (filename:message-type-name)')

  # This is supposed to be argv[1]?
  parser.add_option(
      '-i', '--input', dest='input', type='str', default='',
      help='Input file')

  return parser


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

  (options, argv) = CreateOptionsParser().parse_args(argv)

  try:
    options.action = argv[1]
  except IndexError:
    raise Error('Usage: pyb_tool <action>')

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
    success = main(sys.argv)
    sys.exit(not success)
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
