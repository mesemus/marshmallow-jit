# marshmallow.fields.UUID
def _jit_serialize_SerializeUUIDSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            value = str(value)
        ret_2['a'] = value
    return ret_2
