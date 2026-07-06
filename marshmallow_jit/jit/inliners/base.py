# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base Inliner class for field-specific serialization/deserialization.

Defines the Inliner base cass and common validation code generation
used by all field-type-specific inliner implementations.
"""

from typing import TYPE_CHECKING

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

if TYPE_CHECKING:
    pass


class Inliner:
    #: True if generate_code() never writes anything (a pure passthrough), so callers
    #: can skip invoking it entirely instead of generating a call to a no-op method.
    is_noop: bool = False

    #: True if this inliner's generated code might set the value to `missing`,
    #: requiring a post-inliner check before assignment. Most inliners return False
    #: because they transform values without ever producing `missing`.
    can_return_missing: bool = False

    #: True if the caller needs to prepare partial kwargs (d_kwargs) before
    #: invoking this inliner. Deserialization inliners typically return False
    #: because they handle deserialization directly without needing partial.
    #: Serialization inliners always return False as they don't use partial.
    needs_partial_kwargs: bool = False

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
        """Generate deserialization/serialization code for this field type."""
        pass

    def generate_validate(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        """Generate inlined validation code for this field.

        This inlines _validate, _validate_all, and individual validator logic
        to eliminate function call overhead. Static checks are done at compile-time,
        only the value-dependent checks are in generated code.

        This is called after generate_code() to validate the transformed value.
        """
        from marshmallow.fields import Field as MarshmallowField
        from marshmallow.validate import URL, Email

        from marshmallow_jit.utils import is_overridden, is_property_overridden

        # Check if validation is needed at compile-time
        has_custom_validate = is_overridden(field._validate, MarshmallowField._validate)
        has_custom_validate_all = is_property_overridden(field, "_validate_all", MarshmallowField)
        has_validators = bool(field.validators)

        if not (has_custom_validate or has_custom_validate_all or has_validators):
            return

        # If user overrides _validate or _validate_all, we must call it
        if has_custom_validate or has_custom_validate_all:
            code += f"{field_obj_variable_name}._validate({value_variable_name})"
            return

        # And(...)(value)
        validators = tuple(field.validators)
        validators_var = code.add_variable("validators", validators)
        error_var = code.add_variable("and_default_error", field.error_messages["validator_failed"])

        # call
        errors_var = code.add_variable("validation_errors", None)
        kwargs_var = code.add_variable("validation_kwargs", None)
        code += f"""
        {errors_var} = []
        {kwargs_var} = {{}}
        """
        for idx, validator in enumerate(validators):
            with code.indent("try"):
                if isinstance(validator, Email):
                    # inline the email validator
                    code += f"""
                        _validator_self = {validators_var}[{idx}]
                        if not {value_variable_name} or "@" not in {value_variable_name}:
                            raise ValidationError(_validator_self._format_error({value_variable_name}))

                        user_part, domain_part = {value_variable_name}.rsplit("@", 1)

                        if not _validator_self.USER_REGEX.match(user_part):
                            raise ValidationError(_validator_self._format_error({value_variable_name}))

                        _failed = True
                        if domain_part not in _validator_self.DOMAIN_WHITELIST:
                            if not _validator_self.DOMAIN_REGEX.match(domain_part):
                                try:
                                    domain_part = domain_part.encode("idna").decode("ascii")
                                except UnicodeError:
                                    pass
                                else:
                                    if _validator_self.DOMAIN_REGEX.match(domain_part):
                                        _failed = False
                                if _failed:
                                    raise ValidationError(self._format_error({value_variable_name}))
                    """
                elif isinstance(validator, URL):
                    # Inline URL validation
                    code.add_import_line("from marshmallow.exceptions import ValidationError")
                    # Pre-compute regex at compile time since it's static
                    regex = validator._regex(
                        relative=validator.relative, absolute=validator.absolute, require_tld=validator.require_tld
                    )
                    regex_var = code.add_variable("url_regex", regex)
                    code += f"""
                    _validator_self = {validators_var}[{idx}]
                    if not {value_variable_name}:
                        raise ValidationError(_validator_self._format_error({value_variable_name}))

                    # Check first if the scheme is valid
                    _url_scheme = None
                    if "://" in {value_variable_name}:
                        _url_scheme = {value_variable_name}.split("://")[0].lower()
                        if _url_scheme not in _validator_self.schemes:
                            raise ValidationError(_validator_self._format_error({value_variable_name}))

                    # Hostname is optional for file URLs. If absent it means `localhost`.
                    # Fill it in for the validation if needed
                    if _url_scheme == "file" and {value_variable_name}.startswith("file:///"):
                        _url_matched = (
                            {regex_var}.search({value_variable_name}.replace("file:///", "file://localhost/", 1))
                        )
                    else:
                        _url_matched = {regex_var}.search({value_variable_name})

                    if not _url_matched:
                        raise ValidationError(_validator_self._format_error({value_variable_name}))
                    """
                else:
                    code += f"""
                        r = {validators_var}[{idx}]({value_variable_name})
                        if r is False and not isinstance(validator, Validator):
                            warnings.warn(
                                "Returning `False` from a validator is deprecated. Raise a `ValidationError` instead.",
                                ChangedInMarshmallow4Warning,
                                stacklevel=2,
                            )
                            raise ValidationError({error_var})  # noqa: TRY301
                    """

            with code.indent("except ValidationError as err"):
                code += f"""
                    {kwargs_var}.update(err.kwargs)
                    if isinstance(err.messages, dict):
                        {errors_var}.append(err.messages)
                    else:
                        {errors_var}.extend(err.messages)
                """

        code += f"""
        if {errors_var}:
            raise ValidationError({errors_var}, **{kwargs_var})
        """
