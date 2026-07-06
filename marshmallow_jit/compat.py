# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Marshmallow version compatibility utilities.

This module provides a unified API across marshmallow 3.x and 4.x,
handling differences in import paths and available features.
"""

import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from marshmallow import EXCLUDE, INCLUDE, RAISE
from marshmallow.fields import Constant, Enum, Field, List

# Detect marshmallow version by checking if Field is subscriptable (generic)
# In v3: Field is not generic
# In v4: Field is generic (Field[T])
try:
    _ = Field[Any]
    _MARSHMALLOW_MAJOR_VERSION = 4
except TypeError:
    _MARSHMALLOW_MAJOR_VERSION = 3

# In marshmallow 4, the context parameter was removed from Schema.__init__()
# Context is now completely removed from the API
HAS_CONTEXT_PARAM = _MARSHMALLOW_MAJOR_VERSION == 3

# In marshmallow 4, TimeDelta.serialization_type was removed
# TimeDelta always uses float in v4
HAS_TIMEDELTA_SERIALIZATION_TYPE = _MARSHMALLOW_MAJOR_VERSION == 3

# Type aliases for fields that work in both marshmallow 3 and 4
# In v3: These fields are not generic
# In v4: These fields are generic with type parameters
if _MARSHMALLOW_MAJOR_VERSION == 3:
    type MAField = Field  # type: ignore[misc]
    MAConstant = Constant  # type: ignore[misc]
    MAList = List  # type: ignore[misc]
    MAEnum = Enum  # type: ignore[misc]
else:
    type MAField = Field[Any]
    MAConstant = Constant[Any]
    MAList = List[Any]
    MAEnum = Enum[Any]

# Temporal parsing functions were moved in marshmallow 4
# In v3: marshmallow.utils.from_iso_datetime, from_iso_date, from_iso_time, from_rfc
# In v4: Uses built-in datetime.fromisoformat and email.utils.parsedate_to_datetime
if _MARSHMALLOW_MAJOR_VERSION == 3:
    from marshmallow.utils import (  # type: ignore[attr-defined,unresolved-import]
        from_iso_date,
        from_iso_datetime,
        from_iso_time,
        from_rfc,
    )
else:
    # Marshmallow 4 - provide compatibility wrappers
    from_iso_datetime = datetime.datetime.fromisoformat
    from_iso_date = datetime.date.fromisoformat
    from_iso_time = datetime.time.fromisoformat
    from_rfc = parsedate_to_datetime


__all__ = [
    "RAISE",
    "INCLUDE",
    "EXCLUDE",
    "_MARSHMALLOW_MAJOR_VERSION",
    "HAS_CONTEXT_PARAM",
    "HAS_TIMEDELTA_SERIALIZATION_TYPE",
    "from_iso_datetime",
    "from_iso_date",
    "from_iso_time",
    "from_rfc",
    "MAField",
    "MAConstant",
    "MAList",
    "MAEnum",
]
