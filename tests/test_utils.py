# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Tests for utility functions."""

from types import MethodType
from typing import Any, override

from marshmallow import fields

from marshmallow_jit.utils import is_overridden, is_property_overridden


class BaseClass:
    """Base class for testing."""

    def base_method(self) -> str:
        return "base"

    def overridable_method(self) -> str:
        return "base"

    @property
    def base_property(self) -> str:
        return "base"

    @property
    def overridable_property(self) -> str:
        return "base"


class InheritedNotOverridden(BaseClass):
    """Inherits from BaseClass without overriding."""

    pass


class InheritedWithMethodOverride(BaseClass):
    """Overrides a method."""

    @override
    def overridable_method(self) -> str:
        return "overridden"


class InheritedWithPropertyOverride(BaseClass):
    """Overrides a property."""

    @property
    @override
    def overridable_property(self) -> str:
        return "overridden"


class InheritedWithNewProperty(BaseClass):
    """Adds a new property not in base."""

    @property
    def new_property(self) -> str:
        return "new"


class InheritedWithPropertyAsAttribute(BaseClass):
    """Replaces a property with a regular attribute."""

    overridable_property = "attribute"  # type: ignore[misc,assignment]


# ========================================================================
# Tests for is_overridden
# ========================================================================


def test_is_overridden_base_method() -> None:
    """Test that base method is not considered overridden."""
    obj = InheritedNotOverridden()
    assert not is_overridden(obj.base_method, BaseClass.base_method)  # type: ignore[arg-type]


def test_is_overridden_inherited_not_overridden() -> None:
    """Test that inherited method is not considered overridden."""
    obj = InheritedNotOverridden()
    assert not is_overridden(obj.overridable_method, BaseClass.overridable_method)  # type: ignore[arg-type]


def test_is_overridden_method_override() -> None:
    """Test that overridden method is detected."""
    obj = InheritedWithMethodOverride()
    assert is_overridden(obj.overridable_method, BaseClass.overridable_method)  # type: ignore[arg-type]


def test_is_overridden_with_method_type() -> None:
    """Test with actual MethodType objects."""
    obj = InheritedWithMethodOverride()
    instance_method = obj.overridable_method
    assert isinstance(instance_method, MethodType)
    assert is_overridden(instance_method, BaseClass.overridable_method)


def test_is_overridden_base_class_reference() -> None:
    """Test comparing against the same method."""
    obj = BaseClass()
    assert not is_overridden(obj.base_method, BaseClass.base_method)  # type: ignore[arg-type]


# ========================================================================
# Tests for is_property_overridden
# ========================================================================


def test_is_property_overridden_not_in_dict() -> None:
    """Test when property is not in instance's class __dict__ (inherited)."""
    obj = InheritedNotOverridden()
    result = is_property_overridden(obj, "base_property", BaseClass)
    assert result is False


def test_is_property_overridden_inherited_property() -> None:
    """Test when property is inherited but not overridden."""
    obj = InheritedNotOverridden()
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    assert result is False


def test_is_property_overridden_with_override() -> None:
    """Test when property is actually overridden."""
    obj = InheritedWithPropertyOverride()
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    assert result is True


def test_is_property_overridden_new_property() -> None:
    """Test when property doesn't exist in base class."""
    obj = InheritedWithNewProperty()
    result = is_property_overridden(obj, "new_property", BaseClass)
    assert result is True


def test_is_property_overridden_property_as_attribute() -> None:
    """Test when property is replaced with regular attribute."""
    obj = InheritedWithPropertyAsAttribute()
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    assert result is True


def test_is_property_overridden_nonexistent_property() -> None:
    """Test with property that doesn't exist anywhere."""
    obj = BaseClass()
    result = is_property_overridden(obj, "nonexistent", BaseClass)
    assert result is False


def test_is_property_overridden_base_class_no_property() -> None:
    """Test when base class doesn't have the property but instance does."""
    obj = InheritedWithNewProperty()
    # Check against BaseClass which doesn't have 'new_property'
    result = is_property_overridden(obj, "new_property", BaseClass)
    assert result is True


# ========================================================================
# Tests with real marshmallow Field objects
# ========================================================================


def test_is_overridden_with_marshmallow_field() -> None:
    """Test is_overridden with actual marshmallow field methods."""
    from marshmallow.fields import Field

    # Standard field doesn't override _serialize
    string_field = fields.String()
    # Note: We need to check if String overrides Field._serialize
    # String actually does override _serialize, so this should be True
    result = is_overridden(string_field._serialize, Field._serialize)  # type: ignore[arg-type]
    assert result is True  # String overrides _serialize


def test_is_overridden_with_custom_field() -> None:
    """Test is_overridden with custom field."""
    from marshmallow.fields import Field

    class CustomField(Field):
        @override
        def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> str:
            return "custom"

    field = CustomField()
    result = is_overridden(field._serialize, Field._serialize)  # type: ignore[arg-type]
    assert result is True


def test_is_property_overridden_with_marshmallow_validate_all() -> None:
    """Test is_property_overridden with marshmallow _validate_all property."""
    from marshmallow.fields import Field

    # Standard String field doesn't override _validate_all
    string_field = fields.String()
    result = is_property_overridden(string_field, "_validate_all", Field)
    assert result is False


def test_is_property_overridden_with_custom_validate_all() -> None:
    """Test is_property_overridden with custom _validate_all."""
    from marshmallow.fields import Field

    class CustomField(Field):
        @property
        @override
        def _validate_all(self) -> bool:
            return True

    field = CustomField()
    result = is_property_overridden(field, "_validate_all", Field)
    assert result is True


def test_is_property_overridden_same_property_object() -> None:
    """Test that same property object is not considered overridden."""
    from marshmallow.fields import Field

    # Field base class with _validate_all
    field = Field()
    result = is_property_overridden(field, "_validate_all", Field)
    # Field has it in __dict__, but it's the same property object
    # Actually, for the base instance, it's not in Field's __dict__ check
    # Let's verify:
    assert "_validate_all" in Field.__dict__
    assert isinstance(Field.__dict__["_validate_all"], property)
    # For Field() instance, type(field).__dict__ is Field.__dict__
    # So "_validate_all" IS in type(field).__dict__
    # But it's the same property object as in base_class.__dict__
    # So the function should check if they're the same
    # Looking at the code: instance_prop.fget is not base_prop.fget
    # If they're the same, fget should be identical
    assert result is False


# ========================================================================
# Edge cases
# ========================================================================


def test_is_property_overridden_multiple_inheritance_levels() -> None:
    """Test with multiple levels of inheritance."""

    class Level1(BaseClass):
        @property
        @override
        def overridable_property(self) -> str:
            return "level1"

    class Level2(Level1):
        pass

    class Level3(Level2):
        @property
        @override
        def overridable_property(self) -> str:
            return "level3"

    obj = Level3()
    # Level3 overrides relative to BaseClass (has it in Level3.__dict__)
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    assert result is True

    # Level2 doesn't override itself - it inherits from Level1
    # But Level1 DID override relative to BaseClass
    # So Level2 instances have overridden behavior
    obj2 = Level2()
    result2 = is_property_overridden(obj2, "overridable_property", BaseClass)
    # This should return True because the MRO contains an override (in Level1)
    assert result2 is True

    # Level1 does override relative to BaseClass
    obj1 = Level1()
    result1 = is_property_overridden(obj1, "overridable_property", BaseClass)
    assert result1 is True


def test_is_property_overridden_with_descriptor() -> None:
    """Test that non-property descriptors are detected as overrides."""

    class CustomDescriptor:
        def __get__(self, obj: Any, objtype: type | None = None) -> str:
            return "descriptor"

    class WithDescriptor(BaseClass):
        overridable_property = CustomDescriptor()  # type: ignore[assignment]

    obj = WithDescriptor()
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    # Descriptor is not a property, so different types -> override
    assert result is True


def test_is_property_overridden_deleted_property() -> None:
    """Test when property is deleted from a subclass."""

    class DeletedProperty(BaseClass):
        # This is an unusual case but possible
        overridable_property = None  # type: ignore[assignment]

    obj = DeletedProperty()
    result = is_property_overridden(obj, "overridable_property", BaseClass)
    # None is not a property, so it's overridden
    assert result is True


def test_is_property_overridden_with_non_property_in_base() -> None:
    """Test when base has non-property attribute but instance has property.

    This is an edge case - the function is designed to check property overrides,
    so when the base doesn't have a property, it returns False (not an override).
    """

    class BaseWithAttribute:
        non_property_attr = "value"

    class SubclassWithProperty(BaseWithAttribute):
        @property
        @override
        def non_property_attr(self) -> str:  # type: ignore[misc]
            return "property value"

    obj = SubclassWithProperty()
    # Base has a regular attribute, not a property
    # The function returns False because it's checking property overrides specifically
    result = is_property_overridden(obj, "non_property_attr", BaseWithAttribute)
    # Since base doesn't have it as a property, this returns False
    assert result is False
