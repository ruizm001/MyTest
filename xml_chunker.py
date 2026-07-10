#!/usr/bin/env python3
"""Split an XML file into smaller chunk files, or count its elements."""

import argparse
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


def chunk_xml(input_file: str, chunk_size: int, output_dir: str) -> list[str]:
    tree = ET.parse(input_file)
    root = tree.getroot()
    children = list(root)

    if not children:
        print("No child elements found under root — nothing to chunk.")
        return []

    os.makedirs(output_dir, exist_ok=True)
    output_files = []
    chunk_num = 1

    for i in range(0, len(children), chunk_size):
        batch = children[i : i + chunk_size]

        # Build a new root with the same tag and attributes
        new_root = ET.Element(root.tag, root.attrib)
        for child in batch:
            new_root.append(child)

        tree_out = ET.ElementTree(new_root)
        ET.indent(tree_out, space="  ")

        stem = Path(input_file).stem
        out_path = os.path.join(output_dir, f"{stem}_chunk_{chunk_num:03d}.xml")
        tree_out.write(out_path, encoding="unicode", xml_declaration=True)
        output_files.append(out_path)
        print(f"  Wrote {len(batch)} element(s) -> {out_path}")
        chunk_num += 1

    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="Break an XML file into smaller chunk files, or count its elements."
    )
    parser.add_argument("input", help="Path to the input XML file")
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print element counts and exit without chunking",
    )
    parser.add_argument(
        "-n",
        "--chunk-size",
        type=int,
        default=100,
        help="Number of top-level child elements per chunk (default: 100)",
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

    print(f"Parsing {args.input} ...")
    files = chunk_xml(args.input, args.chunk_size, args.output_dir)
    print(f"\nDone — {len(files)} chunk(s) written to '{args.output_dir}/'")


if __name__ == "__main__":
    main()
