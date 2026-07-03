# marshmallow.fields.Function
def _jit_serialize_SerializeFunctionSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    value = field__a__func_3(obj)
    if value is not missing:
        ret_2['a'] = value
    return ret_2
