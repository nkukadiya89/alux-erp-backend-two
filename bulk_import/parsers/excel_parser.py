# bulk_import/parsers/excel_parser.py
from typing import Any, Dict, List

import pandas as pd


class ExcelParser:
    """Excel file parser"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> List[Dict[str, Any]]:
        """Parse Excel file and return list of dictionaries"""
        try:
            # Read Excel file
            df = pd.read_excel(
                self.file_path,
                dtype=str,  # Read all as strings to avoid type issues
                keep_default_na=False,  # Don't convert empty cells to NaN
            )

            # Convert to dictionary records
            records = df.to_dict(orient="records")

            # Clean up the records (remove NaN, strip whitespace)
            cleaned_records = []
            for record in records:
                cleaned_record = {}
                for key, value in record.items():
                    # Clean key (column name)
                    clean_key = str(key).strip()
                    # Clean value
                    if pd.isna(value) or value == "":
                        clean_value = None
                    else:
                        clean_value = str(value).strip()

                    cleaned_record[clean_key] = clean_value

                cleaned_records.append(cleaned_record)

            return cleaned_records

        except Exception as e:
            raise ExcelParseError(f"Failed to parse Excel file: {str(e)}")


class ExcelParseError(Exception):
    """Excel parsing error"""

    pass
