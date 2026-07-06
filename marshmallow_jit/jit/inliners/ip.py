# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""IP address field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, override

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from ._ip_base import _IPSerializationInliner
from .base import Inliner

if TYPE_CHECKING:
    pass


class IPSerializationInliner(_IPSerializationInliner):
    """IP serialization inliner - inherits from base."""

    pass


class IPDeserializationInliner(Inliner):
    """IP deserialization validates and converts to ipaddress.IPv4Address or ipaddress.IPv6Address.

    Handles string input and validates it's a valid IP address. Returns ipaddress.IPv4Address
    or ipaddress.IPv6Address objects depending on the input.
    """

    @override
    def generate_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        code.add_import_line("import ipaddress")
        code.add_import_line("from marshmallow import utils")
        code += f"""
        if {value_variable_name} is None:
            pass
        else:
            try:
                {value_variable_name} = (
                    {field_obj_variable_name}.DESERIALIZATION_CLASS or ipaddress.ip_address
                )(utils.ensure_text_type({value_variable_name}))
            except (ValueError, TypeError) as error:
                raise {field_obj_variable_name}.make_error("invalid_ip") from error
        """
