#!/usr/bin/python -S
"""
raw_decode.py
"""

__author__ = 'Andy Chu'


import struct
import sys
import pprint

import decoding


class Error(Exception):
  pass


class DecodeError(Error):
  pass


def _DecodePart(s, pos, trial=False, indent=0):
  """Yields key-value pairs."""
  result = {}

  space = indent * ' '

  while pos < len(s):
    key, pos = decoding.DecodeVarInt(s, pos)
    tag = key >> 3
    wire_type = key & 0x07

    if wire_type == 4:  # End group
      print '*** EARLY RETURN'
      return result, pos  # EARLY RETURN

    print space, 'Decoding message of length %s' % len(s)
    print space, 'tag', tag, 'wire type:', wire_type

    if wire_type == 0:  # varint
      value, pos = decoding.DecodeVarInt(s, pos)

    elif wire_type == 1:  # 64 bit
      # <Q means little endian 64 bit
      try:
        (value,) = struct.unpack('<Q', s[pos : pos+8])
      except struct.error, e:
        raise DecodeError(e)
      pos += 8

    elif wire_type == 2:  # bytes
      length, pos = decoding.DecodeVarInt(s, pos)
      value = s[pos : pos+length]
      # Heuristic to tell if a byte string is a message or just a string.
      # TODO: Schema tells us if it's unicode or bytes.
      # TODO: This can cause weird problems!
      try:
        value, _ = _DecodePart(value, 0, trial=True, indent=indent+2)
      except DecodeError, e:
        print space, "Can't decode as BYTES"
        # If we get here, then value is still a string.  Otherwise, it's been
        # transformed into a dictionary.
        pass

      pos += length

    elif wire_type == 3:  # Start group
      value, pos = _DecodePart(s, pos, indent=indent+2)
      print 'GROUP', value, pos

    elif wire_type == 4:
      raise DecodeError('No groups yet')

    elif wire_type == 5:  # 32 bit
      # <Q means little endian 32 bit
      try:
        (value,) = struct.unpack('<I', s[pos : pos+4])
      except struct.error, e:
        raise DecodeError(e)
      pos += 4

    else:
      raise DecodeError('Invalid wire type %s' % wire_type)

    print space, '---- w', wire_type

    # If we already this tag, transform the value into a list of values
    if tag in result:
      prev_value = result[tag]
      if isinstance(prev_value, list):
        prev_value.append(value)
      else:
        result[tag] = [prev_value, value]
    else:
      result[tag] = value

  return result, pos


def DecodeWithoutDescriptor(s):
  return _DecodePart(s, 0)[0]


def main(argv):
  s = open(argv[1], 'rb').read()
  value = DecodeWithoutDescriptor(s)
  pprint.pprint(value)
  #json.dumps(value, indent=2, sort_keys=True)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except DecodeError, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)

