# marshmallow.fields.NaiveDateTime
def _jit_deserialize_SerializeNaiveDateTimeSchema_1(
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
                try:
                    value = from_iso_datetime(value)
                except (TypeError, AttributeError, ValueError) as error:
                    raise field_2.make_error(
                        "invalid", input=value, obj_type=field_2.OBJ_TYPE
                    ) from error
                if is_aware(value):
                    if field__a__timezone_5 is None:
                        raise field_2.make_error(
                            "invalid_awareness",
                            awareness=field_2.AWARENESS,
                            obj_type=field_2.OBJ_TYPE
                        )
                    value = value.astimezone(field__a__timezone_5).replace(tzinfo=None)
        except ValidationError as error:
            error_store.store_error(error.messages, 'a', index=index)
            return error.valid_data if error.valid_data is not None else missing
        if value is not missing:
            ret_2['a'] = value
    if unknown != EXCLUDE:
        for key in set(data) - loaded_fields_6:
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
