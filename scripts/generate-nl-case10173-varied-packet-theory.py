#!/usr/bin/env python3
"""Generate a small, hash-pinned HOL4 fixture of genuine case-10173 packets.

The historical kernel/reciprocal traces and analytic-certificate capture are
untrusted preparation.  The generated theorem asks the proved word checker to
validate every supplied certificate and recompute each verdict.  Exact input
hashes, row identities, arities, and role ordering are checked here to make the
development fixture reproducible; none of those generator checks replace the
in-logic packet checks.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct


EXPECTED_KERNEL_SHA256 = (
    "a4591c1d5e93fc9fa3cfae61585d42b32f181afb69955d7dc85cebac45d55d3a"
)
EXPECTED_RECIPROCAL_SHA256 = (
    "8983a97132fc395213c6bd0ff1eb24bbe7390480ddd04a3500ce6791cd095b92"
)
EXPECTED_ANALYTIC_SHA256 = (
    "8108d47c92287232381ddd75a3bfe275063e1a4ed209a84327201f45f0819b01"
)
EXPECTED_DECIMAL_KERNEL_SHA256 = (
    "0750885c2d30cb93dbabf63b0b334ca176f17ed37e1cd6ac3c0a274baeec89a3"
)
EXPECTED_DECIMAL_RECIPROCAL_SHA256 = (
    "09994e156b5066424c73cd4389566ded3902362a0751c2f6db8b236af583fb1a"
)
EXPECTED_DECIMAL_ANALYTIC_SHA256 = (
    "793296918ef37a1ff0eca41decc3bcb6f8138f012c85640dd85133265c376959"
)
EXPECTED_DECIMAL_ROOT_SHA256 = (
    "ac3f94e1ad09dda4240809ff29638dea23150e60e9572df2a61b4567d716d4cb"
)
KERNEL_PREFIX = "CANDLE_NL_NATIVE_HISTORICAL_DIHEDRAL_KERNEL"
RECIPROCAL_PREFIX = "CANDLE_NL_NATIVE_HISTORICAL_RECIPROCAL"
FULL_CELLS = 4173
RECIPROCALS_PER_CELL = 14
COORDINATES = 6
BOX_RECIPROCAL_ORDINALS = (5, 6, 7, 8, 9, 10, 13, 11, 12)
WORD_LIMIT = 1 << 64


Interval = tuple[int, int]
Certificate = tuple[Interval, Interval, Interval, Interval, Interval]


def authenticated_lines(path: Path, expected: str, role: str) -> list[str]:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"{role} identity drift: {actual}")
    return payload.decode("ascii").splitlines()


def fields_of(line: str, prefix: str, role: str) -> dict[str, str]:
    parts = line.split()
    if not parts or parts[0] != prefix:
        raise ValueError(f"malformed {role} prefix")
    fields: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"malformed {role} field: {part}")
        key, value = part.split("=", 1)
        if key in fields:
            raise ValueError(f"duplicate {role} field: {key}")
        fields[key] = value
    return fields


def interval(text: str, context: str) -> Interval:
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"malformed interval at {context}: {text}")
    lower, upper = map(int, parts)
    if lower > upper:
        raise ValueError(f"reversed interval at {context}: {text}")
    if abs(lower) >= WORD_LIMIT or abs(upper) >= WORD_LIMIT:
        raise ValueError(f"word64 overflow at {context}: {text}")
    return lower, upper


def interval_list(text: str, count: int, context: str) -> list[Interval]:
    result = [
        interval(item, f"{context}[{index}]")
        for index, item in enumerate(text.split(","))
    ]
    if len(result) != count:
        raise ValueError(f"{context} arity drift: {len(result)} != {count}")
    return result


def signed64(value: int) -> str:
    negative = "T" if value < 0 else "F"
    return f"BoundedSigned64 {negative} {abs(value)}w"


def sml_interval(value: Interval, indent: str) -> str:
    lower, upper = value
    return (
        f"(BoundedInterval64\n"
        f"{indent}  ({signed64(lower)})\n"
        f"{indent}  ({signed64(upper)}))"
    )


def sml_list(items: list[str], indent: str) -> str:
    if not items:
        return "[]"
    separator = f";\n{indent} "
    return f"[{separator.join(items)}]"


def parse_analytic(lines: list[str]) -> list[list[Certificate]]:
    expected_rows = FULL_CELLS * COORDINATES
    if len(lines) != expected_rows:
        raise ValueError(f"analytic row count drift: {len(lines)} != {expected_rows}")
    result: list[list[Certificate]] = [[] for _ in range(FULL_CELLS)]
    for row, line in enumerate(lines):
        fields = line.split("\t")
        if len(fields) != 15:
            raise ValueError(f"analytic field-count drift at row {row}: {len(fields)}")
        cell, coordinate = map(int, fields[:2])
        if cell != row // COORDINATES or coordinate != row % COORDINATES:
            raise ValueError(f"analytic identity drift at row {row}: {cell}:{coordinate}")
        if fields[2:5] != ["sqrt", "0", "0"]:
            raise ValueError(f"analytic role drift at row {row}")
        endpoints = list(map(int, fields[5:]))
        values: list[Interval] = []
        for index in range(0, len(endpoints), 2):
            value = (endpoints[index], endpoints[index + 1])
            interval(f"{value[0]}:{value[1]}", f"analytic row {row}")
            values.append(value)
        if len(values) != 5:
            raise AssertionError("analytic certificate shape drift")
        result[cell].append((values[0], values[1], values[2], values[3], values[4]))
    return result


def sml_certificate(value: Certificate, indent: str) -> str:
    fields = [sml_interval(item, indent + "  ") for item in value]
    return "BoundedCase10173Sqrt64Certificate\n" + "\n".join(
        f"{indent}  {field}" for field in fields
    )


def sml_packet(
    kernel: dict[str, str],
    reciprocals: list[dict[str, str]],
    certificates: list[Certificate],
    indent: str,
) -> str:
    center = interval_list(kernel["center_environment"], COORDINATES, "center")
    box = interval_list(kernel["box_environment"], COORDINATES, "box")
    radii = [
        max(center_value[0] - box_value[0], box_value[1] - center_value[1])
        for center_value, box_value in zip(center, box, strict=True)
    ]
    if any(radius < 0 or radius >= WORD_LIMIT for radius in radii):
        raise ValueError("invalid derived radius")
    center_reciprocals = [interval(record["output"], "center reciprocal")
                          for record in reciprocals[:5]]
    box_reciprocals = [interval(reciprocals[ordinal]["output"], "box reciprocal")
                       for ordinal in BOX_RECIPROCAL_ORDINALS]

    fields = [
        sml_list([f"{value}w" for value in radii], indent + "  "),
        sml_list([sml_interval(value, indent + "  ") for value in center], indent + "  "),
        sml_list([sml_interval(value, indent + "  ") for value in box], indent + "  "),
        sml_list([sml_certificate(value, indent + "  ") for value in certificates],
                 indent + "  "),
        sml_interval(interval(kernel["center_root_delta"], "center root delta"), indent),
        sml_interval(interval(kernel["center_root_four_x0"], "center root four-x0"), indent),
        sml_list([sml_interval(value, indent + "  ") for value in center_reciprocals],
                 indent + "  "),
        sml_interval(interval(kernel["box_root_delta"], "box root delta"), indent),
        sml_interval(interval(kernel["box_root_four_x0"], "box root four-x0"), indent),
        sml_list([sml_interval(value, indent + "  ") for value in box_reciprocals],
                 indent + "  "),
    ]
    return "BoundedCase10173Packet\n" + "\n".join(f"{indent}  {field}" for field in fields)


def packet_values(
    kernel: dict[str, str],
    reciprocals: list[dict[str, str]],
    certificates: list[Certificate],
) -> tuple[
    list[int], list[Interval], list[Interval], list[Certificate], Interval,
    Interval, list[Interval], Interval, Interval, list[Interval]
]:
    """Return the canonical packet fields in their checked-parser order."""
    center = interval_list(kernel["center_environment"], COORDINATES, "center")
    box = interval_list(kernel["box_environment"], COORDINATES, "box")
    radii = [
        max(center_value[0] - box_value[0], box_value[1] - center_value[1])
        for center_value, box_value in zip(center, box, strict=True)
    ]
    if any(radius < 0 or radius >= WORD_LIMIT for radius in radii):
        raise ValueError("invalid derived radius")
    center_reciprocals = [
        interval(record["output"], "center reciprocal")
        for record in reciprocals[:5]
    ]
    box_reciprocals = [
        interval(reciprocals[ordinal]["output"], "box reciprocal")
        for ordinal in BOX_RECIPROCAL_ORDINALS
    ]
    return (
        radii,
        center,
        box,
        certificates,
        interval(kernel["center_root_delta"], "center root delta"),
        interval(kernel["center_root_four_x0"], "center root four-x0"),
        center_reciprocals,
        interval(kernel["box_root_delta"], "box root delta"),
        interval(kernel["box_root_four_x0"], "box root four-x0"),
        box_reciprocals,
    )


def packed_signed64(value: int) -> bytes:
    return bytes([1 if value < 0 else 0]) + struct.pack("<Q", abs(value))


def packed_interval64(value: Interval) -> bytes:
    return packed_signed64(value[0]) + packed_signed64(value[1])


def packed_packet(
    kernel: dict[str, str],
    reciprocals: list[dict[str, str]],
    certificates: list[Certificate],
) -> bytes:
    (radii, center, box, certificates, center_root_delta,
     center_root_four_x0, center_reciprocals, box_root_delta,
     box_root_four_x0, box_reciprocals) = packet_values(
        kernel, reciprocals, certificates)
    fields = [b"".join(struct.pack("<Q", value) for value in radii)]
    fields.append(b"".join(map(packed_interval64, center)))
    fields.append(b"".join(map(packed_interval64, box)))
    fields.append(b"".join(
        packed_interval64(value)
        for certificate in certificates
        for value in certificate
    ))
    fields.append(packed_interval64(center_root_delta))
    fields.append(packed_interval64(center_root_four_x0))
    fields.append(b"".join(map(packed_interval64, center_reciprocals)))
    fields.append(packed_interval64(box_root_delta))
    fields.append(packed_interval64(box_root_four_x0))
    fields.append(b"".join(map(packed_interval64, box_reciprocals)))
    result = b"".join(fields)
    if len(result) != 1128:
        raise AssertionError(f"packed packet size drift: {len(result)}")
    return result


def generate(
    kernel_path: Path,
    reciprocal_path: Path,
    analytic_path: Path,
    cells: int,
) -> str:
    if not 2 <= cells <= 16:
        raise ValueError("this focused fixture must contain between 2 and 16 cells")
    kernel_lines = authenticated_lines(
        kernel_path, EXPECTED_KERNEL_SHA256, "kernel trace")
    reciprocal_lines = authenticated_lines(
        reciprocal_path, EXPECTED_RECIPROCAL_SHA256, "reciprocal trace")
    analytic_lines = authenticated_lines(
        analytic_path, EXPECTED_ANALYTIC_SHA256, "analytic trace")
    if len(kernel_lines) != FULL_CELLS:
        raise ValueError(f"kernel row count drift: {len(kernel_lines)}")
    if len(reciprocal_lines) != FULL_CELLS * RECIPROCALS_PER_CELL:
        raise ValueError(f"reciprocal row count drift: {len(reciprocal_lines)}")
    analytic = parse_analytic(analytic_lines)

    definitions: list[str] = []
    names: list[str] = []
    for index in range(cells):
        kernel = fields_of(kernel_lines[index], KERNEL_PREFIX, f"kernel row {index}")
        if int(kernel.get("index", "-1")) != index:
            raise ValueError(f"kernel identity drift at row {index}")
        reciprocal_base = index * RECIPROCALS_PER_CELL
        reciprocals: list[dict[str, str]] = []
        for ordinal in range(RECIPROCALS_PER_CELL):
            record = fields_of(
                reciprocal_lines[reciprocal_base + ordinal],
                RECIPROCAL_PREFIX,
                f"reciprocal row {reciprocal_base + ordinal}",
            )
            if (int(record.get("index", "-1")) != index or
                    int(record.get("ordinal", "-1")) != ordinal):
                raise ValueError(f"reciprocal identity drift at {index}:{ordinal}")
            reciprocals.append(record)
        name = f"bounded_case10173_varied_packet{index}"
        names.append(name)
        packet = sml_packet(kernel, reciprocals, analytic[index], "  ")
        definitions.append(
            f"Definition {name}_def:\n"
            f"  {name} =\n"
            f"  {packet}\n"
            f"End\n"
        )

    prefix_name = f"bounded_case10173_varied_prefix{cells}"
    prefix_list = ";\n     ".join(names)
    header = f'''(*****************************************************************************
 * Mechanically generated genuine case-10173 varied-packet proof fixture.
 *
 * kernel trace:     sha256 {EXPECTED_KERNEL_SHA256}
 * reciprocal trace: sha256 {EXPECTED_RECIPROCAL_SHA256}
 * analytic trace:   sha256 {EXPECTED_ANALYTIC_SHA256}
 * cells: {cells}
 *****************************************************************************)
Theory compute_boundedCase10173VariedData
Ancestors
  compute_boundedCase10173PacketBatch
Libs
  bossLib preamble wordsLib

'''
    footer = f'''Definition {prefix_name}_def:
  {prefix_name} =
    [{prefix_list}]
End

Theorem {prefix_name}_well_shaped:
  EVERY bounded_case10173_packet_well_shaped {prefix_name}
Proof
  EVAL_TAC
QED

Theorem {prefix_name}_accepts:
  bounded_case10173_packet_batch_accepts {prefix_name}
Proof
  rw [{prefix_name}_def,
      compute_boundedCase10173PacketBatchTheory.bounded_case10173_packet_batch_accepts_def]
  >- (rw [{names[0]}_def]
      >> EVAL_TAC >> wordsLib.WORD_EVAL_TAC)
'''
    for name in names[1:]:
        footer += (
            f"  >- (rw [{name}_def]\n"
            f"      >> EVAL_TAC >> wordsLib.WORD_EVAL_TAC)\n"
        )
    footer += f'''QED

Theorem {prefix_name}_check_cv:
  bounded_case10173_packet_batch_check_cv
      (bounded_cv_encode_case10173_packet_list {prefix_name}) = SOME (Num 1)
Proof
  irule
    compute_boundedCase10173PacketBatchTheory.bounded_case10173_packet_batch_check_cv_accepts
  >> simp [{prefix_name}_well_shaped,
           {prefix_name}_accepts]
QED

val _ = export_theory ();
'''
    return header + "\n".join(definitions) + "\n" + footer


def generate_packed(
    kernel_path: Path,
    reciprocal_path: Path,
    analytic_path: Path,
    cells: int,
) -> bytes:
    if not 1 <= cells <= FULL_CELLS:
        raise ValueError(f"packed fixture must contain 1..{FULL_CELLS} cells")
    kernel_lines = authenticated_lines(
        kernel_path, EXPECTED_KERNEL_SHA256, "kernel trace")
    reciprocal_lines = authenticated_lines(
        reciprocal_path, EXPECTED_RECIPROCAL_SHA256, "reciprocal trace")
    analytic_lines = authenticated_lines(
        analytic_path, EXPECTED_ANALYTIC_SHA256, "analytic trace")
    if len(kernel_lines) != FULL_CELLS:
        raise ValueError(f"kernel row count drift: {len(kernel_lines)}")
    if len(reciprocal_lines) != FULL_CELLS * RECIPROCALS_PER_CELL:
        raise ValueError(f"reciprocal row count drift: {len(reciprocal_lines)}")
    analytic = parse_analytic(analytic_lines)

    packets: list[bytes] = []
    for index in range(cells):
        kernel = fields_of(kernel_lines[index], KERNEL_PREFIX, f"kernel row {index}")
        if int(kernel.get("index", "-1")) != index:
            raise ValueError(f"kernel identity drift at row {index}")
        reciprocal_base = index * RECIPROCALS_PER_CELL
        reciprocals: list[dict[str, str]] = []
        for ordinal in range(RECIPROCALS_PER_CELL):
            record = fields_of(
                reciprocal_lines[reciprocal_base + ordinal],
                RECIPROCAL_PREFIX,
                f"reciprocal row {reciprocal_base + ordinal}",
            )
            if (int(record.get("index", "-1")) != index or
                    int(record.get("ordinal", "-1")) != ordinal):
                raise ValueError(f"reciprocal identity drift at {index}:{ordinal}")
            reciprocals.append(record)
        packets.append(packed_packet(kernel, reciprocals, analytic[index]))

    return b"CNLCPB01" + struct.pack("<I", cells) + b"".join(packets)


def verify_decimal_roots(
    kernel_lines: list[str], root_lines: list[str]
) -> None:
    if len(root_lines) != FULL_CELLS:
        raise ValueError(f"decimal root row count drift: {len(root_lines)}")
    roles = (
        "center_root_delta",
        "center_root_four_x0",
        "box_root_delta",
        "box_root_four_x0",
    )
    for index, (kernel_line, root_line) in enumerate(
        zip(kernel_lines, root_lines, strict=True)
    ):
        kernel = fields_of(kernel_line, KERNEL_PREFIX, f"decimal kernel row {index}")
        root_fields = root_line.split()
        if len(root_fields) != 9 or int(root_fields[0]) != index:
            raise ValueError(f"decimal root identity/shape drift at row {index}")
        expected = [
            endpoint
            for role in roles
            for endpoint in interval(kernel[role], f"decimal kernel {index}:{role}")
        ]
        actual = list(map(int, root_fields[1:]))
        if actual != expected:
            raise ValueError(f"decimal root value drift at row {index}")


def generate_decimal_theory(
    kernel_path: Path,
    reciprocal_path: Path,
    analytic_path: Path,
    root_path: Path,
    cells: int,
) -> str:
    if not 1 <= cells <= 16:
        raise ValueError("decimal fixture must contain between 1 and 16 cells")
    kernel_lines = authenticated_lines(
        kernel_path, EXPECTED_DECIMAL_KERNEL_SHA256, "decimal kernel trace")
    reciprocal_lines = authenticated_lines(
        reciprocal_path,
        EXPECTED_DECIMAL_RECIPROCAL_SHA256,
        "decimal reciprocal trace",
    )
    analytic_lines = authenticated_lines(
        analytic_path, EXPECTED_DECIMAL_ANALYTIC_SHA256, "decimal analytic trace")
    root_lines = authenticated_lines(
        root_path, EXPECTED_DECIMAL_ROOT_SHA256, "authenticated decimal roots")
    if len(kernel_lines) != FULL_CELLS:
        raise ValueError(f"decimal kernel row count drift: {len(kernel_lines)}")
    if len(reciprocal_lines) != FULL_CELLS * RECIPROCALS_PER_CELL:
        raise ValueError(
            f"decimal reciprocal row count drift: {len(reciprocal_lines)}"
        )
    verify_decimal_roots(kernel_lines, root_lines)
    analytic = parse_analytic(analytic_lines)

    definitions: list[str] = []
    theorems: list[str] = []
    for index in range(cells):
        kernel = fields_of(
            kernel_lines[index], KERNEL_PREFIX, f"decimal kernel row {index}"
        )
        if int(kernel.get("index", "-1")) != index:
            raise ValueError(f"decimal kernel identity drift at row {index}")
        reciprocal_base = index * RECIPROCALS_PER_CELL
        reciprocals: list[dict[str, str]] = []
        for ordinal in range(RECIPROCALS_PER_CELL):
            record = fields_of(
                reciprocal_lines[reciprocal_base + ordinal],
                RECIPROCAL_PREFIX,
                f"decimal reciprocal row {reciprocal_base + ordinal}",
            )
            if (
                int(record.get("index", "-1")) != index
                or int(record.get("ordinal", "-1")) != ordinal
            ):
                raise ValueError(
                    f"decimal reciprocal identity drift at {index}:{ordinal}"
                )
            reciprocals.append(record)
        name = f"bounded_case10173_decimal_packet{index}"
        packet = sml_packet(kernel, reciprocals, analytic[index], "  ")
        definitions.append(
            f"Definition {name}_def:\n"
            f"  {name} =\n"
            f"  {packet}\n"
            f"End\n"
        )
        theorems.append(
            f"Theorem {name}_accepts:\n"
            f"  case {name} of\n"
            f"  | BoundedCase10173Packet radii center_environment box_environment\n"
            f"      coordinate_sqrt_certificates center_root_delta\n"
            f"      center_root_four_x0 center_reciprocals box_root_delta\n"
            f"      box_root_four_x0 box_reciprocals =>\n"
            f"      bounded_case10173_checked_cell_accepts_decimal radii\n"
            f"        center_environment box_environment coordinate_sqrt_certificates\n"
            f"        center_root_delta center_root_four_x0 center_reciprocals\n"
            f"        box_root_delta box_root_four_x0 box_reciprocals\n"
            f"Proof\n"
            f"  rw [{name}_def]\n"
            f"  >> EVAL_TAC >> wordsLib.WORD_EVAL_TAC\n"
            f"QED\n"
        )

    header = f'''(*****************************************************************************
 * Mechanically generated genuine case-10173 decimal cell fixture.
 *
 * Decimal kernel:     sha256 {EXPECTED_DECIMAL_KERNEL_SHA256}
 * Decimal reciprocal: sha256 {EXPECTED_DECIMAL_RECIPROCAL_SHA256}
 * Decimal analytic:   sha256 {EXPECTED_DECIMAL_ANALYTIC_SHA256}
 * Authenticated roots:sha256 {EXPECTED_DECIMAL_ROOT_SHA256}
 * Cells: {cells}
 *****************************************************************************)
Theory compute_boundedCase10173HistoricalCellDecimalData
Ancestors
  compute_boundedCase10173HistoricalCellDecimal
  compute_boundedCase10173Packet
Libs
  bossLib preamble wordsLib

'''
    return header + "\n".join(definitions) + "\n" + "\n".join(theorems) + (
        "\nval _ = export_theory ();\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel_trace", type=Path)
    parser.add_argument("reciprocal_trace", type=Path)
    parser.add_argument("analytic_trace", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--roots",
        type=Path,
        help="authenticated four-root fixture required by decimal-theory",
    )
    parser.add_argument("--cells", type=int, default=3)
    parser.add_argument(
        "--format",
        choices=("theory", "packed", "decimal-theory"),
        default="theory",
        help="emit an HOL4 theory fixture or the fixed-width binary batch",
    )
    args = parser.parse_args()
    if args.format == "theory":
        rendered = generate(
            args.kernel_trace,
            args.reciprocal_trace,
            args.analytic_trace,
            args.cells,
        ).encode("ascii")
    elif args.format == "packed":
        rendered = generate_packed(
            args.kernel_trace,
            args.reciprocal_trace,
            args.analytic_trace,
            args.cells,
        )
    else:
        if args.roots is None:
            parser.error("--roots is required with --format decimal-theory")
        rendered = generate_decimal_theory(
            args.kernel_trace,
            args.reciprocal_trace,
            args.analytic_trace,
            args.roots,
            args.cells,
        ).encode("ascii")
    args.output.write_bytes(rendered)
    print(f"cells={args.cells}")
    print(f"format={args.format}")
    print(f"bytes={len(rendered)}")
    print(f"sha256={hashlib.sha256(rendered).hexdigest()}")


if __name__ == "__main__":
    main()
