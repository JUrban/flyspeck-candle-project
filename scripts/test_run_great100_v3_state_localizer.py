#!/usr/bin/env python3
"""Focused tests for candidate-V3 chunked state transport."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def _load_localizer():
    path = SCRIPT_DIR / "run-great100-v3-state-localizer.py"
    spec = importlib.util.spec_from_file_location("great100_v3_state", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


localizer = _load_localizer()
canonical = localizer.canonical


def _identity(value: bytes) -> dict:
    return {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}


def _components():
    return {
        "type_constants": canonical.encode_node(
            b"list", [canonical.encode_node(b"type", [b"bool", b"0"])]),
        "term_constants": canonical.encode_node(b"list", []),
        "definitions": canonical.encode_node(
            b"list", [canonical.encode_node(b"theorem", [
                canonical.encode_node(b"list", []), b"definition"])]),
        "global_axioms": canonical.encode_node(
            b"list", [b"axiom-1", b"axiom-2", b"axiom-3"]),
    }


def _stream_lines(components, counts=(1, 0, 1, 3), chunk_bytes=5):
    kernel = canonical.encode_node(
        b"kernel-state",
        [components[name] for name in localizer.STREAM_COMPONENTS])
    lengths = [len(components[name]) for name in localizer.STREAM_COMPONENTS]
    yield b"\t".join([
        localizer.STREAM_BEGIN,
        str(len(kernel)).encode("ascii"),
        *(str(length).encode("ascii") for length in lengths),
        *(str(count).encode("ascii") for count in counts),
    ])
    for name in localizer.STREAM_COMPONENTS:
        value = components[name]
        encoded_name = name.encode("ascii")
        yield b"\t".join([
            localizer.STREAM_COMPONENT_BEGIN,
            encoded_name,
            str(len(value)).encode("ascii"),
        ])
        chunks = [
            value[offset:offset + chunk_bytes]
            for offset in range(0, len(value), chunk_bytes)
        ]
        for sequence, chunk in enumerate(chunks):
            yield b"\t".join([
                localizer.STREAM_CHUNK,
                encoded_name,
                str(sequence).encode("ascii"),
                chunk.hex().encode("ascii"),
            ])
        yield b"\t".join([
            localizer.STREAM_COMPONENT_END,
            encoded_name,
            str(len(value)).encode("ascii"),
            str(len(chunks)).encode("ascii"),
        ])
    yield localizer.STREAM_END


class StateStreamReaderTests(unittest.TestCase):
    def test_reconstructs_exact_kernel_and_components(self):
        components = _components()
        reader = localizer._StateStreamReader()
        for line in _stream_lines(components):
            fields = line.split(b"\t")
            marker = fields[0]
            if marker == localizer.STREAM_BEGIN:
                reader.begin(fields)
            elif marker == localizer.STREAM_COMPONENT_BEGIN:
                reader.component_begin(fields)
            elif marker == localizer.STREAM_CHUNK:
                reader.chunk(fields)
            elif marker == localizer.STREAM_COMPONENT_END:
                reader.component_end(fields)
            else:
                self.assertEqual(marker, localizer.STREAM_END)
                reader.end(fields)
        observed = reader.finish()
        kernel = canonical.encode_node(
            b"kernel-state",
            [components[name] for name in localizer.STREAM_COMPONENTS])
        self.assertEqual(observed["kernel_state"], _identity(kernel))
        for name, value in components.items():
            self.assertEqual(observed[name], _identity(value))
        self.assertEqual(
            tuple(observed[name] for name in (
                "type_constant_count", "term_constant_count",
                "definition_count", "global_axiom_count")),
            (1, 0, 1, 3))

    def test_rejects_out_of_order_component(self):
        reader = localizer._StateStreamReader()
        first = next(_stream_lines(_components())).split(b"\t")
        reader.begin(first)
        with self.assertRaisesRegex(canonical.WireError, "out-of-order"):
            reader.component_begin([
                localizer.STREAM_COMPONENT_BEGIN, b"definitions", b"0"])

    def test_rejects_chunk_sequence_gap(self):
        components = _components()
        lines = iter(_stream_lines(components))
        reader = localizer._StateStreamReader()
        reader.begin(next(lines).split(b"\t"))
        reader.component_begin(next(lines).split(b"\t"))
        fields = next(lines).split(b"\t")
        fields[2] = b"1"
        with self.assertRaisesRegex(canonical.WireError, "sequence mismatch"):
            reader.chunk(fields)

    def test_rejects_declared_kernel_length_mismatch(self):
        components = _components()
        lines = list(_stream_lines(components))
        begin = lines[0].split(b"\t")
        begin[1] = str(int(begin[1]) + 1).encode("ascii")
        lines[0] = b"\t".join(begin)
        reader = localizer._StateStreamReader()
        for line in lines:
            fields = line.split(b"\t")
            marker = fields[0]
            if marker == localizer.STREAM_BEGIN:
                reader.begin(fields)
            elif marker == localizer.STREAM_COMPONENT_BEGIN:
                reader.component_begin(fields)
            elif marker == localizer.STREAM_CHUNK:
                reader.chunk(fields)
            elif marker == localizer.STREAM_COMPONENT_END:
                reader.component_end(fields)
            else:
                reader.end(fields)
        with self.assertRaisesRegex(canonical.WireError, "kernel length"):
            reader.finish()

    def test_reads_theorem_and_stream_identity(self):
        components = _components()
        hypotheses = canonical.encode_node(b"list", [])
        conclusion = canonical.encode_node(b"constant", [b"T", b"bool"])
        theorem = canonical.encode_node(b"theorem", [hypotheses, conclusion])
        theorem_line = b"\t".join([
            canonical.V3_THEOREM_MARKER,
            b"TEST_THEOREM".hex().encode("ascii"),
            theorem.hex().encode("ascii"),
            hypotheses.hex().encode("ascii"),
            conclusion.hex().encode("ascii"),
            components["global_axioms"].hex().encode("ascii"),
            b"0", b"3",
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.log"
            path.write_bytes(
                b"noise\n" + theorem_line + b"\n" +
                b"\n".join(_stream_lines(components)) + b"\n")
            observed = localizer._read_v3_identity(path, ["TEST_THEOREM"])
        self.assertEqual(observed["theorems"][0]["theorem"], _identity(theorem))
        self.assertEqual(
            observed["post_state"]["global_axioms"],
            _identity(components["global_axioms"]))


if __name__ == "__main__":
    unittest.main()
