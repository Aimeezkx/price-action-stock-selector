"""Generate the S&P 500 top-300 universe from State Street's official SPY holdings."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


SOURCE_URL = (
    "https://www.ssga.com/library-content/products/fund-data/etfs/us/"
    "holdings-daily-us-en-spy.xlsx"
)
METHODOLOGY_URL = "https://www.spglobal.com/spdji/en/methodology/article/sp-us-indices-methodology/"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def read_xlsx(path: Path) -> list[list[str | float | None]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(f"{NS}si")]
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[str | float | None]] = []
    for row in sheet.findall(f".//{NS}row"):
        values: list[str | float | None] = []
        for cell in row.findall(f"{NS}c"):
            index = column_index(cell.attrib["r"])
            while len(values) <= index:
                values.append(None)
            value_node = cell.find(f"{NS}v")
            value: str | float | None = value_node.text if value_node is not None else None
            if value is not None and cell.attrib.get("t") == "s":
                value = shared[int(value)]
            elif value is not None and cell.attrib.get("t") not in {"str", "inlineStr"}:
                try:
                    value = float(value)
                except ValueError:
                    pass
            values[index] = value
        rows.append(values)
    return rows


def generate(input_path: Path, output_path: Path, limit: int = 300) -> dict:
    rows = read_xlsx(input_path)
    source_as_of = str(rows[2][1]).replace("As of ", "")
    header_index = next(
        index
        for index, row in enumerate(rows)
        if len(row) >= 2 and row[0] == "Name" and row[1] == "Ticker"
    )
    holdings = []
    for row in rows[header_index + 1 :]:
        ticker = str(row[1]).strip().upper() if len(row) > 1 and row[1] else ""
        if (
            len(row) < 5
            or not re.fullmatch(r"[A-Z][A-Z0-9.]*", ticker)
            or not isinstance(row[4], (int, float))
        ):
            continue
        holdings.append(
            {
                "name": str(row[0]).strip(),
                "symbol": ticker,
                "weight": round(float(row[4]), 6),
            }
        )
    holdings.sort(key=lambda item: item["weight"], reverse=True)
    selected = [dict(item, rank=index) for index, item in enumerate(holdings[:limit], 1)]
    payload = {
        "universe": "SP500_TOP300",
        "source": "State Street SPY daily holdings",
        "source_url": SOURCE_URL,
        "methodology_url": METHODOLOGY_URL,
        "source_as_of": source_as_of,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranking": "SPY index weight (float-adjusted market-cap weighting proxy)",
        "count": len(selected),
        "symbols": selected,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1] / "app" / "data" / "sp500_top300.json",
    )
    args = parser.parse_args()
    if args.input:
        payload = generate(args.input, args.output)
    else:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as handle:
            handle.write(content)
            handle.flush()
            payload = generate(Path(handle.name), args.output)
    print(json.dumps({"output": str(args.output), **{key: payload[key] for key in ("source_as_of", "count")}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
