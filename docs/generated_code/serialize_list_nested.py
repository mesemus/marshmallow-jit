# marshmallow.fields.List
def _jit_serialize_SerializeListSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            value_iter, value = value, []
            for item_2 in value_iter:
                if item_2 is not None:
                    if isinstance(item_2, (list, tuple)):
                        result_3 = []
                        for item_3 in item_2:
                            result_3.append(a_schema_3._serialize(item_3, many=False))
                        item_2 = result_3
                    else:
                        item_2 = a_schema_3._serialize(item_2, many=False)
                value.append(item_2)
        ret_2['a'] = value
    return ret_2
