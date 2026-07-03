# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from typing import Any, override

import pytest
from marshmallow import Schema, fields, missing

from marshmallow_jit.jit.accessors.dict import DictAccessor
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode


def render(schema: Schema, attr_name: str, field: fields.Raw, value_variable_name: str = "value") -> PythonCode:
    accessor = DictAccessor()
    code = PythonCode()
    context = Context()
    field_var = code.add_variable("field", field)
    accessor.generate_code(code, value_variable_name, field_var, schema, attr_name, field, context)

    # verify the generated code is syntactically valid without running it
    with_function = PythonCode()
    with with_function.indent("def func(obj)"):
        with_function += str(code)
    with_function.compile({"obj": {}})

    return code


def field_variable(code: PythonCode, field: fields.Raw) -> str:
    for name, value in code.variables.items():
        if value is field:
            return name
    raise AssertionError("field was not registered as a code variable")


@pytest.fixture
def dedent() -> Any:
    """Strips a multiline string's common leading whitespace the same way PythonCode.write() does."""

    def _dedent(text: str) -> str:
        code = PythonCode()
        code += text
        return str(code)

    return _dedent


def test_missing_dump_default_assigns_missing_directly(dedent: Any) -> None:
    field = fields.Raw()
    code = render(Schema(), "name", field)
    assert str(code) == dedent(
        """
        try:
            value = obj['name']
        except KeyError:
            value = missing
        """
    )


@pytest.mark.parametrize("default_value", [0, "", False, None, [], {}, "fallback", 42])
def test_non_callable_dump_default_is_assigned_directly_without_a_callable_check(
    dedent: Any, default_value: int | str | bool | list[Any] | dict[str, Any]
) -> None:
    field = fields.Raw(dump_default=default_value)
    code = render(Schema(), "name", field)
    fvar = field_variable(code, field)
    assert str(code) == dedent(
        f"""
        try:
            value = obj['name']
        except KeyError:
            value = {fvar}.dump_default
        """
    )


@pytest.mark.parametrize("callable_default", [list, dict, str, lambda: "generated"])
def test_callable_dump_default_is_called_directly_without_a_callable_check(
    dedent: Any, callable_default: type[list[Any] | dict[str, Any] | str]
) -> None:
    field = fields.Raw(dump_default=callable_default)
    code = render(Schema(), "name", field)
    fvar = field_variable(code, field)
    assert str(code) == dedent(
        f"""
        try:
            value = obj['name']
        except KeyError:
            value = {fvar}.dump_default()
        """
    )


@pytest.mark.parametrize("dump_default", [missing, "fallback", list])
def test_field_variable_is_registered_and_bound_to_the_actual_field_instance(
    dump_default: object,
) -> None:
    field = fields.Raw(dump_default=dump_default)
    code = render(Schema(), "name", field)
    fvar = field_variable(code, field)
    assert code.variables[fvar] is field


def test_uses_the_given_value_variable_name_throughout(dedent: Any) -> None:
    code = render(Schema(), "name", fields.Raw(), value_variable_name="val2")
    assert str(code) == dedent(
        """
        try:
            val2 = obj['name']
        except KeyError:
            val2 = missing
        """
    )


def test_uses_field_attribute_instead_of_attr_name_as_the_lookup_key() -> None:
    result = str(render(Schema(), "name", fields.Raw(attribute="internal_name")))
    assert "obj['internal_name']" in result
    assert "obj['name']" not in result


@pytest.mark.parametrize(
    "key",
    ["simple", "with space", "with'quote", 'with"doublequote', "with\\backslash"],
)
def test_check_key_is_rendered_via_repr(key: str) -> None:
    result = str(render(Schema(), key, fields.Raw()))
    assert f"obj[{key!r}]" in result


def test_field_attribute_as_a_dotted_path_produces_chained_bracket_lookups(dedent: Any) -> None:
    # a dotted field.attribute like "a.b.c" is split on "." into a chain of bracket
    # lookups, all covered by the single except KeyError clause
    field = fields.Raw(attribute="a.b.c")
    code = render(Schema(), "name", field)
    assert str(code) == dedent(
        """
        try:
            value = obj['a']['b']['c']
        except KeyError:
            value = missing
        """
    )


@pytest.mark.parametrize("default_value", ["fallback", 42])
def test_field_attribute_as_a_dotted_path_with_non_callable_dump_default(dedent: Any, default_value: str | int) -> None:
    field = fields.Raw(attribute="a.b.c", dump_default=default_value)
    code = render(Schema(), "name", field)
    fvar = field_variable(code, field)
    assert str(code) == dedent(
        f"""
        try:
            value = obj['a']['b']['c']
        except KeyError:
            value = {fvar}.dump_default
        """
    )


def test_field_attribute_as_a_dotted_path_with_callable_dump_default(dedent: Any) -> None:
    field = fields.Raw(attribute="a.b.c", dump_default=list)
    code = render(Schema(), "name", field)
    fvar = field_variable(code, field)
    assert str(code) == dedent(
        f"""
        try:
            value = obj['a']['b']['c']
        except KeyError:
            value = {fvar}.dump_default()
        """
    )


def test_check_attribute_false_generates_a_single_none_assignment() -> None:
    field = fields.Raw()
    field._CHECK_ATTRIBUTE = False
    code = render(Schema(), "name", field)
    # Accessor no longer generates code for _CHECK_ATTRIBUTE=False fields;
    # the serializer handles initialization when needed.
    assert str(code) == ""
    # The generate() helper registers a field variable even if not used
    assert len(code.variables) == 1


def test_check_attribute_false_bypasses_custom_get_attribute() -> None:
    class CustomSchema(Schema):
        @override
        def get_attribute(self, obj: Any, attr: str, default: Any) -> Any:
            raise AssertionError("should not be called")

    field = fields.Raw()
    field._CHECK_ATTRIBUTE = False
    code = render(CustomSchema(), "name", field)
    # Accessor generates no code; custom get_attribute is not called.
    assert str(code) == ""


def test_uses_self_get_attribute_when_schema_overrides_it(dedent: Any) -> None:
    class CustomSchema(Schema):
        @override
        def get_attribute(self, obj: Any, attr: str, default: Any) -> Any:
            return default

    field = fields.Raw()
    code = render(CustomSchema(), "name", field)
    fvar = field_variable(code, field)
    # The variable name now includes an index due to generate_variable
    assert f"default={fvar}.dump_default" in str(code)


def test_overridden_get_attribute_also_uses_field_attribute_as_check_key() -> None:
    class CustomSchema(Schema):
        @override
        def get_attribute(self, obj: Any, attr: str, default: Any) -> Any:
            return default

    result = str(render(CustomSchema(), "name", fields.Raw(attribute="internal_name")))
    # The variable is registered with the "field" prefix
    fvar = "field_1"  # First field gets index 1
    assert f"self.get_attribute(obj, 'internal_name', default={fvar}.dump_default)" in result
    assert "'name'" not in result
