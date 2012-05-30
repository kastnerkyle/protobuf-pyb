#!/usr/bin/python
"""
pyb2.py

Better version of pyb where we:

  - Don't care about the "internal Python" interface -- we use dicts; we don't
    use metaclasses to generate Python classes for each message type.
  - Compile the schema into a tree of decoding functions.
  - Lazily decode?  I don't see a need for this now, but it might fall out.

We reuse encoder.py, decoder.py, and wire_format.py from the open source Python
implementation.

Now all we have to do is walk through the descriptor and construct a tree of
decoders.


Dynamic bootstrapping
----------------------

1. Start with the meta descriptor as JSON
2. Create pyb.DescriptorSet from it
3. Decode a binary descriptor (e.g. addressbook) using the DescriptorSet,
getting a dictinoary
3. Create a pyb.DescriptorSet from that
4. Decode and encode regular messages using the descriptor
"""

__author__ = 'Andy Chu'


from pprint import pprint
import sys

try:
  import json
except ImportError:
  import simplejson as json

import lookup
import decoder
import encoder


class Error(Exception):
  pass


def PrintSubtree(subtree, indent=0):
  names = sorted(subtree)
  for name in names:
    value = subtree[name]
    print ' ' * indent + name,
    if isinstance(value, dict):
      print
      PrintSubtree(value, indent+2)
    else:
      print '\t' + str(value)


#
# ENCODING
#


class _BaseValue(object):

  def __str__(self):
    return '<Value %s %s>' % (self.value, self.descriptors)


class _MessageEncodeNode(_BaseValue):
  """
  A message value in the encoding tree.  Occurs at the top level (since a
  message is the only kind of node that can be encoded) and WITHIN the tree.
  """

  def __init__(self, value, descriptors):
    """
    Args:
      value: dictionary representing the message (field name -> value)
      descriptors: field name -> Descriptor() instance
    """
    self.value = value
    self.descriptors = descriptors

  def ByteSize(self):
    """
    Called by stuff in encoders.py.
    """
    # TODO: Does there need to be a cache?  I think there are multiple recursive
    # calls to the same sizer?
    size = 0
    for field_name, descriptor in self.descriptors.iteritems():
      node = self.value.get(field_name)
      if node:
        size += descriptor.sizer(node.value)
    return size

  # TODO: port this logic, not used yet
  def _IsPresent(item):
    """
    Given a (FieldDescriptor, value) tuple from _fields, return true if the
    value should be included in the list returned by ListFields()."""

    if item[0].label == _FieldDescriptor.LABEL_REPEATED:
      return bool(item[1])
    elif item[0].cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      return item[1]._is_present_in_parent
    else:
      return True

  # TODO: port this logic, not used yet
  def ListFields(self):
    """
    Returns a list of field descriptor -> value?
    """
    # TODO: When constructing a descriptor,
    all_fields = [item for item in self._fields.iteritems() if _IsPresent(item)]
    all_fields.sort(key = lambda item: item[0].number)
    return all_fields

  def _InternalSerialize(self, write_bytes):
    """
    """
    # TODO: sort the fields by number
    for field_name, descriptor in self.descriptors.iteritems():
      node = self.value.get(field_name)
      if node:
        descriptor.encoder(write_bytes, node.value)


class _RepeatedValueNode(_BaseValue):

  def __init__(self, value, descriptor):
    """
    """
    self.value = value
    self.descriptors = descriptor


class _Atom(_BaseValue):

  def __init__(self, value, descriptor):
    """
    """
    self.value = value
    self.descriptor = descriptor

  def __str__(self):
    return '<Value %s %s>' % (self.value, self.descriptor)


def _MakeNode(value, descriptor):
  """
  Args:
    value: single value
    descriptor: Descriptor instance
  """
  # TODO: The dichotomy here should be composite/primitive, NOT dict/list.  If
  # we have a message descriptor, then we should create a _MessageEncodeNode.
  # Otherwise we create an _Atom node.

  print '_MakeNode', value, descriptor
  if isinstance(value, dict):
    assert isinstance(descriptor.fields, dict)
    return _DictToTree(value, descriptor.fields)

  elif isinstance(value, list):
    li = []
    for item in value:
      li.append(_MakeNode(item, descriptor))
    node = _RepeatedValueNode(li, descriptor)
    return node
  else:
    # Field descriptor?
    return _Atom(value, descriptor)


def _DictToTree(node, descriptors):
  """
  Args:
    node: root raw dictionary object
    descriptors: dict of Descriptor() instances (output of _MakeDescriptors)

  Returns:
    Tree of _Node objects

  Take a simple dictionary and create a _MessageEncodeNode tree.
  """
  # NOTE: There is this assymetry because in protobufs, you MUST encode
  # dictionaries (composites).  You can't encode just an atom -- it needs to be
  # part of a message.  Everything has a name!

  assert isinstance(node, dict)
  d = {}
  for name, value in node.iteritems():
    print 'NAME', name, 'VALUE', value
    descriptor = descriptors[name]
    d[name] = _MakeNode(value, descriptor)
  return _MessageEncodeNode(d, descriptors)


class Encoder(object):
  """
  This objects exists independent of any values.

  _MessageEncodeNode is created with values.
  """
  def __init__(self, descriptors):
    self.descriptors = descriptors

  def encode(self, obj):
    """
    Args:
      obj: A dictinoary

    First we transform it to a tree of nodes, with type information.  Then we
    call the right encoder.
    """
    # this weird structure is forced by encoder.py/decoder.py
    obj = _DictToTree(obj, self.descriptors)

    buf = []
    write_bytes = buf.append
    obj._InternalSerialize(write_bytes)
    return ''.join(buf)


class Descriptor(object):
  """
  Describes a message, or a field?

  descriptor_index is ( field name -> Descriptor Instance)
  """
  def __init__(self, encoder, sizer, fields):
    self.encoder = encoder 
    self.sizer = sizer 
    self.fields = fields
    # fields are pointers to other descriptors?
    # field name -> descriptor?

  def __str__(self):
    return '<Descriptor %s %s>' % (
        self.encoder.__name__,
        self.sizer.__name__)

  def __repr__(self):
    return str(self)


def _MakeDescriptors(type_index, descriptor_index, type_name):
  """
  When an encoder is requested, we have walk the type graph recursively and make
  encoders/sizers for all types (INDEPENDENT of any values).
  """
  message_dict = type_index[type_name]
  descriptors = {}  # field name -> Descriptor instance

  fields = message_dict.get('field')
  if not fields:
    print message_dict
    raise Error('No fields for %s' % type_name)

  for f in fields:
    field_type = f['type']  # a string
    number = f['number']  # a string
    name = f['name']  # a string
    wire_type = lookup.FIELD_TYPE_TO_WIRE_TYPE[field_type]  # int

    print '---------'
    print 'encoders FIELD name', f['name']
    print 'encoders field type', field_type
    print 'encoders wire type', wire_type

    #tag_bytes = encoder.TagBytes(number, wire_type)

    # get a encoder constructor, e.g. MessageENcoder
    make_encoder = lookup.TYPE_TO_ENCODER[field_type]
    print 'MAKE_ENCODER', make_encoder
    make_sizer = lookup.TYPE_TO_SIZER[field_type]
    print 'MAKE_SIZE', make_sizer

    is_repeated = (f['label'] == 'LABEL_REPEATED')
    is_packed = False

    # Recurse
    sub_descriptors = {}
    if field_type == 'TYPE_MESSAGE':
      sub_type_name = f.get('type_name')
      assert sub_type_name
      print "type name", sub_type_name

      # Populate the decoders_index so that the constructor returned below can
      # access decoders.
      if sub_type_name not in descriptor_index:
        # mark visited BEFORE recursive call, preventing infinite recursion
        descriptor_index[sub_type_name] = True
        sub_descriptors = _MakeDescriptors(type_index, descriptor_index,
                                           sub_type_name)

    # Now create the encoders/sizer by calling the constructor.  Put them in two
    # indexes { field name -> encoder } and { field name -> sizer }
    #
    # NOTE: In proto2, there is a FieldDescriptor for each field.  And we attach
    # the encoder/sizer there, which is faster to look up.
    #
    # There is a Descriptor for the message, which has a _fields dict of
    # FieldDescriptor -> default value.  That is used in ListFields.

    encoder = make_encoder(number, is_repeated, is_packed)
    sizer = make_sizer(number, is_repeated, is_packed)
    desc = Descriptor(encoder, sizer, sub_descriptors)
    descriptors[name] = desc


  # NOTE: We can't create a root descriptor here.  Because an encoder needs a
  # TAG number, and the root has no tag.

  # RESULT: populate descriptor index
  descriptor_index[type_name] = descriptors
  return descriptors


#
# DECODING
#

def _DefaultValueConstructor(field, type_index, decoders_index, is_repeated):
  """
  Args:
    field: field descriptor dictionary

  Mutually recursive with _MakeDecoders.

  Types can contain themselves, e.g. DescriptorProto contains DescriptorProto
  nested_types.
  
  So we have to make sure that *decoders* can contain references to themselves.
  A decoder is a dict

    {  tag bytes -> decoding function }

  In the case of a message type, 

    {  tag bytes -> decoder returned by MessageDecoder }

  The decoder has a reference to new_default, which creates _MessageNode which
  holds refernces to the proper decoders.
  """
  field_type = field['type']
  print "DEFAULT VALUE for", field_type
  type_name = field.get('type_name')
  print "type name", type_name
  repeated = (field['label'] == 'LABEL_REPEATED')

  if field_type == 'TYPE_MESSAGE':
    type_name = field.get('type_name')
    assert type_name

    # Populate the decoders_index so that the constructor returned below can
    # access decoders.
    if type_name not in decoders_index:
      # mark visited BEFORE recursive call, preventing infinite recursion
      decoders_index[type_name] = True
      decoders = _MakeDecoders(type_index, decoders_index, type_name)
      decoders_index[type_name] = decoders

    if is_repeated:
      return lambda m: _MessageListNode(decoders_index, type_name)
    else:
      return lambda m: _MessageNode(decoders_index, type_name)

  else:  # scalar
    if is_repeated:
      return lambda m: _ScalarListNode(lambda: field['default_value'])
    else:
      return lambda m: field['default_value']


def _MakeDecoders(type_index, decoders_index, type_name):
  """
  When a decoder is requested for a given type, walk the type graph recursively
  and make decoders (INDEPENDENT of any actual values).
  """
  #pprint(self.root)
  message_dict = type_index[type_name]
  # For other types

  decoders = {}  # tag bytes -> decoder function
  fields = message_dict.get('field')
  if not fields:
    print message_dict
    raise Error('No fields for %s' % type_name)

  for f in fields:
    field_type = f['type']  # a string
    wire_type = lookup.FIELD_TYPE_TO_WIRE_TYPE[field_type]  # int
    tag_bytes = encoder.TagBytes(f['number'], wire_type)

    # get a decoder constructor, e.g. MessageDecoder
    decoder = lookup.TYPE_TO_DECODER[field_type]
    is_repeated = (f['label'] == 'LABEL_REPEATED')
    is_packed = False

    #is_packed = (field_descriptor.has_options and
    #             field_descriptor.GetOptions().packed)

    # field_descriptor, field_descriptor._default_constructor))

    # key for field_dict
    key = f['name']
    new_default = _DefaultValueConstructor(f, type_index, decoders_index,
                                           is_repeated)

    # Now create the decoder by calling the constructor
    decoders[tag_bytes] = decoder(f['number'], is_repeated, is_packed, key,
                                  new_default)

    print '---------'
    print 'FIELD name', f['name']
    print 'field type', field_type
    print 'wire type', wire_type

  # Now we need to get decoders.  They can be memoized in this class.
  # self.decoder_root = {}

  return decoders


class _MessageNode(object):
  """
  This is instantiated in GetDecoder -> function returned by
  _DefaultValueConstructor.
  """

  def __init__(self, decoders_index, type_name):
    # Do lookup on construction
    self.decoders = decoders_index.get(type_name)
    assert self.decoders is not None, "Expected decoders for %r" % type_name
    assert self.decoders is not True, "Got placeholder True for %r" % type_name
    self.field_dict = {}

  def _InternalParse(self, buffer, pos, end):
    # These statements used to be one level up
    local_ReadTag = decoder.ReadTag
    local_SkipField = decoder.SkipField
    decoders_by_tag = self.decoders

    field_dict = self.field_dict
    while pos != end:
      #print 'POS:', pos
      (tag_bytes, new_pos) = local_ReadTag(buffer, pos)
      field_decoder = decoders_by_tag.get(tag_bytes)
      if field_decoder is None:
        new_pos = local_SkipField(buffer, new_pos, end, tag_bytes)
        if new_pos == -1:
          return pos
        pos = new_pos
      else:
        pos = field_decoder(buffer, new_pos, end, self, field_dict)

    return pos

  def decode(self, buffer):
    """Decode function."""
    pos = self._InternalParse(buffer, 0, len(buffer))
    return _TreeToDict(self)


def _TreeToDict(node):
  """
  Take a _MessageNode tree and create a simple dictionary.
  """
  if isinstance(node, _MessageNode):
    result = {}
    for k, v in node.field_dict.iteritems():
      result[k] = _TreeToDict(v)
    return result
  elif isinstance(node, list):
    result = []
    for item in node:
      result.append(_TreeToDict(item))
    return result
  else:
    return node


class _MessageListNode(list):

  def __init__(self, decoders_index, type_name):
    self.decoders_index = decoders_index
    self.type_name = type_name

  def add(self):
    """Return a new value of the given type.  Add it to the end of the list"""

    # ARGH, this might not be a message.
    x = _MessageNode(self.decoders_index, self.type_name)
    self.append(x)
    return x


class _ScalarListNode(list):

  def __init__(self, new_default):
    self.new_default = new_default

  def add(self):
    """Return a new value of the given type.  Add it to the end of the list"""

    x = self.new_default()
    self.append(x)
    return x


class DescriptorSet(object):
  """
  Represents proto message definitions, where the definitions can span multiple
  files.  (Corresponds to proto2.FileDescriptorSet)

  We allow users to get encoders and decoders separately.  Typically programs
  will encode XOR decode a given message type, not both.
  """

  def __init__(self, desc_dict):
    """
    desc_dict: Dictionary representation of the descriptor
    """
    self.desc_dict = desc_dict
    self.type_index = {}
    self.root = IndexTypes(self.desc_dict, self.type_index)

    # cache of encoders and decoders
    # { ".package.Type" : { "tag bytes" -> <decode function> } ... }
    self.decoders_index = {}
    self.descriptor_index = {}

    self.encoders_index = {}
    self.sizers_index = {}

  def GetDecoder(self, type_name):
    """
    Return a callable that can decode a message.

    This should recursively instantiate (or get memoized) Message types (not
    message instances?).

    decoder.py unfortunately uses class polymorphism for dispatch.  It calls
    value._InternalParse a lot.

    type_name: string "package.Type"
                  Could also be "foo.bar.baz.Type"

    """
    # Populate decoders_index for just the message types needed (transitively)
    # for type_name.
    # TODO: Create a GetAllDecoders() to populate the entire index, so that the
    # object is not immutable and can be used from multiple threads.
    decoders = _MakeDecoders(self.type_index, self.decoders_index, type_name)
    self.decoders_index[type_name] = decoders
    m = _MessageNode(self.decoders_index, type_name)
    # Return decoding function
    return m.decode

  def GetEncoder(self, type_name):
    # Populates self.descriptor_index
    _MakeDescriptors(self.type_index, self.descriptor_index, type_name)

    print 'DESCRIPTORS'
    PrintSubtree(self.descriptor_index)
    print

    descriptors = self.descriptor_index[type_name]
    m = Encoder(descriptors)
    # Return encoding function
    return m.encode

#
# Related to DescriptorSet
#

def IndexEnums(enums, root):
  """Given the enum type information, attach it to the Message class."""
  # Like proto2, we ignore the enum type name.  All enums values live in the
  # parent namespace.  This prevents the annoyance of long chains of dotted
  # names.
  for enum_type in enums:
    for value in enum_type['value']:
      root[value['name']] = value['number']
      

def IndexMessages(messages, package, name_list, root, type_index):
  """Create a hierarchy of message types, given information from the
  DescriptorSet.
  
  Args:
    messages: A list of dictionaries.  Each should have a 'name' and a list of
       fields.
    package: The proto package.  This is generally irrelevant to the user of the
        API, but still used internally.
    name_list: Stack of names
    root: Dictionary root
    type_index: The message types are registered in this "global" index of types
  """
  for message_data in messages:
    type_name = message_data['name']
    names = name_list + [type_name]  # NOTE: Creating a new list!
    full_name = '.'.join(names)

    fields = message_data['field']

    root[type_name] = message_data

    # Populate the type index owned by an instance of DescriptorSet
    if package:
      key = '.%s.%s' % (package, full_name)
    else:
      key = '.%s' % full_name
    type_index[key] = message_data

    subtypes = message_data.get('nested_type', [])
    # Recursive call with 'message_type' as the new root
    IndexMessages(subtypes, package, names, root, type_index)
    IndexEnums(message_data.get('enum_type', []), root)


def IndexTypes(descriptor_set, type_index):
  """Make a dict of foo.bar.baz.Type -> DescriptorProto

  Args:
    descriptor_set: A JSON-like dictionary representation of the
       FileDescriptorSet.
    type_index: A type index to populate

  Returns:
    A dictionary
  """
  # Flatten the file structure, and look up types by their fully qualified
  # names
  root = {}

  # TODO: reflect the directory structure of 'file'
  for f in descriptor_set['file']:
    package = f.get('package', '')
    if package:
      subtree = {}
      root[package] = subtree
    else:
      subtree = root
    IndexMessages(f['message_type'], package, [], subtree, type_index)
    IndexEnums(f.get('enum_type', []), subtree)

  #print.pprint(pool.keys())
  return root


def _LoadDescriptorProto():
  f = open('data/descriptor.proto.json')
  d = json.load(f)
  f.close()
  return d


descriptor_proto = _LoadDescriptorProto()
print type(descriptor_proto)
print descriptor_proto.keys()


def main(argv):
  type_index = {}
  
  # TODO: I want to load binary descriptors.  So first load the meta descriptor,
  # and then use that to load a adddressbook.desc.encoded.

  f = open('testdata/addressbook/addressbook.desc.json-from-protoc')
  d = json.load(f)
  IndexTypes(d, type_index)
  print 'INDEX', type_index

  type_index = {}
  IndexTypes(descriptor_proto, type_index)
  print 'INDEX', type_index


if __name__ == '__main__':
  try:
    success = main(sys.argv)
    sys.exit(not success)
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
