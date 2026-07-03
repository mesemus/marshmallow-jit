# marshmallow.fields.Tuple
def _jit_serialize_SerializeTupleSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    value = a__field_3.serialize('a', obj, accessor=self.get_attribute)
    if value is not missing:
        ret_2['a'] = value
    return ret_2
