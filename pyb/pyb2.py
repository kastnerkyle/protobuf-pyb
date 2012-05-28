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

Then we get the top level one, and call


# Dynamic bootstrapping, done at startup

descriptor_proto = json.load("the meta descriptor as JSON")

meta_desc_set = MakeTypes(descriptor_proto, type_index)

# This is done per message

address_book_desc_bytes = <Load binary descriptor addressbook.desc.encoded>
# decode raw data; FileDescriptorSet is equivalent of the proto file
address_book_proto = meta_desc_set.decode("google.protobuf.FileDescriptorSet",
                                          address_book_desc_bytes)
# Now create encoders and decoders?
address_book_desc = MakeTypes(address_book_proto, type_index)


address_book_bytes = <Load binary descriptor addressbook.desc.encoded>

dict = address_book_desc.decode("address_book.AddressBook, address_book_bytes)



You may only need to encode XOR decode a given message type.

So how about:

# create an object from the data
address_book_desc = DescriptorSet(address_book_proto, type_index)
# get an coder
address_book_e = address_book_desc.GetEncoder("address_book.AddressBook")
address_book_d = address_book_desc.GetDecoder("address_book.AddressBook")

<byte string> = address_book_e.encode({ person: ... })
{ person: ... } = address_book_e.dcode(<byte string>)


from python_message.py:


Encoding loop:

  def _IsPresent(item):
    "Given a (FieldDescriptor, value) tuple from _fields, return true if the
    value should be included in the list returned by ListFields()."

    if item[0].label == _FieldDescriptor.LABEL_REPEATED:
      return bool(item[1])
    elif item[0].cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      return item[1]._is_present_in_parent
    else:
      return True

  def ListFields(self):
    all_fields = [item for item in self._fields.iteritems() if _IsPresent(item)]
    all_fields.sort(key = lambda item: item[0].number)
    return all_fields

  def InternalSerialize(self, write_bytes):
    for field_descriptor, field_value in self.ListFields():
      field_descriptor._encoder(write_bytes, field_value)


Decoding loop:

  local_ReadTag = decoder.ReadTag
  local_SkipField = decoder.SkipField

  # NOTE: These are the objects in decoder.py wrapped in _SimpleDecoder.
  decoders_by_tag = cls._decoders_by_tag

  def InternalParse(self, buffer, pos, end):
    self._Modified()
    field_dict = self._fields
    while pos != end:
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
import type_checkers
print type_checkers


class Error(Exception):
  pass


# REFERENCE CODE FROM PROTO2


def _DefaultValueConstructorForField(field):
  """Returns a function which returns a default value for a field.

  Args:
    field: FieldDescriptor object for this field.

  The returned function has one argument:
    message: Message instance containing this field, or a weakref proxy
      of same.

  That function in turn returns a default value for this field.  The default
    value may refer back to |message| via a weak reference.
  """

  if field.label == _FieldDescriptor.LABEL_REPEATED:
    if field.default_value != []:
      raise ValueError('Repeated field default value not empty list: %s' % (
          field.default_value))
    if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      # We can't look at _concrete_class yet since it might not have
      # been set.  (Depends on order in which we initialize the classes).
      message_type = field.message_type
      def MakeRepeatedMessageDefault(message):
        return containers.RepeatedCompositeFieldContainer(
            message._listener_for_children, field.message_type)
      return MakeRepeatedMessageDefault
    else:
      type_checker = type_checkers.GetTypeChecker(field.cpp_type, field.type)
      def MakeRepeatedScalarDefault(message):
        return containers.RepeatedScalarFieldContainer(
            message._listener_for_children, type_checker)
      return MakeRepeatedScalarDefault

  if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
    # _concrete_class may not yet be initialized.
    message_type = field.message_type
    def MakeSubMessageDefault(message):
      result = message_type._concrete_class()
      result._SetListener(message._listener_for_children)
      return result
    return MakeSubMessageDefault

  def MakeScalarDefault(message):
    return field.default_value
  return MakeScalarDefault


def _IsMessageSetExtension(field):
  return (field.is_extension and
          field.containing_type.has_options and
          field.containing_type.GetOptions().message_set_wire_format and
          field.type == _FieldDescriptor.TYPE_MESSAGE and
          field.message_type == field.extension_scope and
          field.label == _FieldDescriptor.LABEL_OPTIONAL)


def _AttachFieldHelpers(cls, field_descriptor):
  is_repeated = (field_descriptor.label == _FieldDescriptor.LABEL_REPEATED)
  is_packed = (field_descriptor.has_options and
               field_descriptor.GetOptions().packed)

  if _IsMessageSetExtension(field_descriptor):
    field_encoder = encoder.MessageSetItemEncoder(field_descriptor.number)
    sizer = encoder.MessageSetItemSizer(field_descriptor.number)
  else:
    field_encoder = type_checkers.TYPE_TO_ENCODER[field_descriptor.type](
        field_descriptor.number, is_repeated, is_packed)
    sizer = type_checkers.TYPE_TO_SIZER[field_descriptor.type](
        field_descriptor.number, is_repeated, is_packed)

  field_descriptor._encoder = field_encoder
  field_descriptor._sizer = sizer
  field_descriptor._default_constructor = _DefaultValueConstructorForField(
      field_descriptor)

  def AddDecoder(wiretype, is_packed):
    tag_bytes = encoder.TagBytes(field_descriptor.number, wiretype)
    cls._decoders_by_tag[tag_bytes] = (
        type_checkers.TYPE_TO_DECODER[field_descriptor.type](
            field_descriptor.number, is_repeated, is_packed,
            field_descriptor, field_descriptor._default_constructor))

  AddDecoder(type_checkers.FIELD_TYPE_TO_WIRE_TYPE[field_descriptor.type],
             False)

  if is_repeated and wire_format.IsTypePackable(field_descriptor.type):
    # To support wire compatibility of adding packed = true, add a decoder for
    # packed values regardless of the field's options.
    AddDecoder(wire_format.WIRETYPE_LENGTH_DELIMITED, True)

# END


def PrintSubtree(subtree, indent=0):
  if not isinstance(subtree, dict):
    return
  names = sorted(subtree)
  for name in names:
    print ' ' * indent + name
    PrintSubtree(subtree[name], indent+2)


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

  The decoder has a reference to new_default, which creates _FakeMessage which
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
    # TODO: document thread safety -- mutating decoders_index here
    if type_name not in decoders_index:
      # mark visited BEFORE recursive call, preventing infinite recursion
      decoders_index[type_name] = True
      decoders = _MakeDecoders(type_index, decoders_index, type_name)
      decoders_index[type_name] = decoders

    # TODO: How to end recursive types?  DescriptorProto contains
    # DescriptorProto (nested_type).

    #print '----'
    #pprint(decoders_index)
    #print '----'
    #sys.stdin.readline()

    if is_repeated:
      return lambda m: _FakeCompositeList(decoders_index, type_name)
    else:
      return lambda m: _FakeMessage(decoders_index, type_name)

  else:  # scalar
    if is_repeated:
      return lambda m: _FakeScalarList(lambda: field['default_value'])
    else:
      return lambda m: field['default_value']


def _MakeDecoders(type_index, decoders_index, type_name):
  """
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
    print f

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


class _FakeMessage(object):
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
    return MakeDict(self)


def MakeDict(node):
  """
  message
  """
  if isinstance(node, _FakeMessage):
    result = {}
    for k, v in node.field_dict.iteritems():
      result[k] = MakeDict(v)
    return result
  elif isinstance(node, list):
    result = []
    for item in node:
      result.append(MakeDict(item))
    return result
  else:
    return node


class _FakeCompositeList(list):

  def __init__(self, decoders_index, type_name):
    self.decoders_index = decoders_index
    self.type_name = type_name

  def add(self):
    """Return a new value of the given type.  Add it to the end of the list"""

    # ARGH, this might not be a message.
    x = _FakeMessage(self.decoders_index, self.type_name)
    self.append(x)
    return x


class _FakeScalarList(list):

  def __init__(self, new_default):
    self.new_default = new_default

  def add(self):
    """Return a new value of the given type.  Add it to the end of the list"""

    x = self.new_default()
    self.append(x)
    return x


class DescriptorSet(object):
  """
  Represents proto message definitions, where the definitions can span.
  """

  def __init__(self, desc_dict):
    """
    desc_dict: Dictinoary representation of the descriptor
    """
    self.desc_dict = desc_dict
    self.type_index = {}
    self.root = IndexTypes(self.desc_dict, self.type_index)

    # cache of encoders and decoders
    # { ".package.Type" : { "tag bytes" -> <decode function> } ... }
    self.decoders_index = {}
    self.encoders_index = {}

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
    m = _FakeMessage(self.decoders_index, type_name)
    # Return decoding function
    return m.decode

  def GetEncoder(self, type_name):
    pass


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
