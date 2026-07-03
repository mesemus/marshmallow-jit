# marshmallow.fields.Method
def _jit_serialize_SerializeMethodSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    value = self.test_method(obj)
    if value is not missing:
        ret_2['a'] = value
    return ret_2
