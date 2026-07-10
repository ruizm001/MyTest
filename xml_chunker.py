#!/usr/bin/env python3
"""Split an XML file into ~100 MB chunk files, or count its elements."""

import argparse
import io
import os
import xml.etree.ElementTree as ET
from pathlib import Path


def count_elements(input_file: str) -> dict:
    tree = ET.parse(input_file)
    root = tree.getroot()
    all_elements = list(root.iter())
    top_level = list(root)
    return {
        "total": len(all_elements),
        "top_level": len(top_level),
        "root_tag": root.tag,
    }


def element_bytes(element: ET.Element) -> int:
    buf = io.StringIO()
    ET.ElementTree(element).write(buf, encoding="unicode")
    return len(buf.getvalue().encode("utf-8"))


def chunk_xml(input_file: str, max_bytes: int, output_dir: str) -> list[str]:
    tree = ET.parse(input_file)
    root = tree.getroot()
    children = list(root)

    if not children:
        print("No child elements found under root — nothing to chunk.")
        return []

    os.makedirs(output_dir, exist_ok=True)
    output_files = []
    stem = Path(input_file).stem
    chunk_num = 1
    batch = []
    batch_bytes = 0

    def write_chunk(batch, chunk_num):
        new_root = ET.Element(root.tag, root.attrib)
        for child in batch:
            new_root.append(child)
        tree_out = ET.ElementTree(new_root)
        ET.indent(tree_out, space="  ")
        out_path = os.path.join(output_dir, f"{stem}_chunk_{chunk_num:03d}.xml")
        tree_out.write(out_path, encoding="unicode", xml_declaration=True)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"  Wrote {len(batch)} element(s) ({size_mb:.1f} MB) -> {out_path}")
        return out_path

    for child in children:
        child_size = element_bytes(child)

        if batch and batch_bytes + child_size > max_bytes:
            output_files.append(write_chunk(batch, chunk_num))
            chunk_num += 1
            batch = []
            batch_bytes = 0

        batch.append(child)
        batch_bytes += child_size

    if batch:
        output_files.append(write_chunk(batch, chunk_num))

    return output_files


def parse_size(value: str) -> int:
    value = value.strip().upper()
    if value.endswith("GB"):
        return int(float(value[:-2]) * 1024 ** 3)
    if value.endswith("MB"):
        return int(float(value[:-2]) * 1024 ** 2)
    if value.endswith("KB"):
        return int(float(value[:-2]) * 1024)
    return int(value)


def main():
    parser = argparse.ArgumentParser(
        description="Break an XML file into chunk files by size, or count its elements."
    )
    parser.add_argument("input", help="Path to the input XML file")
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print element counts and exit without chunking",
    )
    parser.add_argument(
        "-s",
        "--max-size",
        default="100MB",
        help="Maximum size per chunk file, e.g. 100MB, 50MB, 1GB (default: 100MB)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="xml_chunks",
        help="Directory to write chunk files into (default: xml_chunks/)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}")
        return

    if args.count:
        counts = count_elements(args.input)
        print(f"File               : {args.input}")
        print(f"Root element       : <{counts['root_tag']}>")
        print(f"Top-level children : {counts['top_level']}")
        print(f"Total elements     : {counts['total']}")
        return

    max_bytes = parse_size(args.max_size)
    print(f"Parsing {args.input} ...")
    print(f"Target chunk size  : {args.max_size} ({max_bytes:,} bytes)")
    files = chunk_xml(args.input, max_bytes, args.output_dir)
    print(f"\nDone -- {len(files)} chunk(s) written to '{args.output_dir}/'")


if __name__ == "__main__":
    main()
