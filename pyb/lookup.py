#!/usr/bin/python -S
"""
lookup.py
"""

__author__ = 'Andy Chu'


import wire_format
import decoder


# Pyb version of type_checkers.FIELD_TYPE_TO_WIRE_TYPE.
FIELD_TYPE_TO_WIRE_TYPE = {
    'TYPE_DOUBLE': wire_format.WIRETYPE_FIXED64,
    'TYPE_FLOAT': wire_format.WIRETYPE_FIXED32,
    'TYPE_INT64': wire_format.WIRETYPE_VARINT,
    'TYPE_UINT64': wire_format.WIRETYPE_VARINT,
    'TYPE_INT32': wire_format.WIRETYPE_VARINT,
    'TYPE_FIXED64': wire_format.WIRETYPE_FIXED64,
    'TYPE_FIXED32': wire_format.WIRETYPE_FIXED32,
    'TYPE_BOOL': wire_format.WIRETYPE_VARINT,
    'TYPE_STRING':
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    'TYPE_GROUP': wire_format.WIRETYPE_START_GROUP,
    'TYPE_MESSAGE':
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    'TYPE_BYTES':
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    'TYPE_UINT32': wire_format.WIRETYPE_VARINT,
    'TYPE_ENUM': wire_format.WIRETYPE_VARINT,
    'TYPE_SFIXED32': wire_format.WIRETYPE_FIXED32,
    'TYPE_SFIXED64': wire_format.WIRETYPE_FIXED64,
    'TYPE_SINT32': wire_format.WIRETYPE_VARINT,
    'TYPE_SINT64': wire_format.WIRETYPE_VARINT,
    }

# Pyb version of type_checkers.TYPE_TO_DECODER
TYPE_TO_DECODER = {
    'TYPE_DOUBLE': decoder.DoubleDecoder,
    'TYPE_FLOAT': decoder.FloatDecoder,
    'TYPE_INT64': decoder.Int64Decoder,
    'TYPE_UINT64': decoder.UInt64Decoder,
    'TYPE_INT32': decoder.Int32Decoder,
    'TYPE_FIXED64': decoder.Fixed64Decoder,
    'TYPE_FIXED32': decoder.Fixed32Decoder,
    'TYPE_BOOL': decoder.BoolDecoder,
    'TYPE_STRING': decoder.StringDecoder,
    'TYPE_GROUP': decoder.GroupDecoder,
    'TYPE_MESSAGE': decoder.MessageDecoder,
    'TYPE_BYTES': decoder.BytesDecoder,
    'TYPE_UINT32': decoder.UInt32Decoder,
    'TYPE_ENUM': decoder.EnumDecoder,
    'TYPE_SFIXED32': decoder.SFixed32Decoder,
    'TYPE_SFIXED64': decoder.SFixed64Decoder,
    'TYPE_SINT32': decoder.SInt32Decoder,
    'TYPE_SINT64': decoder.SInt64Decoder,
    }
