"""
pyb -- A minimal, dynamic, pure Python implementation of Protocol Buffers

What does this mean?

  * minimal: Aiming for 1000-1500 total lines of Python.  Less code is faster
    code, especially in Python.
  * dynamic: no code generation, no build step
  * pure Python: usable without compiling any dependencies; usable in
    restricted environments like App Engine

  Protocol Buffers typically work by generating code ("bindings") from the type
  definitions in your .proto file.  This is appropriate in C++, Java, and
  statically-typed languages in general, but it goes against the grain of
  Python.

  Code generation gets you two things in C++/Java/etc.:

    - Speed.  A field lookup is a matter of adding an offset to a base pointer,
      rather than a string lookup (e.g. as implemented by hash table)
    - Type safety.  You can get type errors at compile time, e.g. if you try to
      set a boolean field to a floating point value.

  Neither of these apply in Python:

    - No matter what, a field lookup (foo.bar) will involve a dictionary
      lookup in Python, because the name is resolved at runtime.
    - You only get type errors at runtime in Python.

Message API
-----------

  The API is simpler than the C++ API by design, just as Python itself is
  simpler than C++.  It doesn't have every knob under the sun.

  That said, *earlier* runtime errors are better than later ones.  Here are
  cases we want to make safer:

    person.invalid_field_name = 3

    --> This should raise AttributeError immediately, rather than waiting for
    the message to be encoded.

    person.enum_type = "MOBILE"
    person.enum_type = Person.MOBILE

    --> The latter is preferable because it will catch invalid values earlier.

  Other choices:

    message.foo              get attribute 'foo'
    message.foo = 3          set attribute 'foo'
    'foo' in message         test for the presence of an attribute
                             (rather than message.HasField('foo'), or
                             message.has_foo() )
    del message.foo          Remove the attribute foo, rather than
                             message.ClearField('foo') or message.clear_foo()

  Construction:

    number = PhoneNumber(number='609-555-1234', phone_type=PhoneType.MOBILE)])
    p = Person(name='Andy', phone=[number])

    This allows you to write nested "protobuf literals" without a series of
    assignment statements (proto2 doesn't seem to allow this).

  Deserialization:
    An unnamed argument is assumed to be a byte string:

      number = PhoneNumber('\\x12\\34')

    Or use "Construction method" style:

      number = PhoneNumber.FromBytes('\\x12\\34')

  Serialization:
    number.ToBytes()

  Value Semantics
  ---------------

  TODO: If we want lazy decoding, then Message objects should be immutable.
  This simplifies things a lot and is more Pythonic.

  That means, no "MergeFrom".  No CopyFrom either -- use constructors.

  "Introspection" (TODO)
  ---------------

  These don't have to be particularly speed-optimized.

  Iteration:
    for name, value in number.items():  # Python 3 syntax, an iterator
      ...
    for name in number.names():
    for value in number.values():

  Visitor?

TODO
----

  - __eq__ on Message objects.
  - Use copy() or deepcopy() on Messages?

  - Name conflict avoidance: e.g. 'yield_' for 'yield'

  - Make sure you don't encode default values

  - Encoding.  This gets complicated because when doing non-trivial
    transformations, the schema may change too.  Might not be so appropriate for
    this type of library.

  - Figure out foreign messages, extensions, etc.
  - Packed repeated fields

  - Profile with and without __slots__

  - Be more flexible about loading descriptors.  Hook this up to a "global db"
    of types, which is the alternative to build-time generation.

  - Measure speed.  There are a couple of benchmarks out there.
    - built in protobuf
    - experimental

  - More testing of edge cases.

To Document
-----------

  - "Build" process
  - Embed descriptors as JSON
    - NOTE: The names of the fields in descriptor.proto can change.  So it
      might not be wise to embed descriptor.desc.json -- maybe
      descriptor.desc.encoded is better.

Incompatibilities with proto2
-----------------------------

  - import generated code vs. making types from a DescriptorSet

  - 'email' in message vs message.HasField('email')
    - TODO: could implement HasField, not a huge deal

  - del message.bar vs. message.ClearField('bar')
    - Also could do this, not a big deal

  - TODO: HasExtension, ClearExtension
"""

from pyb import *
