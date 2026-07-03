# marshmallow.fields.Nested
def _jit_serialize_SerializeNestedSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            if isinstance(value, (list, tuple)):
                result_2 = []
                for item_2 in value:
                    result_2.append(a_schema_3._serialize(item_2, many=False))
                value = result_2
            else:
                value = a_schema_3._serialize(value, many=False)
        ret_2['a'] = value
    return ret_2
