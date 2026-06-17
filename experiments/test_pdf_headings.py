"""Validate PDF heading detection end-to-end.

Generates a representative spec-sheet PDF with real font-size headings (18pt title,
13pt bold section heads, 11pt body) and one long section, then runs it through the
parser and the `structure` chunker to confirm:
  - headings are detected and emitted as markdown `#`
  - chunks carry the right `section` title
  - an over-long section falls back to a recursive split

Usage: python -m experiments.test_pdf_headings
"""
from __future__ import annotations

import textwrap

import fitz

from config import settings
from ingestion.chunkers import structure
from ingestion.parser import parse_file

_LONG = (
    "Planning a large rollout begins before the first device is unboxed. The "
    "reference imaging workflow uses a PXE network-boot sequence compatible with "
    "common deployment suites. Before enabling secured-core across the fleet, "
    "confirm every device meets the firmware floor: the minimum supported BIOS for "
    "secured-core operation is version 1.38, and devices below that must be updated "
    "first. Firmware management should be centralized; the recommended firmware "
    "baseline for production fleets is version 2.4.1, which aligns the self-healing "
    "BIOS behavior and supervisor password policy across models. Teams operating "
    "mixed fleets should note the update payloads are model-specific and must be "
    "staged per model. Network prerequisites are frequently underestimated: the "
    "imaging server should sit on a subnet with sufficient bandwidth, and teams "
    "imaging more than fifty devices concurrently should segment provisioning "
    "traffic onto a dedicated VLAN to avoid saturating shared links."
)

DOC = [
    ("h", "ThinkPad X1 Carbon Gen 13 Specification", 18),
    ("h", "Overview", 13),
    ("b", "The ThinkPad X1 Carbon Gen 13 is an ultralight business laptop weighing "
          "1.09 kg, built on a carbon-fiber chassis tested against 12 MIL-STD-810H methods."),
    ("h", "Battery and Power", 13),
    ("b", "Battery life is rated up to 18 hours under the MobileMark 25 benchmark. "
          "Rapid Charge restores up to 80% capacity in approximately 60 minutes."),
    ("h", "Deployment Considerations", 13),
    ("b", _LONG),
    ("h", "Security", 13),
    ("b", "Includes a discrete TPM 2.0 and a fingerprint reader in the power button."),
]


def make_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for kind, *rest in DOC:
        if kind == "h":
            text, size = rest
            if y > 740:
                page = doc.new_page()
                y = 72.0
            page.insert_text((72, y), text, fontsize=size, fontname="hebo")  # bold
            y += size * 1.9
        else:
            for line in textwrap.wrap(rest[0], width=95):
                if y > 760:
                    page = doc.new_page()
                    y = 72.0
                page.insert_text((72, y), line, fontsize=11, fontname="helv")
                y += 15
            y += 8
    doc.save(path)


def main() -> None:
    path = "/tmp/x1_spec.pdf"
    make_pdf(path)
    pages = parse_file(path)
    print(f"Parsed {len(pages)} page(s). Reconstructed markdown (page 1):\n")
    print(pages[0]["text"])

    chunks = structure(pages, {"source": "x1_spec.pdf"})
    print(f"\n--- structure chunker: {len(chunks)} chunks "
          f"(chunk_size={settings.chunk_size}) ---")
    for c in chunks:
        section = c["metadata"].get("section", "")
        print(f"  section={section!r:40} {c['text'][:55]!r}")


if __name__ == "__main__":
    main()
