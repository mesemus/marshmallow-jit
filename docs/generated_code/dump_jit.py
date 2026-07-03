"""Dumps the JIT-generated `_serialize` and `_deserialize` source for a representative
set of marshmallow fields, one `serialize_<type>.py` / `deserialize_<type>.py` file per
field, into this directory.

These are documentation artifacts (referenced from ../generated_code_report.md) meant for
reading, not execution - the generated source references free variables such as `missing`
and `marshmallow` that only exist in the compiled function's own globals (see
PythonCode.compile), so a file here won't import or run standalone.

Two groups of fields are dumped:

  - fields marshmallow-jit has a builtin Inliner for (derived from
    BuiltinSerializationInlinersFactory._inliners_by_type in marshmallow_jit/jit/inliners.py
    - add a new one there and this script picks it up automatically)
  - OTHER_FIELD_FACTORIES below: fields it does *not* have an Inliner for (List, Nested,
    Tuple, Dict, Enum, Method, Function, Constant, Raw). These fall back to calling the
    field's own Field.serialize() directly (SchemaSerializer.generate_fallback) - since
    that fallback doesn't inspect the field type at all, every field in this group
    produces the *same* generated code, differing only in the field-type comment header
    this script adds. That sameness is itself the point: it's what "no Inliner exists
    for this field yet" looks like.

Run with:
    python docs/generated_code/dump_jit.py
"""

import enum
import types
from collections.abc import Callable
from pathlib import Path

from marshmallow import Schema, validate
from marshmallow.fields import (
    IP,
    UUID,
    AwareDateTime,
    Boolean,
    Constant,
    Date,
    DateTime,
    Decimal,
    Dict,
    Email,
    Enum,
    Field,
    Float,
    Function,
    Integer,
    IPInterface,
    IPv4,
    IPv4Interface,
    IPv6,
    IPv6Interface,
    List,
    Method,
    NaiveDateTime,
    Nested,
    Raw,
    Str,
    Time,
    TimeDelta,
    Tuple,
    Url,
)

from marshmallow_jit.jit.inliners.entrypoints import BuiltinSerializationInlinersFactory
from marshmallow_jit.schema import JITSchemaMixin

OUTPUT_DIR = Path(__file__).parent

# Human-friendly file name stems for the known field types - falls back to the class
# name (lowercased) for any field type registered later that isn't listed here.
FRIENDLY_NAMES: dict[type[Field], str] = {
    Str: "str",
    Url: "url",
    Email: "email",
    UUID: "uuid",
    Integer: "integer",
    Float: "float",
    Decimal: "decimal",
    Boolean: "boolean",
    DateTime: "datetime",
    NaiveDateTime: "naive_datetime",
    AwareDateTime: "aware_datetime",
    Time: "time",
    Date: "date",
    TimeDelta: "timedelta",
    IP: "ip",
    IPv4: "ipv4",
    IPv6: "ipv6",
    IPInterface: "ip_interface",
    IPv4Interface: "ipv4_interface",
    IPv6Interface: "ipv6_interface",
    List: "list",
}


class _ExampleEnum(enum.Enum):
    RED = "red"
    GREEN = "green"


class _ExampleNestedSchema(Schema):
    id = Integer()
    name = Str()


def inlined_field_factories() -> list[tuple[str, Callable[[], Field]]]:
    """(id, factory) for every field type marshmallow-jit has a builtin Inliner for."""
    seen: set[type[Field]] = set()
    specs: list[tuple[str, Callable[[], Field]]] = []

    # Fields that need special construction (can't be instantiated with no args)
    special_fields = {
        Enum: lambda: Enum(_ExampleEnum),
        Constant: lambda: Constant("constant-value"),
        Method: lambda: Method(serialize="test_method"),
        Function: lambda: Function(serialize=lambda obj: "func-result"),
        List: lambda: List(Str()),  # List needs an inner field
        Dict: lambda: Dict(keys=Str(), values=Integer()),  # Dict needs key and value fields
        Nested: lambda: Nested(_ExampleNestedSchema),  # Nested needs a schema
    }

    for field_type, _inliner in BuiltinSerializationInlinersFactory._inliners_by_type:
        if field_type in seen:
            continue
        seen.add(field_type)

        field_id = FRIENDLY_NAMES.get(field_type, field_type.__name__.lower())
        # Use special factory if defined, otherwise use the class itself (which works for
        # most fields that can be instantiated with no arguments)
        factory = special_fields.get(field_type, field_type)
        specs.append((field_id, factory))
    return specs


# Fields marshmallow-jit does *not* have a builtin Inliner for (yet) - see the module
# docstring for why they all produce identical generated code.
OTHER_FIELD_FACTORIES: list[tuple[str, Callable[[], Field]]] = [
    # Note: Raw, Constant, Method, Function, Enum, and List now have builtin Inliners,
    # so they are handled by inlined_field_factories()
    ("dict", lambda: Dict(keys=Str(), values=Integer())),
    ("tuple", lambda: Tuple((Str(), Integer()))),
    ("nested", lambda: Nested(_ExampleNestedSchema)),
]


def all_field_factories() -> list[tuple[str, Callable[[], Field]]]:
    return inlined_field_factories() + OTHER_FIELD_FACTORIES


def all_field_factories_with_list_variants() -> list[tuple[str, Callable[[], Field]]]:
    """All field factories including special List variants (list of primitives and list of nested)."""
    factories = inlined_field_factories() + OTHER_FIELD_FACTORIES

    # Add list of nested schema variant
    def list_of_nested_factory():
        return List(Nested(_ExampleNestedSchema))

    factories.append(("list_nested", list_of_nested_factory))
    return factories


def build_schema(factory: Callable[[], Field]) -> type[Schema]:
    """A minimal single-field "mapping" schema for a field built by `factory`, with the
    JIT mixin applied."""
    field = factory()
    namespace: dict = {
        "a": field,
        "Meta": type("Meta", (), {"jit_options": {"serializer": "mapping"}}),
    }

    # For Method fields, we need to add the referenced method to the schema
    if isinstance(field, Method) and field.serialize_method_name:
        method_name = field.serialize_method_name
        # Add a dummy method that returns a constant value
        namespace[method_name] = lambda self, obj: "method-result"

    class_name = f"Serialize{field.__class__.__name__}Schema"
    return types.new_class(class_name, (JITSchemaMixin, Schema), exec_body=lambda ns: ns.update(namespace))


def build_schema_with_validators(factory: Callable[[], Field], validators: list) -> type[Schema]:
    """A minimal single-field schema with validators added, with the JIT mixin applied."""
    field = factory()
    # Add validators to the field
    field.validators = tuple(validators)
    namespace: dict = {
        "a": field,
        "Meta": type("Meta", (), {"jit_options": {"serializer": "mapping"}}),
    }

    class_name = f"Serialize{field.__class__.__name__}WithValidatorsSchema"
    return types.new_class(class_name, (JITSchemaMixin, Schema), exec_body=lambda ns: ns.update(namespace))


def generated_source(factory: Callable[[], Field], serialize: bool = True) -> str:
    schema_class = build_schema(factory)
    field = schema_class._declared_fields["a"]
    schema = schema_class()
    if serialize:
        source = schema._serialize.__source__  # ty: ignore[unresolved-attribute]
        return f"# marshmallow.fields.{field.__class__.__name__}\n{source}"
    else:
        source = schema._deserialize.__source__  # ty: ignore[unresolved-attribute]
        return f"# marshmallow.fields.{field.__class__.__name__}\n{source}"


def generated_source_with_validators(factory: Callable[[], Field], validators: list, serialize: bool = True) -> str:
    schema_class = build_schema_with_validators(factory, validators)
    field = schema_class._declared_fields["a"]
    schema = schema_class()
    if serialize:
        source = schema._serialize.__source__  # ty: ignore[unresolved-attribute]
        return f"# marshmallow.fields.{field.__class__.__name__} with validators\n{source}"
    else:
        source = schema._deserialize.__source__  # ty: ignore[unresolved-attribute]
        return f"# marshmallow.fields.{field.__class__.__name__} with validators\n{source}"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate standard serialization files (including list of primitives via inlined_field_factories)
    for field_id, factory in all_field_factories():
        path = OUTPUT_DIR / f"serialize_{field_id}.py"
        path.write_text(generated_source(factory, serialize=True) + "\n")
        print(f"wrote {path}")

    # Generate standard deserialization files
    for field_id, factory in all_field_factories():
        path = OUTPUT_DIR / f"deserialize_{field_id}.py"
        path.write_text(generated_source(factory, serialize=False) + "\n")
        print(f"wrote {path}")

    # Generate special List variant files - serialization
    # List of nested schemas
    list_nested_path = OUTPUT_DIR / "serialize_list_nested.py"
    list_nested_path.write_text(generated_source(lambda: List(Nested(_ExampleNestedSchema)), serialize=True) + "\n")
    print(f"wrote {list_nested_path}")

    # List of lists of strings
    list_of_lists_path = OUTPUT_DIR / "serialize_list_of_lists.py"
    list_of_lists_path.write_text(generated_source(lambda: List(List(Str())), serialize=True) + "\n")
    print(f"wrote {list_of_lists_path}")

    # Dict with List values
    dict_with_list_path = OUTPUT_DIR / "serialize_dict_with_list.py"
    dict_with_list_path.write_text(
        generated_source(lambda: Dict(keys=Str(), values=List(Str())), serialize=True) + "\n"
    )
    print(f"wrote {dict_with_list_path}")

    # Generate special List variant files - deserialization
    # List of nested schemas
    list_nested_deser_path = OUTPUT_DIR / "deserialize_list_nested.py"
    list_nested_deser_path.write_text(
        generated_source(lambda: List(Nested(_ExampleNestedSchema)), serialize=False) + "\n"
    )
    print(f"wrote {list_nested_deser_path}")

    # List of lists of strings
    list_of_lists_deser_path = OUTPUT_DIR / "deserialize_list_of_lists.py"
    list_of_lists_deser_path.write_text(generated_source(lambda: List(List(Str())), serialize=False) + "\n")
    print(f"wrote {list_of_lists_deser_path}")

    # Dict with List values
    dict_with_list_deser_path = OUTPUT_DIR / "deserialize_dict_with_list.py"
    dict_with_list_deser_path.write_text(
        generated_source(lambda: Dict(keys=Str(), values=List(Str())), serialize=False) + "\n"
    )
    print(f"wrote {dict_with_list_deser_path}")

    # Generate validator examples - deserialization
    # String with Length validator
    str_validators = [validate.Length(min=1, max=100)]
    str_validator_path = OUTPUT_DIR / "deserialize_str_with_validators.py"
    str_validator_path.write_text(
        generated_source_with_validators(lambda: Str(), str_validators, serialize=False) + "\n"
    )
    print(f"wrote {str_validator_path}")

    # Integer with Range validator
    int_validators = [validate.Range(min=0, max=100)]
    int_validator_path = OUTPUT_DIR / "deserialize_int_with_validators.py"
    int_validator_path.write_text(
        generated_source_with_validators(lambda: Integer(), int_validators, serialize=False) + "\n"
    )
    print(f"wrote {int_validator_path}")

    # String with Multiple validators (Length + OneOf)
    multi_validators = [validate.Length(min=2, max=50), validate.OneOf(["alice", "bob", "charlie"])]
    multi_validator_path = OUTPUT_DIR / "deserialize_str_multi_validators.py"
    multi_validator_path.write_text(
        generated_source_with_validators(lambda: Str(), multi_validators, serialize=False) + "\n"
    )
    print(f"wrote {multi_validator_path}")

    # Email field (has built-in Email validator)
    email_validator_path = OUTPUT_DIR / "deserialize_email_with_validator.py"
    email_validator_path.write_text(generated_source(lambda: Email(), serialize=False) + "\n")
    print(f"wrote {email_validator_path}")


if __name__ == "__main__":
    main()
