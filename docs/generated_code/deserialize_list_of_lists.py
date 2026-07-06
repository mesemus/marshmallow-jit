# marshmallow.fields.List
def _jit_deserialize_SerializeListSchema_1(
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
                if not isinstance(value, list):
                    if not is_collection(value):
                        raise field_2.make_error("invalid")
                value_iter, value = value, []
                errors_2 = {}
                result_2 = []
                for idx_2, item_2 in enumerate(value_iter):
                    try:
                        if not isinstance(item_2, list):
                            if not is_collection(item_2):
                                raise a_idx_2_inner_field_5.make_error("invalid")
                        item_2_iter, item_2 = item_2, []
                        errors_3 = {}
                        result_3 = []
                        for idx_3, item_3 in enumerate(item_2_iter):
                            try:
                                # Only call ensure_text_type if needed (already a str is fast path)
                                if type(item_3) is not str:
                                    if not isinstance(item_3, (str, bytes)):
                                        raise a_idx_2__idx_3_inner_field_6.make_error("invalid")
                                    try:
                                        item_3 = marshmallow.utils.ensure_text_type(item_3)
                                    except UnicodeDecodeError as error:
                                        raise a_idx_2__idx_3_inner_field_6.make_error("invalid_utf8") from error
                                if item_3 is not missing:
                                    result_3.append(item_3)
                            except ValidationError as error:
                                if error.valid_data is not None:
                                    result_3.append(error.valid_data)
                                errors_3[idx_3] = error.messages
                        if errors_3:
                            raise ValidationError(errors_3, valid_data=result_3)
                        item_2 = result_3
                        if item_2 is not missing:
                            result_2.append(item_2)
                    except ValidationError as error:
                        if error.valid_data is not None:
                            result_2.append(error.valid_data)
                        errors_2[idx_2] = error.messages
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
