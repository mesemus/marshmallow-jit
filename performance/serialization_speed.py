# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Benchmarks JIT-compiled schema serialization against plain marshmallow.

For every field type in FIELD_SPECS, and for schemas with 1/10/50/100 fields of that
type, this script measures:

  - schema *instantiation* time (this is where marshmallow-jit generates and compiles
    the serializer function, so it is the main source of JIT overhead)
  - schema.dump() time for valid, invalid and missing data

...twice: once for a plain marshmallow schema, once for the same schema with the JIT
mixin applied. This is repeated for all three serializers ("mapping", "instance",
"hybrid" - for "hybrid", both dict and instance sources are tried, since that
serializer is meant to support both).

Run with:
    python -m performance.serialization_speed [--quick] [--repeats N] ...

Adding a new field to benchmark only requires appending a FieldSpec to FIELD_SPECS.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import decimal
import ipaddress
import time
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from marshmallow import Schema
from marshmallow.fields import (
    IP,
    UUID,
    AwareDateTime,
    Boolean,
    Constant,
    Date,
    DateTime,
    Decimal,
    Dict,
    Email,
    Enum,
    Field,
    Float,
    Function,
    Integer,
    IPInterface,
    IPv4,
    IPv4Interface,
    IPv6,
    IPv6Interface,
    List,
    Method,
    NaiveDateTime,
    Nested,
    Raw,
    Str,
    Time,
    TimeDelta,
    Url,
)
from tqdm import tqdm

from marshmallow_jit.schema import JITSchemaMixin

# ---------------------------------------------------------------------------
# Field types under benchmark - add new fields/inliners here as they're implemented.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class FieldSpec:
    """One field type/configuration to benchmark.

    `valid_value` and `invalid_value` are used, unchanged, for *every* field in the
    generated schema (a schema with field_count=100 gets the same value 100 times) -
    this benchmark is about the cost of the code path, not about varied data.
    """

    id: str
    factory: Callable[[], Field]
    valid_value: Any
    invalid_value: Any


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("str", Str, "hello world", b"\xff\xfe"),
    FieldSpec("url", Url, "https://example.com", b"\xff\xfe"),
    FieldSpec("email", Email, "a@b.com", b"\xff\xfe"),
    FieldSpec("uuid", UUID, uuid.uuid4(), "not-a-uuid-object"),
    FieldSpec("integer", Integer, 42, "not-a-number"),
    FieldSpec("float", Float, 3.14, "not-a-number"),
    FieldSpec("decimal", Decimal, decimal.Decimal("1.23"), "not-a-number"),
    FieldSpec("boolean", Boolean, True, object()),
    FieldSpec("datetime", DateTime, dt.datetime(2024, 1, 2, 3, 4, 5), "not-a-date"),
    FieldSpec("naive_datetime", NaiveDateTime, dt.datetime(2024, 1, 2), "not-a-date"),
    FieldSpec("aware_datetime", AwareDateTime, dt.datetime(2024, 1, 2, tzinfo=dt.UTC), "not-a-date"),
    FieldSpec("time", Time, dt.time(3, 4, 5), "not-a-time"),
    FieldSpec("date", Date, dt.date(2024, 1, 2), "not-a-date"),
    FieldSpec("timedelta", TimeDelta, dt.timedelta(days=1, hours=2), "not-a-timedelta"),
    FieldSpec("ip", IP, ipaddress.ip_address("127.0.0.1"), "not-an-ip"),
    FieldSpec("ipv4", IPv4, ipaddress.IPv4Address("127.0.0.1"), "not-an-ip"),
    FieldSpec("ipv6", IPv6, ipaddress.IPv6Address("::1"), "not-an-ip"),
    FieldSpec("ip_interface", IPInterface, ipaddress.ip_interface("192.168.0.2/24"), "not-an-interface"),
    FieldSpec("ipv4_interface", IPv4Interface, ipaddress.IPv4Interface("192.168.0.2/24"), "not-an-interface"),
    FieldSpec("ipv6_interface", IPv6Interface, ipaddress.IPv6Interface("::1/128"), "not-an-interface"),
    # Additional field types with inliners
    FieldSpec("constant", lambda: Constant(42), "ignored", 999),
    FieldSpec(
        "enum",
        lambda: Enum(__import__("enum").Enum("TestEnum", {"RED": "red", "GREEN": "green"})),
        "RED",
        "not-an-enum-member",
    ),
    FieldSpec("list", lambda: List(Str()), ["a", "b", "c"], 42),
    FieldSpec("dict", lambda: Dict(keys=Str(), values=Integer()), {"x": 1, "y": 2}, "not-a-dict"),
    FieldSpec(
        "nested",
        lambda: Nested(type("_TempSchema", (Schema,), {"id": Integer(), "name": Str()})),
        {"id": 1, "name": "foo"},
        "not-a-dict",
    ),
    # Method and Function fields require callables - they have specialized inliners
    FieldSpec("method", Method, "ignored-value", 5),
    FieldSpec("function", lambda: Function(serialize=lambda obj: "called"), "ignored", 5),
    # Raw field - passes values through without transformation
    FieldSpec("raw", Raw, "hello", 42),
    # Composite field types (nested structures)
    FieldSpec("list_of_lists", lambda: List(List(Str())), [["a", "b"], ["c"]], 42),
    FieldSpec(
        "list_of_nested",
        lambda: List(Nested(type("_InnerSchema", (Schema,), {"id": Integer(), "name": Str()}))),
        [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
        "not-a-list",
    ),
    FieldSpec(
        "dict_of_nested",
        lambda: Dict(keys=Str(), values=Nested(type("_InnerSchema2", (Schema,), {"id": Integer(), "name": Str()}))),
        {"x": {"id": 1, "name": "a"}, "y": {"id": 2, "name": "b"}},
        "not-a-dict",
    ),
]

FIELD_COUNTS: tuple[int, ...] = (1, 10, 50, 100)
SERIALIZER_KINDS: tuple[str, ...] = ("mapping", "instance", "hybrid")
DATA_KINDS: tuple[str, ...] = ("valid", "invalid", "missing")

# which source object shape(s) each serializer is exercised with
SOURCE_KINDS_BY_SERIALIZER: dict[str, tuple[str, ...]] = {
    "mapping": ("dict",),
    "instance": ("instance",),
    "hybrid": ("dict", "instance"),
}


# ---------------------------------------------------------------------------
# Schema and data builders
# ---------------------------------------------------------------------------


class AttributeSource:
    """A plain attribute-holding object, for the "instance" and "hybrid" source kinds."""


def field_names(field_count: int) -> list[str]:
    return [f"f{i}" for i in range(field_count)]


def build_schema_class(spec: FieldSpec, field_count: int, *, jit: bool, serializer_kind: str) -> type[Schema]:
    """Build a schema class with the given field spec.

    For nested fields, creates inner schemas that are also JIT-compiled when jit=True,
    ensuring we measure the true performance of nested JIT serialization.
    """

    # Helper to create an inner schema (for Nested fields)
    def make_inner_schema(jit_inner: bool) -> Schema:
        inner_ns = {"id": Integer(), "name": Str()}
        if jit_inner:
            inner_ns["Meta"] = type("Meta", (), {"jit_options": {"serializer": serializer_kind}})
            inner_bases = (JITSchemaMixin, Schema)
            inner_name = f"_InnerJIT_{spec.id}_{serializer_kind}"
        else:
            inner_bases = (Schema,)
            inner_name = f"_InnerPlain_{spec.id}"
        return types.new_class(inner_name, inner_bases, exec_body=lambda ns: ns.update(inner_ns))()

    # Build the field factory, handling nested fields specially
    def field_factory():
        # For nested-related specs, create the field with the appropriate inner schema
        if spec.id == "nested":
            return Nested(make_inner_schema(jit))
        elif spec.id == "list_of_nested":
            return List(Nested(make_inner_schema(jit)))
        elif spec.id == "dict_of_nested":
            return Dict(keys=Str(), values=Nested(make_inner_schema(jit)))
        else:
            return spec.factory()

    namespace: dict[str, Any] = {name: field_factory() for name in field_names(field_count)}
    if jit:
        namespace["Meta"] = type("Meta", (), {"jit_options": {"serializer": serializer_kind}})
        bases = (JITSchemaMixin, Schema)
        class_name = f"JIT_{spec.id}_{field_count}_{serializer_kind}"
    else:
        bases = (Schema,)
        class_name = f"Plain_{spec.id}_{field_count}"
    return types.new_class(class_name, bases, exec_body=lambda ns: ns.update(namespace))


def build_source(field_count: int, value: Any, data_kind: str, source_kind: str) -> dict[str, Any] | AttributeSource:
    """Builds the object to dump(): a dict or an attribute-holder, with all fields set to
    `value`, or none of them set at all for the "missing" data kind."""
    names = field_names(field_count) if data_kind != "missing" else []
    if source_kind == "dict":
        return dict.fromkeys(names, value)
    obj = AttributeSource()
    for name in names:
        setattr(obj, name, value)
    return obj


def value_for_data_kind(spec: FieldSpec, data_kind: str) -> Any:
    if data_kind == "valid":
        return spec.valid_value
    if data_kind == "invalid":
        return spec.invalid_value
    if data_kind == "missing":
        return None  # unused - build_source() omits all fields for "missing"
    raise ValueError(f"Unknown data kind: {data_kind}")


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TimingStats:
    repeats: int
    batch_size: int
    min_ms: float
    mean_ms: float
    max_ms: float

    @classmethod
    def from_per_call_ms_samples(cls, samples: list[float], batch_size: int) -> TimingStats:
        return cls(
            repeats=len(samples),
            batch_size=batch_size,
            min_ms=min(samples),
            mean_ms=sum(samples) / len(samples),
            max_ms=max(samples),
        )


def time_calls(fn: Callable[[], Any], *, repeats: int, batch_size: int) -> tuple[TimingStats, bool]:
    """Calls fn() `batch_size` times per repeat, `repeats` times over, and returns
    per-call millisecond stats plus whether fn() ever raised (errors are swallowed so
    a single repeat can't abort the whole measurement - we still want the timing)."""
    raised = False
    per_call_ms_samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(batch_size):
            try:
                fn()
            except Exception:  # noqa: BLE001 - we're timing failure paths too, not handling them
                raised = True
        elapsed = time.perf_counter() - start
        per_call_ms_samples.append((elapsed / batch_size) * 1000)
    return TimingStats.from_per_call_ms_samples(per_call_ms_samples, batch_size), raised


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BenchmarkRow:
    """One (variant, source_kind, data_kind) measurement - an intermediate result, merged
    pairwise (plain + jit) into a ComparisonRow before being reported."""

    field_id: str
    field_count: int
    serializer_kind: str
    source_kind: str
    data_kind: str
    variant: str  # "plain" or "jit"
    instantiate: TimingStats
    dump: TimingStats
    load: TimingStats | None
    dump_raised: bool
    load_raised: bool


@dataclasses.dataclass(frozen=True)
class ComparisonRow:
    """Plain vs. JIT for one (field_id, field_count, serializer_kind, source_kind,
    data_kind), with matching values placed in adjacent columns for easy plotting."""

    field_id: str
    field_count: int
    serializer_kind: str
    source_kind: str
    data_kind: str
    plain_instantiate_mean_ms: float
    jit_instantiate_mean_ms: float
    plain_dump_mean_ms: float
    jit_dump_mean_ms: float
    plain_load_mean_ms: float | None
    jit_load_mean_ms: float | None
    dump_speedup: float
    load_speedup: float | None
    plain_dump_raised: bool
    jit_dump_raised: bool
    plain_load_raised: bool
    jit_load_raised: bool

    CSV_FIELDS = (
        "field_id",
        "field_count",
        "serializer_kind",
        "source_kind",
        "data_kind",
        "plain_instantiate_mean_ms",
        "jit_instantiate_mean_ms",
        "plain_dump_mean_ms",
        "jit_dump_mean_ms",
        "plain_load_mean_ms",
        "jit_load_mean_ms",
        "dump_speedup",
        "load_speedup",
        "plain_dump_raised",
        "jit_dump_raised",
        "plain_load_raised",
        "jit_load_raised",
    )

    def as_csv_row(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "field_count": self.field_count,
            "serializer_kind": self.serializer_kind,
            "source_kind": self.source_kind,
            "data_kind": self.data_kind,
            "plain_instantiate_mean_ms": round(self.plain_instantiate_mean_ms, 5),
            "jit_instantiate_mean_ms": round(self.jit_instantiate_mean_ms, 5),
            "plain_dump_mean_ms": round(self.plain_dump_mean_ms, 5),
            "jit_dump_mean_ms": round(self.jit_dump_mean_ms, 5),
            "plain_load_mean_ms": round(self.plain_load_mean_ms, 5) if self.plain_load_mean_ms is not None else "",
            "jit_load_mean_ms": round(self.jit_load_mean_ms, 5) if self.jit_load_mean_ms is not None else "",
            "dump_speedup": round(self.dump_speedup, 5),
            "load_speedup": round(self.load_speedup, 5) if self.load_speedup is not None else "",
            "plain_dump_raised": self.plain_dump_raised,
            "jit_dump_raised": self.jit_dump_raised,
            "plain_load_raised": self.plain_load_raised,
            "jit_load_raised": self.jit_load_raised,
        }


def merge_variant_rows(plain_rows: list[BenchmarkRow], jit_rows: list[BenchmarkRow]) -> list[ComparisonRow]:
    """Pairs up the plain/jit BenchmarkRows sharing the same (source_kind, data_kind)."""
    jit_by_key = {(row.source_kind, row.data_kind): row for row in jit_rows}
    merged = []
    for plain in plain_rows:
        jit = jit_by_key[(plain.source_kind, plain.data_kind)]
        dump_speedup = plain.dump.mean_ms / jit.dump.mean_ms if jit.dump.mean_ms else float("nan")

        load_mean_plain = plain.load.mean_ms if plain.load else None
        load_mean_jit = jit.load.mean_ms if jit.load else None
        load_speedup = (
            load_mean_plain / load_mean_jit
            if load_mean_plain is not None and load_mean_jit and load_mean_jit > 0
            else None
        )

        merged.append(
            ComparisonRow(
                field_id=plain.field_id,
                field_count=plain.field_count,
                serializer_kind=plain.serializer_kind,
                source_kind=plain.source_kind,
                data_kind=plain.data_kind,
                plain_instantiate_mean_ms=plain.instantiate.mean_ms,
                jit_instantiate_mean_ms=jit.instantiate.mean_ms,
                plain_dump_mean_ms=plain.dump.mean_ms,
                jit_dump_mean_ms=jit.dump.mean_ms,
                plain_load_mean_ms=load_mean_plain,
                jit_load_mean_ms=load_mean_jit,
                dump_speedup=dump_speedup,
                load_speedup=load_speedup,
                plain_dump_raised=plain.dump_raised,
                jit_dump_raised=jit.dump_raised,
                plain_load_raised=plain.load_raised if plain.load else False,
                jit_load_raised=jit.load_raised if jit.load else False,
            )
        )
    return merged


@dataclasses.dataclass(frozen=True)
class BenchmarkConfig:
    instantiate_repeats: int = 3
    instantiate_batch_size: int = 5
    dump_repeats: int = 3
    dump_batch_size: int = 30
    field_counts: tuple[int, ...] = FIELD_COUNTS

    @classmethod
    def quick(cls) -> BenchmarkConfig:
        return cls(
            instantiate_repeats=2,
            instantiate_batch_size=2,
            dump_repeats=2,
            dump_batch_size=5,
            field_counts=(1, 10),
        )


def iter_cases(config: BenchmarkConfig) -> Iterator[tuple[FieldSpec, int, str]]:
    """Yields (field_spec, field_count, serializer_kind) - the granularity at which
    schema instantiation is measured (once per variant); each case then covers several
    (source_kind, data_kind) dump measurements."""
    for spec in FIELD_SPECS:
        for field_count in config.field_counts:
            for serializer_kind in SERIALIZER_KINDS:
                yield spec, field_count, serializer_kind


def run_case(
    spec: FieldSpec, field_count: int, serializer_kind: str, variant: str, config: BenchmarkConfig
) -> list[BenchmarkRow]:
    jit = variant == "jit"
    schema_class = build_schema_class(spec, field_count, jit=jit, serializer_kind=serializer_kind)

    instantiate_stats, _ = time_calls(
        lambda: schema_class(),
        repeats=config.instantiate_repeats,
        batch_size=config.instantiate_batch_size,
    )

    rows = []
    for source_kind in SOURCE_KINDS_BY_SERIALIZER[serializer_kind]:
        for data_kind in DATA_KINDS:
            schema = schema_class()
            value = value_for_data_kind(spec, data_kind)
            source = build_source(field_count, value, data_kind, source_kind)
            dump_stats, dump_raised = time_calls(
                lambda schema=schema, source=source: schema.dump(source),
                repeats=config.dump_repeats,
                batch_size=config.dump_batch_size,
            )

            # Profile schema.load() as well
            if source_kind == "dict" and not dump_raised:
                try:
                    dumped = schema.dump(source)
                    load_stats, load_raised = time_calls(
                        lambda schema=schema, data=dumped: schema.load(data),
                        repeats=config.dump_repeats,
                        batch_size=config.dump_batch_size,
                    )
                except Exception:  # noqa: BLE001 - load may raise for invalid data
                    load_stats = None
                    load_raised = True
            else:
                # For object sources, we can't easily test load since it expects dict-like input
                # Also skip if dump already raised
                load_stats = None
                load_raised = False

            rows.append(
                BenchmarkRow(
                    field_id=spec.id,
                    field_count=field_count,
                    serializer_kind=serializer_kind,
                    source_kind=source_kind,
                    data_kind=data_kind,
                    variant=variant,
                    instantiate=instantiate_stats,
                    dump=dump_stats,
                    load=load_stats,
                    dump_raised=dump_raised,
                    load_raised=load_raised,
                )
            )
    return rows


def run_all(config: BenchmarkConfig) -> dict[str, list[ComparisonRow]]:
    results: dict[str, list[ComparisonRow]] = {kind: [] for kind in SERIALIZER_KINDS}
    cases = list(iter_cases(config))
    for spec, field_count, serializer_kind in tqdm(cases, desc="Benchmarking", unit="case"):
        plain_rows = run_case(spec, field_count, serializer_kind, "plain", config)
        jit_rows = run_case(spec, field_count, serializer_kind, "jit", config)
        results[serializer_kind].extend(merge_variant_rows(plain_rows, jit_rows))
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_csv(rows: list[ComparisonRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ComparisonRow.CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv_row())


def print_summary(serializer_kind: str, rows: list[ComparisonRow]) -> None:
    print(f"\n=== {serializer_kind} ===")
    header = (
        f"{'fields':>7} | {'plain instantiate ms':>20} | {'jit instantiate ms':>19} "
        f"| {'plain dump ms':>13} | {'jit dump ms':>11} | {'dump spd':>8} "
        f"| {'plain load ms':>13} | {'jit load ms':>11} | {'load spd':>8}"
    )
    print(header)
    print("-" * len(header))
    for field_count in sorted({row.field_count for row in rows}):
        group = [row for row in rows if row.field_count == field_count]

        plain_instantiate = _mean([row.plain_instantiate_mean_ms for row in group])
        jit_instantiate = _mean([row.jit_instantiate_mean_ms for row in group])
        plain_dump = _mean([row.plain_dump_mean_ms for row in group])
        jit_dump = _mean([row.jit_dump_mean_ms for row in group])
        dump_speedup = plain_dump / jit_dump if jit_dump else float("nan")

        plain_load_vals = [row.plain_load_mean_ms for row in group if row.plain_load_mean_ms is not None]
        jit_load_vals = [row.jit_load_mean_ms for row in group if row.jit_load_mean_ms is not None]
        plain_load = _mean(plain_load_vals) if plain_load_vals else None
        jit_load = _mean(jit_load_vals) if jit_load_vals else None
        load_speedup = plain_load / jit_load if plain_load and jit_load and jit_load > 0 else None

        plain_load_str = f"{plain_load:>13.4f}" if plain_load is not None else "         N/A"
        jit_load_str = f"{jit_load:>11.4f}" if jit_load is not None else "        N/A"
        load_speedup_str = f"{load_speedup:>6.2f}x" if load_speedup is not None else "     N/A"

        print(
            f"{field_count:>7} | {plain_instantiate:>20.4f} | {jit_instantiate:>19.4f} "
            f"| {plain_dump:>13.4f} | {jit_dump:>11.4f} | {dump_speedup:>6.2f}x "
            f"| {plain_load_str} | {jit_load_str} | {load_speedup_str}"
        )

    raised_rows = [
        row
        for row in rows
        if row.plain_dump_raised or row.jit_dump_raised or row.plain_load_raised or row.jit_load_raised
    ]
    if raised_rows:
        print(f"({len(raised_rows)} row(s) had a dump()/load() that raised - expected for data_kind='invalid')")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="Use a small, fast configuration for smoke-testing.")
    parser.add_argument("--instantiate-repeats", type=int, default=None)
    parser.add_argument("--instantiate-batch-size", type=int, default=None)
    parser.add_argument("--dump-repeats", type=int, default=None)
    parser.add_argument("--dump-batch-size", type=int, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directory to write the per-serializer CSV files into.",
    )
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> BenchmarkConfig:
    config = BenchmarkConfig.quick() if args.quick else BenchmarkConfig()
    overrides = {
        key: getattr(args, key)
        for key in ("instantiate_repeats", "instantiate_batch_size", "dump_repeats", "dump_batch_size")
        if getattr(args, key) is not None
    }
    return dataclasses.replace(config, **overrides) if overrides else config


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = build_config(args)

    results = run_all(config)

    for serializer_kind, rows in results.items():
        write_csv(rows, args.output_dir / f"serialization_speed_{serializer_kind}.csv")

    for serializer_kind, rows in results.items():
        print_summary(serializer_kind, rows)

    print(f"\nDetailed CSV files written to {args.output_dir}/")


if __name__ == "__main__":
    main()
