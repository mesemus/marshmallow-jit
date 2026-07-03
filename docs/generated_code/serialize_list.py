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
                    item_2 = marshmallow.utils.ensure_text_type(item_2)
                value.append(item_2)
        ret_2['a'] = value
    return ret_2
