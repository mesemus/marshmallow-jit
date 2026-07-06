# marshmallow.fields.Url
def _jit_deserialize_SerializeUrlSchema_1(
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
                # Only call ensure_text_type if needed (already a str is fast path)
                if type(value) is not str:
                    if not isinstance(value, (str, bytes)):
                        raise field_2.make_error("invalid")
                    try:
                        value = marshmallow.utils.ensure_text_type(value)
                    except UnicodeDecodeError as error:
                        raise field_2.make_error("invalid_utf8") from error
                validation_errors_7 = []
                validation_kwargs_8 = {}
                try:
                    _validator_self = validators_5[0]
                    if not value:
                        raise ValidationError(_validator_self._format_error(value))
                    # Check first if the scheme is valid
                    _url_scheme = None
                    if "://" in value:
                        _url_scheme = value.split("://")[0].lower()
                        if _url_scheme not in _validator_self.schemes:
                            raise ValidationError(_validator_self._format_error(value))
                    # Hostname is optional for file URLs. If absent it means `localhost`.
                    # Fill it in for the validation if needed
                    if _url_scheme == "file" and value.startswith("file:///"):
                        _url_matched = (
                            url_regex_9.search(value.replace("file:///", "file://localhost/", 1))
                        )
                    else:
                        _url_matched = url_regex_9.search(value)
                    if not _url_matched:
                        raise ValidationError(_validator_self._format_error(value))
                except ValidationError as err:
                    validation_kwargs_8.update(err.kwargs)
                    if isinstance(err.messages, dict):
                        validation_errors_7.append(err.messages)
                    else:
                        validation_errors_7.extend(err.messages)
                if validation_errors_7:
                    raise ValidationError(validation_errors_7, **validation_kwargs_8)
        except ValidationError as error:
            error_store.store_error(error.messages, 'a', index=index)
            return error.valid_data if error.valid_data is not None else missing
        if value is not missing:
            ret_2['a'] = value
    if unknown != EXCLUDE:
        for key in set(data) - loaded_fields_10:
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
