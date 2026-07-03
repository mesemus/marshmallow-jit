# marshmallow.fields.Dict
def _jit_deserialize_SerializeDictSchema_1(
                            self,
                            data: (
                                typing.Mapping[str, typing.Any]
                                | typing.Iterable[typing.Mapping[str, typing.Any]]
                            ),
                            *,
                            error_store: ErrorStore,
                            many: bool = False,
                            partial=None,
                            unknown=RAISE,
                            index=None,
                        ) -> typing.Any | list[typing.Any]:
    index_errors = self.opts.index_errors
    index = index if index_errors else None
    if many:
        # we do not optimize arrays here (but custom serializer might),
        # so we are just calling the base serialize method for each item
        # and collecting the results into a list
        return self._deserialize_before_jit(
            data, error_store=error_store, many=many, partial=partial, unknown=unknown, index=index
        )
    ret_2 = {}
    if not isinstance(data, Mapping):
        error_store.store_error([self.error_messages["type"]], index=index)
        return ret_2
    if partial is True or partial is False or partial is None:
        partial_is_collection = False
    elif isinstance(partial, (list, tuple, set)):
        partial_is_collection = True
    else:
        # Fallback to marshmallow's is_collection for edge cases (querysets, etc.)
        partial_is_collection = marshmallow.utils.is_collection(partial)
    try:
        value = data['a']
    except:
        value = missing
    if (
                        value is not missing
                        or not(partial is True or (partial_is_collection and 'a' in partial))
                    ):
        # Inline Field.deserialize() - validate missing, handle None, call _deserialize, validate
        try:
            if value is missing:
                if field_2.required:
                    raise field_2.make_error("required")
                value = field_2.load_default
            elif value is None:
                if not field_2.allow_none:
                    raise field_2.make_error("null")
                value = None
            else:
                if not isinstance(value, Mapping):
                    raise field_2.make_error("invalid")
                result_2 = {}
                errors_2 = {}
                for key_2, val_2 in value.items():
                    key_success_3 = True
                    try:
                        if not isinstance(key_2, (str, bytes)):
                            raise a_key_key_field_5.make_error("invalid")
                        try:
                            key_2 = marshmallow.utils.ensure_text_type(key_2)
                        except UnicodeDecodeError as error:
                            raise a_key_key_field_5.make_error("invalid_utf8") from error
                        key_2 = key_2
                    except ValidationError as error:
                        errors_2[key_2] = {"key": error.messages}
                        key_success_3 = False
                    try:
                        # (value is True or value is False) is ~5x faster than isinstance(value, bool)
                        if val_2 is True or val_2 is False:
                            raise a_value_value_field_6.make_error("invalid", input=val_2)
                        try:
                            val_2 = int(val_2)
                        except (TypeError, ValueError) as error:
                            raise a_value_value_field_6.make_error("invalid", input=val_2) from error
                        except OverflowError as error:
                            raise a_value_value_field_6.make_error("too_large", input=val_2) from error
                        val_2 = val_2
                    except ValidationError as error:
                        # Only record value error if key deserialization succeeded
                        if key_success_3:
                            errors_2.setdefault(key_2, {})["value"] = error.messages
                    if key_success_3:
                        result_2[key_2] = val_2
                if errors_2:
                    raise ValidationError(errors_2, valid_data=result_2)
                value = result_2
        except ValidationError as error:
            error_store.store_error(error.messages, 'a', index=index)
            return error.valid_data if error.valid_data is not None else missing
        if value is not missing:
            ret_2['a'] = value
    if unknown != EXCLUDE:
        for key in set(data) - loaded_fields_7:
            value = data[key]
            if unknown == INCLUDE:
                ret_2[key] = value
            elif unknown == RAISE:
                error_store.store_error(
                    [self.error_messages["unknown"]],
                    key,
                    (index if index_errors else None),
                )
    return ret_2
