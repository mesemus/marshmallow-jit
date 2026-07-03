# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from collections.abc import Callable
from types import MethodType
from typing import Any


def is_overridden(instance_func: MethodType, class_func: Callable[..., Any]) -> bool:
    """Check if a method has been overridden in the instance's class."""
    return instance_func.__func__ is not class_func


def is_property_overridden(instance: Any, prop_name: str, base_class: type) -> bool:
    """Check if a property getter has been overridden in the instance's class.

    Args:
        instance: The field instance
        prop_name: Name of the property to check
        base_class: The base class to compare against (e.g., Field)

    Returns:
        True if the property getter has been overridden, False otherwise
    """
    # Check if this class (not parent) defines the property
    if prop_name not in type(instance).__dict__:
        return False

    instance_prop = type(instance).__dict__[prop_name]
    base_prop = base_class.__dict__.get(prop_name)

    # If base class doesn't have this property, any definition is an override
    if base_prop is None:
        return isinstance(instance_prop, property)

    # Compare the getter functions
    if isinstance(instance_prop, property) and isinstance(base_prop, property):
        return instance_prop.fget is not base_prop.fget

    # Different types means it's overridden
    return True
