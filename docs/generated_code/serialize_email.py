# marshmallow.fields.Email
def _jit_serialize_SerializeEmailSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            if type(value) is not str:
                value = marshmallow.utils.ensure_text_type(value)
        ret_2['a'] = value
    return ret_2
