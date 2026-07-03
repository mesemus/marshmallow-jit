# marshmallow.fields.Dict
def _jit_serialize_SerializeDictSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            value_iter, value = value, {}
            for key_2, value_2 in value_iter.items():
                if key_2 is not None:
                    key_2 = marshmallow.utils.ensure_text_type(key_2)
                if value_2 is not None:
                    value_2 = int(value_2)
                value[key_2] = value_2
        ret_2['a'] = value
    return ret_2
