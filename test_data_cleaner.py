import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_cleaner import clean_dataframe, clean_file


class CleanDataFrameTests(unittest.TestCase):
    def test_trims_headers_and_values_removes_blank_and_duplicate_rows(self):
        source = pd.DataFrame(
            [
                [" Ana ", " ana@example.com "],
                ["Ana", "ana@example.com"],
                ["   ", " "],
                [None, None],
            ],
            columns=[" Name ", "E-mail Address"],
        )

        cleaned, stats = clean_dataframe(source)

        self.assertEqual(cleaned.columns.tolist(), ["name", "e_mail_address"])
        self.assertEqual(
            cleaned.fillna("").to_dict(orient="records"),
            [{"name": "Ana", "e_mail_address": "ana@example.com"}],
        )
        self.assertEqual(
            stats,
            {
                "input_rows": 4,
                "blank_rows_removed": 2,
                "duplicate_rows_removed": 1,
                "output_rows": 1,
            },
        )
        self.assertEqual(source.iloc[0, 0], " Ana ")

    def test_clean_file_writes_clean_csv_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sample.csv"
            pd.DataFrame(
                {
                    " Name ": [" Ana ", "Ana", " ", "Budi"],
                    "City": [" Jakarta ", "Jakarta", "", "Bandung"],
                }
            ).to_csv(source_path, index=False)
            original_bytes = source_path.read_bytes()

            output_path, stats = clean_file(source_path)

            self.assertEqual(output_path, Path(temp_dir) / "sample_cleaned.csv")
            self.assertEqual(source_path.read_bytes(), original_bytes)
            self.assertEqual(
                pd.read_csv(output_path).to_dict(orient="records"),
                [
                    {"name": "Ana", "city": "Jakarta"},
                    {"name": "Budi", "city": "Bandung"},
                ],
            )
            self.assertEqual(stats["input_rows"], 4)
            self.assertEqual(stats["blank_rows_removed"], 1)
            self.assertEqual(stats["duplicate_rows_removed"], 1)
            self.assertEqual(stats["output_rows"], 2)


if __name__ == "__main__":
    unittest.main()
