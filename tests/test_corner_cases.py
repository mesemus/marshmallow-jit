"""Additional corner case tests to ensure JIT behaves exactly like marshmallow."""

import datetime as dt
import decimal
from typing import Any

from marshmallow import Schema, fields, post_load, pre_load

from marshmallow_jit.schema import jit_schema


def dump_or_error(schema: Schema, data: Any) -> tuple[str, Any]:
    """Helper to capture result or error."""
    try:
        result = schema.dump(data)
        return ("success", result)
    except Exception as e:
        return ("error", (type(e), str(e), repr(e)))


def load_or_error(schema: Schema, data: Any) -> tuple[str, Any]:
    """Helper to capture result or error."""
    try:
        result = schema.load(data)
        return ("success", result)
    except Exception as e:
        return ("error", (type(e), str(e), repr(e)))


def build_plain_and_jit_schemas(schema_class: type[Schema]) -> tuple[Schema, Schema]:
    """Build plain and JIT versions of a schema from schema class definition.

    The schema_class should be a plain Schema (not yet JIT-compiled).
    Returns (plain_schema_instance, jit_schema_instance).
    """
    plain_schema = schema_class()
    jit_schema_class = jit_schema(schema_class)
    jit_schema_inst = jit_schema_class()
    return plain_schema, jit_schema_inst


class TestDictCornerCases:
    """Test corner cases for Dict field serialization/deserialization."""

    def test_dict_with_none_values_serialization(self) -> None:
        """Test Dict handles None values correctly during serialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Int(allow_none=True))

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {"a": 1, "b": None, "c": 3}}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_none_values_deserialization(self) -> None:
        """Test Dict handles None values correctly during deserialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Int(allow_none=True))

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data_plain = {"data": {"a": 1, "b": None, "c": 3}}
        test_data_jit = {"data": {"a": 1, "b": None, "c": 3}}

        plain_result = load_or_error(plain_schema, test_data_plain)
        jit_result = load_or_error(jit_schema_inst, test_data_jit)

        assert jit_result == plain_result

    def test_dict_with_empty_dict_serialization(self) -> None:
        """Test Dict handles empty dict correctly during serialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Int())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {}}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_empty_dict_deserialization(self) -> None:
        """Test Dict handles empty dict correctly during deserialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Int())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {}}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_nested_dicts_serialization(self) -> None:
        """Test Dict with nested dict values during serialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Dict())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {"a": {"x": 1}, "b": {"y": 2}}}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_nested_dicts_deserialization(self) -> None:
        """Test Dict with nested dict values during deserialization."""

        class TestSchema(Schema):
            data = fields.Dict(keys=fields.Str(), values=fields.Dict())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {"a": {"x": 1}, "b": {"y": 2}}}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_tuple_keys_serialization(self) -> None:
        """Test Dict with tuple keys during serialization."""

        class TestSchema(Schema):
            data = fields.Dict()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"data": {(1, 2): "tuple_key", (3, 4): "another"}}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_dict_with_tuple_keys_deserialization(self) -> None:
        """Test Dict with tuple keys during deserialization."""

        class TestSchema(Schema):
            data = fields.Dict()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        # For deserialization, keys in JSON are strings
        test_data = {"data": {"key1": "value1", "key2": "value2"}}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestListCornerCases:
    """Test corner cases for List field serialization/deserialization."""

    def test_list_with_none_elements_serialization(self) -> None:
        """Test List handles None elements correctly during serialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Int(allow_none=True))

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": [1, None, 3, None, 5]}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_list_with_none_elements_deserialization(self) -> None:
        """Test List handles None elements correctly during deserialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Int(allow_none=True))

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data_plain = {"items": [1, None, 3, None, 5]}
        test_data_jit = {"items": [1, None, 3, None, 5]}

        plain_result = load_or_error(plain_schema, test_data_plain)
        jit_result = load_or_error(jit_schema_inst, test_data_jit)

        assert jit_result == plain_result

    def test_list_with_empty_list_serialization(self) -> None:
        """Test List handles empty list correctly during serialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Str())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": []}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_list_with_empty_list_deserialization(self) -> None:
        """Test List handles empty list correctly during deserialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Str())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": []}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_list_with_generator_serialization(self) -> None:
        """Test List handles generator correctly during serialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Int())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        # Generators are consumed, so we need separate ones for each schema
        test_data_plain = {"items": (x for x in [1, 2, 3])}
        test_data_jit = {"items": (x for x in [1, 2, 3])}

        plain_result = dump_or_error(plain_schema, test_data_plain)
        jit_result = dump_or_error(jit_schema_inst, test_data_jit)

        assert jit_result == plain_result

    def test_list_with_tuple_serialization(self) -> None:
        """Test List handles tuple correctly during serialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Int())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": (1, 2, 3)}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_list_with_tuple_deserialization(self) -> None:
        """Test List handles tuple correctly during deserialization."""

        class TestSchema(Schema):
            items = fields.List(fields.Int())

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": (1, 2, 3)}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestNestedCornerCases:
    """Test corner cases for Nested field serialization/deserialization."""

    def test_nested_with_none_serialization(self) -> None:
        """Test Nested handles None correctly during serialization."""

        class InnerSchema(Schema):
            value = fields.Int()

        class TestSchema(Schema):
            inner = fields.Nested(InnerSchema)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"inner": None}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_nested_with_none_deserialization(self) -> None:
        """Test Nested handles None correctly during deserialization."""

        class InnerSchema(Schema):
            value = fields.Int()

        class TestSchema(Schema):
            inner = fields.Nested(InnerSchema)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"inner": None}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_nested_many_with_empty_list_serialization(self) -> None:
        """Test Nested with many=True handles empty list during serialization."""

        class InnerSchema(Schema):
            value = fields.Int()

        class TestSchema(Schema):
            items = fields.Nested(InnerSchema, many=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": []}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_nested_many_with_empty_list_deserialization(self) -> None:
        """Test Nested with many=True handles empty list during deserialization."""

        class InnerSchema(Schema):
            value = fields.Int()

        class TestSchema(Schema):
            items = fields.Nested(InnerSchema, many=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"items": []}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_deeply_nested_schemas_serialization(self) -> None:
        """Test deeply nested schemas during serialization."""

        class Level3Schema(Schema):
            value = fields.Int()

        class Level2Schema(Schema):
            level3 = fields.Nested(Level3Schema)

        class Level1Schema(Schema):
            level2 = fields.Nested(Level2Schema)

        class TestSchema(Schema):
            level1 = fields.Nested(Level1Schema)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"level1": {"level2": {"level3": {"value": 42}}}}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_deeply_nested_schemas_deserialization(self) -> None:
        """Test deeply nested schemas during deserialization."""

        class Level3Schema(Schema):
            value = fields.Int()

        class Level2Schema(Schema):
            level3 = fields.Nested(Level3Schema)

        class Level1Schema(Schema):
            level2 = fields.Nested(Level2Schema)

        class TestSchema(Schema):
            level1 = fields.Nested(Level1Schema)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"level1": {"level2": {"level3": {"value": 42}}}}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestFieldValidationCornerCases:
    """Test corner cases for field validation."""

    def test_required_field_with_none_serialization(self) -> None:
        """Test required field with None value during serialization."""

        class TestSchema(Schema):
            value = fields.Int(required=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": None}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_required_field_missing_deserialization(self) -> None:
        """Test required field missing during deserialization."""

        class TestSchema(Schema):
            value = fields.Int(required=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {}  # Missing required field

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_allow_none_with_none_serialization(self) -> None:
        """Test allow_none=True with None value during serialization."""

        class TestSchema(Schema):
            value = fields.Int(allow_none=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": None}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_allow_none_with_none_deserialization(self) -> None:
        """Test allow_none=True with None value during deserialization."""

        class TestSchema(Schema):
            value = fields.Int(allow_none=True)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": None}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_field_with_dump_default_none_serialization(self) -> None:
        """Test field with dump_default=None during serialization."""

        class TestSchema(Schema):
            value = fields.Int(dump_default=None)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {}  # Missing field

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_field_with_load_default_deserialization(self) -> None:
        """Test field with load_default during deserialization."""

        class TestSchema(Schema):
            value = fields.Int(load_default=42)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {}  # Missing field

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestSpecialCharactersInKeys:
    """Test schemas with special characters in field names."""

    def test_field_with_spaces_in_data_key_serialization(self) -> None:
        """Test field with spaces in data_key during serialization."""

        class TestSchema(Schema):
            value = fields.Int(data_key="field with spaces")

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"field with spaces": 42}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_field_with_spaces_in_data_key_deserialization(self) -> None:
        """Test field with spaces in data_key during deserialization."""

        class TestSchema(Schema):
            value = fields.Int(data_key="field with spaces")

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"field with spaces": 42}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_field_with_special_chars_in_data_key_serialization(self) -> None:
        """Test field with special characters in data_key during serialization."""

        class TestSchema(Schema):
            value = fields.Int(data_key="field-with-dashes.and.dots")

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"field-with-dashes.and.dots": 42}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_field_with_special_chars_in_data_key_deserialization(self) -> None:
        """Test field with special characters in data_key during deserialization."""

        class TestSchema(Schema):
            value = fields.Int(data_key="field-with-dashes.and.dots")

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"field-with-dashes.and.dots": 42}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestBoundaryValues:
    """Test boundary values for various field types."""

    def test_integer_max_value_serialization(self) -> None:
        """Test Integer with very large values during serialization."""

        class TestSchema(Schema):
            value = fields.Int()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": 2**63 - 1}  # Max int64

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_integer_max_value_deserialization(self) -> None:
        """Test Integer with very large values during deserialization."""

        class TestSchema(Schema):
            value = fields.Int()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": 2**63 - 1}  # Max int64

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_decimal_precision_serialization(self) -> None:
        """Test Decimal with high precision during serialization."""

        class TestSchema(Schema):
            value = fields.Decimal(places=10)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": decimal.Decimal("3.1415926535")}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_decimal_precision_deserialization(self) -> None:
        """Test Decimal with high precision during deserialization."""

        class TestSchema(Schema):
            value = fields.Decimal(places=10)

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": "3.1415926535"}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_string_with_unicode_serialization(self) -> None:
        """Test String with unicode characters during serialization."""

        class TestSchema(Schema):
            value = fields.Str()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": "Hello 世界 🌍 Привет"}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_string_with_unicode_deserialization(self) -> None:
        """Test String with unicode characters during deserialization."""

        class TestSchema(Schema):
            value = fields.Str()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": "Hello 世界 🌍 Привет"}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_datetime_with_microseconds_serialization(self) -> None:
        """Test DateTime with microseconds during serialization."""

        class TestSchema(Schema):
            value = fields.DateTime()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": dt.datetime(2024, 1, 1, 12, 30, 45, 123456)}

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_datetime_with_microseconds_deserialization(self) -> None:
        """Test DateTime with microseconds during deserialization."""

        class TestSchema(Schema):
            value = fields.DateTime()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": "2024-01-01T12:30:45.123456"}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result


class TestSchemaHooks:
    """Test that schema hooks work correctly with JIT."""

    def test_post_load_hook(self) -> None:
        """Test post_load hook is called correctly."""

        class TestSchema(Schema):
            value = fields.Int()

            @post_load
            def add_marker(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                data["marker"] = "processed"
                return data

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {"value": 42}

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_pre_load_hook(self) -> None:
        """Test pre_load hook is called correctly."""

        class TestSchema(Schema):
            value = fields.Int()

            @pre_load
            def double_value(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
                if "value" in data:
                    data["value"] = data["value"] * 2
                return data

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        # pre_load hook mutates data, so we need separate copies
        test_data_plain = {"value": 21}
        test_data_jit = {"value": 21}

        plain_result = load_or_error(plain_schema, test_data_plain)
        jit_result = load_or_error(jit_schema_inst, test_data_jit)

        assert jit_result == plain_result


class TestMixedFieldTypes:
    """Test schemas with mixed field types."""

    def test_schema_with_all_field_types_serialization(self) -> None:
        """Test schema with many different field types during serialization."""

        class TestSchema(Schema):
            string_field = fields.Str()
            int_field = fields.Int()
            float_field = fields.Float()
            bool_field = fields.Bool()
            date_field = fields.Date()
            datetime_field = fields.DateTime()
            list_field = fields.List(fields.Int())
            dict_field = fields.Dict()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {
            "string_field": "hello",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "date_field": dt.date(2024, 1, 1),
            "datetime_field": dt.datetime(2024, 1, 1, 12, 0, 0),
            "list_field": [1, 2, 3],
            "dict_field": {"a": 1, "b": 2},
        }

        plain_result = dump_or_error(plain_schema, test_data)
        jit_result = dump_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result

    def test_schema_with_all_field_types_deserialization(self) -> None:
        """Test schema with many different field types during deserialization."""

        class TestSchema(Schema):
            string_field = fields.Str()
            int_field = fields.Int()
            float_field = fields.Float()
            bool_field = fields.Bool()
            date_field = fields.Date()
            datetime_field = fields.DateTime()
            list_field = fields.List(fields.Int())
            dict_field = fields.Dict()

        plain_schema, jit_schema_inst = build_plain_and_jit_schemas(TestSchema)

        test_data = {
            "string_field": "hello",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "date_field": "2024-01-01",
            "datetime_field": "2024-01-01T12:00:00",
            "list_field": [1, 2, 3],
            "dict_field": {"a": 1, "b": 2},
        }

        plain_result = load_or_error(plain_schema, test_data)
        jit_result = load_or_error(jit_schema_inst, test_data)

        assert jit_result == plain_result
