# marshmallow.fields.Method
def _jit_deserialize_SerializeMethodSchema_1(
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
    if unknown != EXCLUDE:
        for key in set(data) - loaded_fields_2:
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
