"""Small, reusable data-cleaning helpers for CSV and Excel datasets."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import pandas as pd


def normalize_column_names(columns: Iterable[object]) -> list[str]:
    """Return readable snake_case column names, making duplicates unique."""
    normalized: list[str] = []
    used: set[str] = set()

    for raw_name in columns:
        name = "" if raw_name is None else str(raw_name)
        name = name.strip().lower()
        name = re.sub(r"[^\w]+", "_", name, flags=re.UNICODE)
        name = re.sub(r"_+", "_", name).strip("_") or "column"

        candidate = name
        suffix = 2
        while candidate in used:
            candidate = f"{name}_{suffix}"
            suffix += 1

        normalized.append(candidate)
        used.add(candidate)

    return normalized


def clean_dataframe(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Trim text, normalize headers, and remove fully blank and duplicate rows.

    The input DataFrame is not modified. Rows containing some missing values are
    kept; only rows that are entirely blank are removed.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")

    cleaned = dataframe.copy(deep=True)
    input_rows = len(cleaned)
    cleaned.columns = normalize_column_names(cleaned.columns)

    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        cleaned[column] = cleaned[column].replace("", pd.NA)

    before_blank_removal = len(cleaned)
    cleaned = cleaned.dropna(how="all")
    blank_rows_removed = before_blank_removal - len(cleaned)

    before_duplicate_removal = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    duplicate_rows_removed = before_duplicate_removal - len(cleaned)

    cleaned = cleaned.reset_index(drop=True)
    stats = {
        "input_rows": input_rows,
        "blank_rows_removed": blank_rows_removed,
        "duplicate_rows_removed": duplicate_rows_removed,
        "output_rows": len(cleaned),
    }
    return cleaned, stats


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def clean_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Clean a CSV or the first worksheet in an XLSX file.

    By default, writes a sibling file named ``<stem>_cleaned<suffix>``.
    Existing output files and the source file are never overwritten.
    """
    source = Path(input_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source}")

    extension = source.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Supported input formats are .csv and .xlsx")

    if output_path is None:
        destination = source.with_name(f"{source.stem}_cleaned{source.suffix}")
    else:
        destination = Path(output_path).expanduser()

    if destination.suffix.lower() != extension:
        raise ValueError("Output file must use the same extension as the input file")

    source_resolved = source.resolve(strict=False)
    destination_resolved = destination.resolve(strict=False)
    if str(source_resolved).casefold() == str(destination_resolved).casefold():
        raise ValueError("Output path must be different from the input file")
    if destination.exists():
        raise FileExistsError(f"Output file already exists: {destination}")

    if extension == ".csv":
        dataframe = pd.read_csv(source, encoding="utf-8-sig")
    else:
        dataframe = pd.read_excel(source, sheet_name=0, engine="openpyxl")

    cleaned, stats = clean_dataframe(dataframe)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if extension == ".csv":
        cleaned.to_csv(destination, index=False, encoding="utf-8-sig")
    else:
        cleaned.to_excel(destination, index=False, engine="openpyxl")

    return destination, stats


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Clean CSV or XLSX data: normalize headers, trim text, "
            "remove fully blank rows, and drop exact duplicate rows."
        )
    )
    parser.add_argument("input", help="Path to a .csv or .xlsx file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output path; defaults to <input>_cleaned.<ext>",
    )
    args = parser.parse_args(argv)

    try:
        output, stats = clean_file(args.input, args.output)
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Saved: {output}")
    print(f"Rows: {stats['input_rows']} -> {stats['output_rows']}")
    print(f"Blank rows removed: {stats['blank_rows_removed']}")
    print(f"Duplicate rows removed: {stats['duplicate_rows_removed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
