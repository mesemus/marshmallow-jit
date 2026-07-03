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
                        if item_2 is missing:
                            if a_idx_2_inner_field_5.required:
                                raise a_idx_2_inner_field_5.make_error("required")
                            item_2 = a_idx_2_inner_field_5.load_default
                        if item_2 is missing:
                            return item_2
                        if item_2 is not None:
                            if partial is True or partial is False or partial is None:
                                partial_is_collection = False
                                nested_partial = partial
                            elif isinstance(partial, (list, tuple, set)):
                                partial_is_collection = True
                                prefix = 'a[idx_2]' + "."
                                len_prefix = len(prefix)
                                nested_partial = [f[len_prefix:] for f in partial if f.startswith(prefix)]
                            else:
                                # Fallback to marshmallow's is_collection for edge cases (querysets, etc.)
                                partial_is_collection = marshmallow.utils.is_collection(partial)
                                if partial_is_collection:
                                    prefix = 'a[idx_2]' + "."
                                    len_prefix = len(prefix)
                                    nested_partial = [f[len_prefix:] for f in partial if f.startswith(prefix)]
                                elif partial is not None:
                                    nested_partial = partial
                                else:
                                    nested_partial = None
                            if isinstance(item_2, (list, tuple)):
                                result_3 = []
                                for item_3 in item_2:
                                    result_3.append(varaidxschema_dmFyX2FbaWR4XzJdX3NjaGVtYV82.load(
                                        item_3, unknown=a_idx_2_inner_field_5.unknown, partial=nested_partial
                                    ))
                                item_2 = result_3
                            else:
                                item_2 = varaidxschema_dmFyX2FbaWR4XzJdX3NjaGVtYV82.load(
                                    item_2, unknown=a_idx_2_inner_field_5.unknown, partial=nested_partial
                                )
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
