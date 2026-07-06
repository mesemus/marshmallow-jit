# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from collections.abc import Callable
from types import MethodType
from typing import Any


def is_overridden(instance_func: MethodType, class_func: Callable[..., Any]) -> bool:
    """Check if a method has been overridden in the instance's class."""
    return instance_func.__func__ is not class_func


def is_property_overridden(instance: Any, prop_name: str, base_class: type) -> bool:
    """Check if a property getter has been overridden in the instance's class or ancestors.

    This checks if the property's behavior differs from the base_class version,
    using Python's normal attribute lookup through the MRO.

    Args:
        instance: The field instance
        prop_name: Name of the property to check
        base_class: The base class to compare against (e.g., Field)

    Returns:
        True if the property getter has been overridden anywhere in the MRO, False otherwise
    """
    instance_class = type(instance)

    # Get the property from base class
    base_prop = base_class.__dict__.get(prop_name)
    if base_prop is None:
        # Base class doesn't have this property, so check if instance class has it
        try:
            instance_attr = getattr(instance_class, prop_name)
            return isinstance(instance_attr, property)
        except AttributeError:
            return False

    # Get the property from instance class (using normal MRO lookup)
    try:
        instance_prop = getattr(instance_class, prop_name)
    except AttributeError:
        # Property not found in instance class hierarchy
        return False

    # Compare the getter functions if both are properties
    if isinstance(instance_prop, property) and isinstance(base_prop, property):
        return instance_prop.fget is not base_prop.fget

    # If instance has something but it's not a property, it's overridden
    if not isinstance(instance_prop, property) and isinstance(base_prop, property):
        return True

    # Other cases (shouldn't normally happen)
    return False
