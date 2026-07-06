"""Integration tests to improve code coverage.

These tests use real-world scenarios to exercise various code paths.
All tests compare JIT behavior with plain marshmallow to ensure exact equivalence.
"""

import ipaddress
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, override

import pytest
from marshmallow import Schema, ValidationError, fields, post_dump, post_load, pre_load

from marshmallow_jit.schema import JITSchemaMixin, jit_schema


def compare_results(jit_result: Any, plain_result: Any, test_name: str) -> None:
    """Helper to compare JIT and plain marshmallow results."""
    assert jit_result == plain_result, (
        f"{test_name}: JIT result differs from plain marshmallow\nJIT: {jit_result}\nPlain: {plain_result}"
    )


def compare_errors(jit_error: ValidationError, plain_error: ValidationError, test_name: str) -> None:
    """Helper to compare JIT and plain marshmallow validation errors."""
    assert jit_error.messages == plain_error.messages, (
        f"{test_name}: JIT error messages differ from plain marshmallow\n"
        f"JIT: {jit_error.messages}\n"
        f"Plain: {plain_error.messages}"
    )


class TestMultiSerializerDispatch:
    """Test predicate-based dispatcher with multiple serializers."""

    def test_hybrid_serializer_with_dict_and_object(self) -> None:
        """Test hybrid serializer handling both dicts and objects."""

        @dataclass
        class Person:
            name: str
            age: int

        class PersonSchema(Schema):
            name = fields.Str()
            age = fields.Int()

        # Plain marshmallow
        plain_schema = PersonSchema()
        plain_dict_result = plain_schema.dump({"name": "Alice", "age": 30})
        plain_obj_result = plain_schema.dump(Person(name="Bob", age=25))

        # JIT with hybrid serializer
        @jit_schema
        class PersonSchemaJIT(Schema):
            class Meta:
                jit_options = {
                    "serializer": "hybrid",
                }

            name = fields.Str()
            age = fields.Int()

        jit_schema_instance = PersonSchemaJIT()

        # Test with dict
        jit_dict_result = jit_schema_instance.dump({"name": "Alice", "age": 30})
        compare_results(jit_dict_result, plain_dict_result, "hybrid dict")

        # Test with object
        jit_obj_result = jit_schema_instance.dump(Person(name="Bob", age=25))
        compare_results(jit_obj_result, plain_obj_result, "hybrid object")

    def test_multi_serializer_with_predicates(self) -> None:
        """Test multi-serializer configuration with predicate functions."""

        @dataclass
        class User:
            username: str
            email: str

        def is_dict(obj: Any) -> bool:
            return isinstance(obj, dict)

        def is_user_obj(obj: Any) -> bool:
            return isinstance(obj, User)

        # Plain marshmallow
        class FlexibleSchemaPlain(Schema):
            username = fields.Str()
            email = fields.Email()

        plain_schema = FlexibleSchemaPlain()
        plain_dict_result = plain_schema.dump({"username": "alice", "email": "alice@example.com"})
        plain_obj_result = plain_schema.dump(User(username="bob", email="bob@example.com"))

        # JIT with predicates
        @jit_schema
        class FlexibleSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": [
                        (is_dict, "mapping"),
                        (is_user_obj, "instance"),
                    ]
                }

            username = fields.Str()
            email = fields.Email()

        jit_schema_instance = FlexibleSchema()

        # Test with dict
        jit_dict_result = jit_schema_instance.dump({"username": "alice", "email": "alice@example.com"})
        compare_results(jit_dict_result, plain_dict_result, "predicate dict")

        # Test with object
        jit_obj_result = jit_schema_instance.dump(User(username="bob", email="bob@example.com"))
        compare_results(jit_obj_result, plain_obj_result, "predicate object")

    def test_multi_serializer_with_fallback(self) -> None:
        """Test multi-serializer with True as fallback predicate."""

        @dataclass
        class Item:
            name: str

        # Plain marshmallow
        class ItemSchemaPlain(Schema):
            name = fields.Str()

        plain_schema = ItemSchemaPlain()
        plain_dict_result = plain_schema.dump({"name": "Item1"})
        plain_obj_result = plain_schema.dump(Item(name="Item2"))

        # JIT with fallback
        @jit_schema
        class ItemSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": [
                        (lambda x: isinstance(x, dict), "mapping"),
                        (True, "instance"),  # Fallback
                    ]
                }

            name = fields.Str()

        jit_schema_instance = ItemSchema()

        # Test with dict
        jit_dict_result = jit_schema_instance.dump({"name": "Item1"})
        compare_results(jit_dict_result, plain_dict_result, "fallback dict")

        # Test with object
        jit_obj_result = jit_schema_instance.dump(Item(name="Item2"))
        compare_results(jit_obj_result, plain_obj_result, "fallback object")

    def test_dispatcher_no_match_raises_error(self) -> None:
        """Test that dispatcher raises error when no predicate matches."""

        @dataclass
        class User:
            username: str

        @dataclass
        class Admin:
            adminname: str

        @dataclass
        class Product:  # Type not covered by any predicate
            name: str

        def is_user(obj: Any) -> bool:
            return isinstance(obj, User)

        def is_admin(obj: Any) -> bool:
            return isinstance(obj, Admin)

        # JIT with narrow predicates (only User and Admin, no fallback for Product)
        @jit_schema
        class NarrowSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": [
                        (is_user, "instance"),
                        (is_admin, "instance"),
                        # No fallback - Product won't match either predicate
                    ]
                }

            name = fields.Str(attribute="username", dump_default="unknown")

        jit_schema_instance = NarrowSchema()

        # Test that User works
        user_result = jit_schema_instance.dump(User(username="alice"))
        assert user_result == {"name": "alice"}

        # Test that Admin works
        admin_result = jit_schema_instance.dump(Admin(adminname="bob"))
        assert admin_result == {"name": "unknown"}  # dump_default used since adminname != username

        # Test that Product raises ValueError
        # Note: We expect ValueError from the dispatcher when no predicate matches
        with pytest.raises(ValueError, match="No method matches object"):
            jit_schema_instance.dump(Product(name="Widget"))


class TestIPFieldCoverage:
    """Test IP address fields with exploded/compressed options."""

    def test_ip_field_exploded_serialization(self) -> None:
        """Test IP field serialization with exploded format."""

        # Plain marshmallow
        class NetworkSchemaPlain(Schema):
            ipv6 = fields.IPv6(exploded=True)

        plain_schema = NetworkSchemaPlain()
        plain_result = plain_schema.dump({"ipv6": ipaddress.IPv6Address("::1")})

        # JIT
        @jit_schema
        class NetworkSchema(Schema):
            ipv6 = fields.IPv6(exploded=True)

        jit_schema_instance = NetworkSchema()
        jit_result = jit_schema_instance.dump({"ipv6": ipaddress.IPv6Address("::1")})

        compare_results(jit_result, plain_result, "IPv6 exploded")

    def test_ip_field_compressed_serialization(self) -> None:
        """Test IP field serialization with compressed format (default)."""

        # Plain marshmallow
        class NetworkSchemaPlain(Schema):
            ipv6 = fields.IPv6(exploded=False)

        plain_schema = NetworkSchemaPlain()
        plain_result = plain_schema.dump({"ipv6": ipaddress.IPv6Address("2001:0db8::1")})

        # JIT
        @jit_schema
        class NetworkSchema(Schema):
            ipv6 = fields.IPv6(exploded=False)

        jit_schema_instance = NetworkSchema()
        jit_result = jit_schema_instance.dump({"ipv6": ipaddress.IPv6Address("2001:0db8::1")})

        compare_results(jit_result, plain_result, "IPv6 compressed")

    def test_ip_interface_field_exploded(self) -> None:
        """Test IP interface field with exploded format."""

        # Plain marshmallow
        class InterfaceSchemaPlain(Schema):
            iface = fields.IPv6Interface(exploded=True)

        plain_schema = InterfaceSchemaPlain()
        plain_result = plain_schema.dump({"iface": ipaddress.IPv6Interface("::1/128")})

        # JIT
        @jit_schema
        class InterfaceSchema(Schema):
            iface = fields.IPv6Interface(exploded=True)

        jit_schema_instance = InterfaceSchema()
        jit_result = jit_schema_instance.dump({"iface": ipaddress.IPv6Interface("::1/128")})

        compare_results(jit_result, plain_result, "IPv6Interface exploded")


class TestCustomValidationAndProperties:
    """Test custom field validation and property overrides."""

    def test_field_with_custom_validate_method(self) -> None:
        """Test field with overridden _validate method."""

        class CustomIntField(fields.Int):
            @override
            def _validate(self, value: Any) -> None:
                super()._validate(value)
                if value < 0:
                    raise ValidationError("Must be non-negative")

        # Plain marshmallow
        class PositiveSchemaPlain(Schema):
            count = CustomIntField()

        plain_schema = PositiveSchemaPlain()
        plain_valid = plain_schema.load({"count": 10})

        # JIT
        @jit_schema
        class PositiveSchema(Schema):
            count = CustomIntField()

        jit_schema_instance = PositiveSchema()
        jit_valid = jit_schema_instance.load({"count": 10})

        compare_results(jit_valid, plain_valid, "custom validate valid")

        # Test invalid value
        plain_error = None
        jit_error = None

        try:
            plain_schema.load({"count": -5})
        except ValidationError as e:
            plain_error = e

        try:
            jit_schema_instance.load({"count": -5})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "custom validate invalid")

    def test_field_with_validators_list(self) -> None:
        """Test field with validators in the validators list."""
        from marshmallow.validate import Length

        # Plain marshmallow
        class ValidatedSchemaPlain(Schema):
            name = fields.Str(validate=[Length(min=3, max=20)])

        plain_schema = ValidatedSchemaPlain()
        plain_valid = plain_schema.load({"name": "Alice"})

        # JIT
        @jit_schema
        class ValidatedSchema(Schema):
            name = fields.Str(validate=[Length(min=3, max=20)])

        jit_schema_instance = ValidatedSchema()
        jit_valid = jit_schema_instance.load({"name": "Alice"})

        compare_results(jit_valid, plain_valid, "validators list valid")

        # Test too short
        plain_error = None
        jit_error = None

        try:
            plain_schema.load({"name": "Al"})
        except ValidationError as e:
            plain_error = e

        try:
            jit_schema_instance.load({"name": "Al"})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "validators list too short")

    def test_method_field_serialization_and_deserialization(self) -> None:
        """Test Method field for both directions."""

        # Plain marshmallow
        class UserSchemaPlain(Schema):
            name = fields.Str()
            name_upper = fields.Method("get_name_upper", deserialize="load_name_upper")

            def get_name_upper(self, obj: dict[str, Any]) -> str:
                return obj["name"].upper()

            def load_name_upper(self, value: str) -> str:
                return value.lower()

        plain_schema = UserSchemaPlain()
        plain_dump = plain_schema.dump({"name": "alice"})
        plain_load = plain_schema.load({"name": "ignore", "name_upper": "BOB"})

        # JIT
        @jit_schema
        class UserSchema(Schema):
            name = fields.Str()
            name_upper = fields.Method("get_name_upper", deserialize="load_name_upper")

            def get_name_upper(self, obj: dict[str, Any]) -> str:
                return obj["name"].upper()

            def load_name_upper(self, value: str) -> str:
                return value.lower()

        jit_schema_instance = UserSchema()
        jit_dump = jit_schema_instance.dump({"name": "alice"})
        jit_load = jit_schema_instance.load({"name": "ignore", "name_upper": "BOB"})

        compare_results(jit_dump, plain_dump, "method field dump")
        compare_results(jit_load, plain_load, "method field load")

    def test_function_field_with_custom_functions(self) -> None:
        """Test Function field with serialize/deserialize functions."""

        def get_doubled(obj: dict[str, Any]) -> int:
            return obj.get("doubled", 0) * 2

        def set_halved(value: int) -> int:
            return value // 2

        # Plain marshmallow
        class MathSchemaPlain(Schema):
            original = fields.Int()
            doubled = fields.Function(serialize=get_doubled, deserialize=set_halved)

        plain_schema = MathSchemaPlain()
        plain_dump = plain_schema.dump({"original": 5, "doubled": 10})
        plain_load = plain_schema.load({"original": 5, "doubled": 20})

        # JIT
        @jit_schema
        class MathSchema(Schema):
            original = fields.Int()
            doubled = fields.Function(serialize=get_doubled, deserialize=set_halved)

        jit_schema_instance = MathSchema()
        jit_dump = jit_schema_instance.dump({"original": 5, "doubled": 10})
        jit_load = jit_schema_instance.load({"original": 5, "doubled": 20})

        compare_results(jit_dump, plain_dump, "function field dump")
        compare_results(jit_load, plain_load, "function field load")


class TestHybridAccessor:
    """Test hybrid accessor for dict/object access."""

    def test_hybrid_accessor_with_nested_attributes(self) -> None:
        """Test hybrid accessor with dotted attribute names."""

        @dataclass
        class Address:
            street: str
            city: str

        @dataclass
        class Person:
            name: str
            address: Address

        # Plain marshmallow
        class PersonSchemaPlain(Schema):
            name = fields.Str()
            street = fields.Str(attribute="address.street")
            city = fields.Str(attribute="address.city")

        plain_schema = PersonSchemaPlain()
        person = Person(name="Alice", address=Address(street="Main St", city="NYC"))
        plain_result = plain_schema.dump(person)

        # JIT
        @jit_schema
        class PersonSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": "hybrid",
                }

            name = fields.Str()
            street = fields.Str(attribute="address.street")
            city = fields.Str(attribute="address.city")

        jit_schema_instance = PersonSchema()
        jit_result = jit_schema_instance.dump(person)

        compare_results(jit_result, plain_result, "hybrid nested attributes")


class TestInstanceAccessor:
    """Test instance accessor for object serialization."""

    def test_instance_accessor_with_nested_objects(self) -> None:
        """Test instance accessor with nested object attributes."""

        @dataclass
        class Company:
            name: str

        @dataclass
        class Employee:
            name: str
            company: Company

        # Plain marshmallow
        class EmployeeSchemaPlain(Schema):
            name = fields.Str()
            company_name = fields.Str(attribute="company.name")

        plain_schema = EmployeeSchemaPlain()
        emp = Employee(name="Bob", company=Company(name="TechCorp"))
        plain_result = plain_schema.dump(emp)

        # JIT
        @jit_schema
        class EmployeeSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": "instance",
                }

            name = fields.Str()
            company_name = fields.Str(attribute="company.name")

        jit_schema_instance = EmployeeSchema()
        jit_result = jit_schema_instance.dump(emp)

        compare_results(jit_result, plain_result, "instance nested objects")

    def test_instance_accessor_serializes_successfully(self) -> None:
        """Test instance accessor with various attribute access patterns."""

        @dataclass
        class Employee:
            name: str
            salary: float

        # Plain marshmallow
        class EmployeeSchemaPlain(Schema):
            name = fields.Str()
            salary = fields.Float()

        plain_schema = EmployeeSchemaPlain()
        emp = Employee(name="Charlie", salary=50000.0)
        plain_result = plain_schema.dump(emp)

        # JIT
        @jit_schema
        class EmployeeSchema(Schema):
            class Meta:
                jit_options = {
                    "serializer": "instance",
                }

            name = fields.Str()
            salary = fields.Float()

        jit_schema_instance = EmployeeSchema()
        jit_result = jit_schema_instance.dump(emp)

        compare_results(jit_result, plain_result, "instance accessor")


class TestDictAccessorEdgeCases:
    """Test dict accessor edge cases."""

    def test_dict_accessor_with_load_default(self) -> None:
        """Test dict accessor with missing keys and load_default."""

        # Plain marshmallow
        class ConfigSchemaPlain(Schema):
            required_key = fields.Str(required=True)
            optional_key = fields.Str(load_default="default_value")

        plain_schema = ConfigSchemaPlain()
        plain_result = plain_schema.load({"required_key": "value"})

        # JIT
        @jit_schema
        class ConfigSchema(Schema):
            required_key = fields.Str(required=True)
            optional_key = fields.Str(load_default="default_value")

        jit_schema_instance = ConfigSchema()
        jit_result = jit_schema_instance.load({"required_key": "value"})

        compare_results(jit_result, plain_result, "dict accessor load_default")


class TestSchemaHooksIntegration:
    """Test schema processing hooks with JIT compilation."""

    def test_pre_load_hook_modifies_data(self) -> None:
        """Test that pre_load hook is called and modifies data."""

        # Plain marshmallow
        class PreLoadSchemaPlain(Schema):
            name = fields.Str()
            age = fields.Int()

            @pre_load
            def uppercase_name(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data = dict(data)
                data["name"] = data["name"].upper()
                return data

        plain_schema = PreLoadSchemaPlain()
        plain_result = plain_schema.load({"name": "alice", "age": 30})

        # JIT
        @jit_schema
        class PreLoadSchema(Schema):
            name = fields.Str()
            age = fields.Int()

            @pre_load
            def uppercase_name(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data = dict(data)
                data["name"] = data["name"].upper()
                return data

        jit_schema_instance = PreLoadSchema()
        jit_result = jit_schema_instance.load({"name": "alice", "age": 30})

        compare_results(jit_result, plain_result, "pre_load hook")

    def test_post_load_hook_transforms_result(self) -> None:
        """Test that post_load hook is called and transforms result."""

        # Plain marshmallow
        class PostLoadSchemaPlain(Schema):
            first_name = fields.Str()
            last_name = fields.Str()

            @post_load
            def make_full_name(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data["full_name"] = f"{data['first_name']} {data['last_name']}"
                return data

        plain_schema = PostLoadSchemaPlain()
        plain_result = plain_schema.load({"first_name": "John", "last_name": "Doe"})

        # JIT
        @jit_schema
        class PostLoadSchema(Schema):
            first_name = fields.Str()
            last_name = fields.Str()

            @post_load
            def make_full_name(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data["full_name"] = f"{data['first_name']} {data['last_name']}"
                return data

        jit_schema_instance = PostLoadSchema()
        jit_result = jit_schema_instance.load({"first_name": "John", "last_name": "Doe"})

        compare_results(jit_result, plain_result, "post_load hook")

    def test_post_dump_hook_modifies_output(self) -> None:
        """Test that post_dump hook is called and modifies output."""

        # Plain marshmallow
        class PostDumpSchemaPlain(Schema):
            name = fields.Str()
            secret = fields.Str()

            @post_dump
            def remove_secret(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data = dict(data)
                data.pop("secret", None)
                return data

        plain_schema = PostDumpSchemaPlain()
        plain_result = plain_schema.dump({"name": "Alice", "secret": "password123"})

        # JIT
        @jit_schema
        class PostDumpSchema(Schema):
            name = fields.Str()
            secret = fields.Str()

            @post_dump
            def remove_secret(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data = dict(data)
                data.pop("secret", None)
                return data

        jit_schema_instance = PostDumpSchema()
        jit_result = jit_schema_instance.dump({"name": "Alice", "secret": "password123"})

        compare_results(jit_result, plain_result, "post_dump hook")


class TestListFieldEdgeCases:
    """Test List field edge cases and validation."""

    def test_list_field_with_generator_input(self) -> None:
        """Test List field with generator input."""

        def gen() -> Generator[int]:
            yield 1
            yield 2
            yield 3

        # Plain marshmallow
        class StreamSchemaPlain(Schema):
            items = fields.List(fields.Int())

        plain_schema = StreamSchemaPlain()
        plain_result = plain_schema.load({"items": gen()})

        # JIT
        @jit_schema
        class StreamSchema(Schema):
            items = fields.List(fields.Int())

        jit_schema_instance = StreamSchema()

        def gen2() -> Generator[int]:
            yield 1
            yield 2
            yield 3

        jit_result = jit_schema_instance.load({"items": gen2()})

        compare_results(jit_result, plain_result, "list with generator")

    def test_list_field_deserialization_with_tuple_input(self) -> None:
        """Test List field deserialization with tuple input."""

        # Plain marshmallow
        class TupleSchemaPlain(Schema):
            values = fields.List(fields.Str())

        plain_schema = TupleSchemaPlain()
        plain_result = plain_schema.load({"values": ("a", "b", "c")})

        # JIT
        @jit_schema
        class TupleSchema(Schema):
            values = fields.List(fields.Str())

        jit_schema_instance = TupleSchema()
        jit_result = jit_schema_instance.load({"values": ("a", "b", "c")})

        compare_results(jit_result, plain_result, "list with tuple")

    def test_list_field_with_non_collection_raises_error(self) -> None:
        """Test List field with non-collection input raises error."""

        # Plain marshmallow
        class ListSchemaPlain(Schema):
            items = fields.List(fields.Int())

        plain_schema = ListSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({"items": "not a list"})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class ListSchema(Schema):
            items = fields.List(fields.Int())

        jit_schema_instance = ListSchema()
        jit_error = None
        try:
            jit_schema_instance.load({"items": "not a list"})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        assert "items" in jit_error.messages
        assert "items" in plain_error.messages


class TestDictFieldEdgeCases:
    """Test Dict field edge cases."""

    def test_dict_field_with_key_field_serialization(self) -> None:
        """Test Dict field with key_field for key transformation."""

        # Plain marshmallow
        class MappingSchemaPlain(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        plain_schema = MappingSchemaPlain()
        plain_result = plain_schema.dump({"data": {1: "one", 2: "two", 3: "three"}})

        # JIT
        @jit_schema
        class MappingSchema(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        jit_schema_instance = MappingSchema()
        jit_result = jit_schema_instance.dump({"data": {1: "one", 2: "two", 3: "three"}})

        compare_results(jit_result, plain_result, "dict with key field dump")

    def test_dict_field_with_key_field_deserialization(self) -> None:
        """Test Dict field deserialization with key transformation."""

        # Plain marshmallow
        class MappingSchemaPlain(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        plain_schema = MappingSchemaPlain()
        plain_result = plain_schema.load({"data": {"1": "one", "2": "two"}})

        # JIT
        @jit_schema
        class MappingSchema(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        jit_schema_instance = MappingSchema()
        jit_result = jit_schema_instance.load({"data": {"1": "one", "2": "two"}})

        compare_results(jit_result, plain_result, "dict with key field load")

    def test_dict_field_with_invalid_key_raises_error(self) -> None:
        """Test Dict field with invalid key type raises error."""

        # Plain marshmallow
        class StrictMappingSchemaPlain(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        plain_schema = StrictMappingSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({"data": {"invalid": "value"}})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class StrictMappingSchema(Schema):
            data = fields.Dict(keys=fields.Int(), values=fields.Str())

        jit_schema_instance = StrictMappingSchema()
        jit_error = None
        try:
            jit_schema_instance.load({"data": {"invalid": "value"}})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "dict invalid key")

    def test_dict_field_with_non_mapping_raises_error(self) -> None:
        """Test Dict field with non-mapping input raises error."""

        # Plain marshmallow
        class DictSchemaPlain(Schema):
            data = fields.Dict()

        plain_schema = DictSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({"data": "not a dict"})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class DictSchema(Schema):
            data = fields.Dict()

        jit_schema_instance = DictSchema()
        jit_error = None
        try:
            jit_schema_instance.load({"data": "not a dict"})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "dict non-mapping")


class TestBooleanFieldEdgeCases:
    """Test Boolean field edge cases."""

    def test_boolean_field_with_truthy_string_deserialization(self) -> None:
        """Test Boolean field deserialization with truthy strings."""

        # Plain marshmallow
        class FlagSchemaPlain(Schema):
            enabled = fields.Boolean()

        plain_schema = FlagSchemaPlain()
        plain_true = plain_schema.load({"enabled": "true"})
        plain_one = plain_schema.load({"enabled": "1"})
        plain_int_one = plain_schema.load({"enabled": 1})

        # JIT
        @jit_schema
        class FlagSchema(Schema):
            enabled = fields.Boolean()

        jit_schema_instance = FlagSchema()
        jit_true = jit_schema_instance.load({"enabled": "true"})
        jit_one = jit_schema_instance.load({"enabled": "1"})
        jit_int_one = jit_schema_instance.load({"enabled": 1})

        compare_results(jit_true, plain_true, "boolean truthy string 'true'")
        compare_results(jit_one, plain_one, "boolean truthy string '1'")
        compare_results(jit_int_one, plain_int_one, "boolean truthy int 1")

    def test_boolean_field_with_falsy_string_deserialization(self) -> None:
        """Test Boolean field deserialization with falsy strings."""

        # Plain marshmallow
        class FlagSchemaPlain(Schema):
            enabled = fields.Boolean()

        plain_schema = FlagSchemaPlain()
        plain_false = plain_schema.load({"enabled": "false"})
        plain_zero = plain_schema.load({"enabled": "0"})
        plain_int_zero = plain_schema.load({"enabled": 0})

        # JIT
        @jit_schema
        class FlagSchema(Schema):
            enabled = fields.Boolean()

        jit_schema_instance = FlagSchema()
        jit_false = jit_schema_instance.load({"enabled": "false"})
        jit_zero = jit_schema_instance.load({"enabled": "0"})
        jit_int_zero = jit_schema_instance.load({"enabled": 0})

        compare_results(jit_false, plain_false, "boolean falsy string 'false'")
        compare_results(jit_zero, plain_zero, "boolean falsy string '0'")
        compare_results(jit_int_zero, plain_int_zero, "boolean falsy int 0")


class TestDecimalFieldEdgeCases:
    """Test Decimal field edge cases."""

    def test_decimal_field_serialization_and_deserialization(self) -> None:
        """Test Decimal field round-trip."""

        # Plain marshmallow
        class PriceSchemaPlain(Schema):
            amount = fields.Decimal()

        plain_schema = PriceSchemaPlain()
        plain_result = plain_schema.load({"amount": "123.45"})

        # JIT
        @jit_schema
        class PriceSchema(Schema):
            amount = fields.Decimal()

        jit_schema_instance = PriceSchema()
        jit_result = jit_schema_instance.load({"amount": "123.45"})

        compare_results(jit_result, plain_result, "decimal load")

    def test_decimal_field_as_string_serialization(self) -> None:
        """Test Decimal field deserialization validates correctly."""

        # Plain marshmallow
        class PriceSchemaPlain(Schema):
            amount = fields.Decimal()

        plain_schema = PriceSchemaPlain()
        plain_valid = plain_schema.load({"amount": "123.45"})

        # JIT
        @jit_schema
        class PriceSchema(Schema):
            amount = fields.Decimal()

        jit_schema_instance = PriceSchema()
        jit_valid = jit_schema_instance.load({"amount": "123.45"})

        compare_results(jit_valid, plain_valid, "decimal valid")

        # Test invalid
        plain_error = None
        try:
            plain_schema.load({"amount": "not a number"})
        except ValidationError as e:
            plain_error = e

        jit_error = None
        try:
            jit_schema_instance.load({"amount": "not a number"})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "decimal invalid")


class TestFloatFieldEdgeCases:
    """Test Float field edge cases."""

    def test_float_field_serialization(self) -> None:
        """Test Float field serialization."""

        # Plain marshmallow
        class ValueSchemaPlain(Schema):
            num = fields.Float()

        plain_schema = ValueSchemaPlain()
        plain_result = plain_schema.dump({"num": 3.14})

        # JIT
        @jit_schema
        class ValueSchema(Schema):
            num = fields.Float()

        jit_schema_instance = ValueSchema()
        jit_result = jit_schema_instance.dump({"num": 3.14})

        compare_results(jit_result, plain_result, "float dump")

    def test_float_field_deserialization(self) -> None:
        """Test Float field deserialization from string."""

        # Plain marshmallow
        class ValueSchemaPlain(Schema):
            num = fields.Float()

        plain_schema = ValueSchemaPlain()
        plain_result = plain_schema.load({"num": "3.14"})

        # JIT
        @jit_schema
        class ValueSchema(Schema):
            num = fields.Float()

        jit_schema_instance = ValueSchema()
        jit_result = jit_schema_instance.load({"num": "3.14"})

        compare_results(jit_result, plain_result, "float load")


class TestIntegerFieldEdgeCases:
    """Test Integer field edge cases."""

    def test_integer_field_with_strict_mode(self) -> None:
        """Test Integer field with strict=True rejects floats."""

        # Plain marshmallow
        class StrictSchemaPlain(Schema):
            count = fields.Int(strict=True)

        plain_schema = StrictSchemaPlain()
        plain_valid = plain_schema.load({"count": 42})

        # JIT
        @jit_schema
        class StrictSchema(Schema):
            count = fields.Int(strict=True)

        jit_schema_instance = StrictSchema()
        jit_valid = jit_schema_instance.load({"count": 42})

        compare_results(jit_valid, plain_valid, "int strict valid")

        # Float should be rejected in strict mode
        plain_error = None
        try:
            plain_schema.load({"count": 42.0})
        except ValidationError as e:
            plain_error = e

        jit_error = None
        try:
            jit_schema_instance.load({"count": 42.0})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "int strict invalid")

    def test_integer_field_deserialization_from_string(self) -> None:
        """Test Integer field deserialization from string."""

        # Plain marshmallow
        class IntSchemaPlain(Schema):
            value = fields.Int()

        plain_schema = IntSchemaPlain()
        plain_result = plain_schema.load({"value": "42"})

        # JIT
        @jit_schema
        class IntSchema(Schema):
            value = fields.Int()

        jit_schema_instance = IntSchema()
        jit_result = jit_schema_instance.load({"value": "42"})

        compare_results(jit_result, plain_result, "int from string")


class TestNestedSchemaEdgeCases:
    """Test Nested schema edge cases."""

    def test_nested_schema_with_many(self) -> None:
        """Test nested schema with many=True for serialization."""

        # Plain marshmallow
        class ItemSchemaPlain(Schema):
            name = fields.Str()
            price = fields.Float()

        class OrderSchemaPlain(Schema):
            items = fields.Nested(ItemSchemaPlain, many=True)

        plain_schema = OrderSchemaPlain()
        plain_result = plain_schema.dump(
            {"items": [{"name": "Item1", "price": 10.0}, {"name": "Item2", "price": 20.0}]}
        )

        # JIT
        @jit_schema
        class ItemSchema(Schema):
            name = fields.Str()
            price = fields.Float()

        @jit_schema
        class OrderSchema(Schema):
            items = fields.Nested(ItemSchema, many=True)

        jit_schema_instance = OrderSchema()
        jit_result = jit_schema_instance.dump(
            {"items": [{"name": "Item1", "price": 10.0}, {"name": "Item2", "price": 20.0}]}
        )

        compare_results(jit_result, plain_result, "nested many")


class TestJITSchemaReuse:
    """Test JIT schema reuse and initialization."""

    def test_jit_schema_reuse_different_data(self) -> None:
        """Test that JIT schema can be reused with different data."""

        # Plain marshmallow
        class ReusableSchemaPlain(Schema):
            name = fields.Str()

        plain_schema = ReusableSchemaPlain()
        plain_result1 = plain_schema.dump({"name": "Alice"})
        plain_result2 = plain_schema.dump({"name": "Bob"})

        # JIT
        @jit_schema
        class ReusableSchema(Schema):
            name = fields.Str()

        jit_schema_instance = ReusableSchema()
        jit_result1 = jit_schema_instance.dump({"name": "Alice"})
        jit_result2 = jit_schema_instance.dump({"name": "Bob"})

        compare_results(jit_result1, plain_result1, "reuse first call")
        compare_results(jit_result2, plain_result2, "reuse second call")

    def test_jit_applied_flag_prevents_double_compilation(self) -> None:
        """Test that _jit_applied flag prevents double compilation."""

        class CustomSchema(JITSchemaMixin, Schema):
            name = fields.Str()

        schema = CustomSchema()
        assert schema._jit_applied is True


class TestPythonCodeGeneration:
    """Test Python code generation utilities."""

    def test_complex_schema_serialization_and_deserialization(self) -> None:
        """Test that complex field types work correctly."""

        import uuid

        test_uuid = uuid.uuid4()
        test_data = {
            "when": datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            "duration": timedelta(hours=2),
            "ip": ipaddress.IPv4Address("192.168.1.1"),
            "uuid_field": test_uuid,
            "email": "test@example.com",
            "url": "https://example.com",
        }

        # Plain marshmallow
        class ComplexSchemaPlain(Schema):
            when = fields.AwareDateTime()
            duration = fields.TimeDelta()
            ip = fields.IP()
            uuid_field = fields.UUID()
            email = fields.Email()
            url = fields.Url()

        plain_schema = ComplexSchemaPlain()
        plain_result = plain_schema.dump(test_data)

        # JIT
        @jit_schema
        class ComplexSchema(Schema):
            when = fields.AwareDateTime()
            duration = fields.TimeDelta()
            ip = fields.IP()
            uuid_field = fields.UUID()
            email = fields.Email()
            url = fields.Url()

        jit_schema_instance = ComplexSchema()
        jit_result = jit_schema_instance.dump(test_data)

        compare_results(jit_result, plain_result, "complex fields dump")


class TestSchemaWithUnknownFields:
    """Test schema handling of unknown fields."""

    def test_schema_unknown_exclude_serialization(self) -> None:
        """Test schema with unknown=EXCLUDE excludes extra fields."""
        from marshmallow import EXCLUDE

        # Plain marshmallow
        class StrictSchemaPlain(Schema):
            class Meta:
                unknown = EXCLUDE

            name = fields.Str()

        plain_schema = StrictSchemaPlain()
        plain_result = plain_schema.dump({"name": "Alice", "extra": "data", "more": "fields"})

        # JIT
        @jit_schema
        class StrictSchema(Schema):
            class Meta:
                unknown = EXCLUDE

            name = fields.Str()

        jit_schema_instance = StrictSchema()
        jit_result = jit_schema_instance.dump({"name": "Alice", "extra": "data", "more": "fields"})

        compare_results(jit_result, plain_result, "unknown exclude dump")

    def test_schema_unknown_include_serialization(self) -> None:
        """Test schema with unknown=INCLUDE includes extra fields in load."""
        from marshmallow import INCLUDE

        # Plain marshmallow
        class PermissiveSchemaPlain(Schema):
            class Meta:
                unknown = INCLUDE

            name = fields.Str()

        plain_schema = PermissiveSchemaPlain()
        plain_result = plain_schema.load({"name": "Alice", "extra": "data"})

        # JIT
        @jit_schema
        class PermissiveSchema(Schema):
            class Meta:
                unknown = INCLUDE

            name = fields.Str()

        jit_schema_instance = PermissiveSchema()
        jit_result = jit_schema_instance.load({"name": "Alice", "extra": "data"})

        compare_results(jit_result, plain_result, "unknown include load")

    def test_schema_unknown_raise_deserialization(self) -> None:
        """Test schema with unknown=RAISE raises error on extra fields."""
        from marshmallow import RAISE

        # Plain marshmallow
        class StrictSchemaPlain(Schema):
            class Meta:
                unknown = RAISE

            name = fields.Str()

        plain_schema = StrictSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({"name": "Alice", "extra": "data"})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class StrictSchema(Schema):
            class Meta:
                unknown = RAISE

            name = fields.Str()

        jit_schema_instance = StrictSchema()
        jit_error = None
        try:
            jit_schema_instance.load({"name": "Alice", "extra": "data"})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "unknown raise")


class TestContextPassing:
    """Test context passing through nested serialization."""

    def test_context_passed_to_nested_schema(self) -> None:
        """Test that context is passed to nested schemas."""
        import warnings

        import pytest

        from marshmallow_jit.compat import HAS_CONTEXT_PARAM

        # Context parameter was removed in marshmallow 4
        if not HAS_CONTEXT_PARAM:
            pytest.skip("Context parameter removed in marshmallow 4")

        try:
            from marshmallow.warnings import RemovedInMarshmallow4Warning  # type: ignore[unresolved-import]
        except ImportError:
            # Marshmallow 4 - warnings module removed
            pytest.skip("Warnings module removed in marshmallow 4")

        # Suppress deprecation warnings for context parameter (testing marshmallow 3.x compatibility)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RemovedInMarshmallow4Warning)

            # Plain marshmallow
            class ChildSchemaPlain(Schema):
                name = fields.Str()

            class ParentSchemaPlain(Schema):
                child = fields.Nested(ChildSchemaPlain)

            plain_schema = ParentSchemaPlain(context={"uppercase": True})  # type: ignore[call-arg]
            plain_result = plain_schema.dump({"child": {"name": "alice"}})

            # JIT
            @jit_schema
            class ChildSchema(Schema):
                name = fields.Str()

            @jit_schema
            class ParentSchema(Schema):
                child = fields.Nested(ChildSchema)

            jit_schema_instance = ParentSchema(context={"uppercase": True})  # type: ignore[call-arg]
            jit_result = jit_schema_instance.dump({"child": {"name": "alice"}})

            compare_results(jit_result, plain_result, "context passing")


class TestErrorStoreIntegration:
    """Test error accumulation and reporting."""

    def test_single_field_error(self) -> None:
        """Test that single field error is reported correctly."""

        # Plain marshmallow
        class SingleFieldSchemaPlain(Schema):
            name = fields.Str(required=True)

        plain_schema = SingleFieldSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class SingleFieldSchema(Schema):
            name = fields.Str(required=True)

        jit_schema_instance = SingleFieldSchema()
        jit_error = None
        try:
            jit_schema_instance.load({})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "single field error")

    def test_nested_errors(self) -> None:
        """Test error reporting for nested schemas."""

        # Plain marshmallow
        class ItemSchemaPlain(Schema):
            name = fields.Str(required=True)

        class OrderSchemaPlain(Schema):
            item = fields.Nested(ItemSchemaPlain)

        plain_schema = OrderSchemaPlain()
        plain_error = None
        try:
            plain_schema.load({"item": {}})
        except ValidationError as e:
            plain_error = e

        # JIT
        @jit_schema
        class ItemSchema(Schema):
            name = fields.Str(required=True)

        @jit_schema
        class OrderSchema(Schema):
            item = fields.Nested(ItemSchema)

        jit_schema_instance = OrderSchema()
        jit_error = None
        try:
            jit_schema_instance.load({"item": {}})
        except ValidationError as e:
            jit_error = e

        assert plain_error is not None and jit_error is not None
        compare_errors(jit_error, plain_error, "nested errors")
