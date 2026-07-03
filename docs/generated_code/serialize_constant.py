# marshmallow.fields.Constant
def _jit_serialize_SerializeConstantSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    value = 'constant-value'
    ret_2['a'] = value
    return ret_2
