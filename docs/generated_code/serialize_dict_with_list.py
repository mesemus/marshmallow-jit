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
            value_iter = value
            value_keys = {}
            for key_2 in value_iter:
                key_2_serialized = key_2
                if key_2_serialized is not None:
                    if type(key_2_serialized) is not str:
                        key_2_serialized = marshmallow.utils.ensure_text_type(key_2_serialized)
                value_keys[key_2] = key_2_serialized
            value = {}
            for key_2, value_2 in value_iter.items():
                if key_2 in value_keys:
                    key_2_final = value_keys[key_2]
                    if value_2 is not None:
                        value_2_iter, value_2 = value_2, []
                        for item_3 in value_2_iter:
                            if item_3 is not None:
                                if type(item_3) is not str:
                                    item_3 = marshmallow.utils.ensure_text_type(item_3)
                            value_2.append(item_3)
                    value[key_2_final] = value_2
        ret_2['a'] = value
    return ret_2
