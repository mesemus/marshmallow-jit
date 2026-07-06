# marshmallow.fields.TimeDelta
def _jit_serialize_SerializeTimeDeltaSchema_1(self, obj: typing.Any, *, many: bool = False) -> dict[str, typing.Any]:
    if many and obj is not None:
        return [self._serialize(d, many=False) for d in obj]
    ret_2 = {}
    try:
        value = obj['a']
    except KeyError:
        value = missing
    if value is not missing:
        if value is not None:
            base_unit = __import__('datetime').timedelta(**{'seconds': 1})
            delta = marshmallow.utils.timedelta_to_microseconds(value)
            unit = marshmallow.utils.timedelta_to_microseconds(base_unit)
            value = delta // unit
        ret_2['a'] = value
    return ret_2
