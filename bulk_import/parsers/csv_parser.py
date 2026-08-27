# bulk_import/parsers/csv_parser.py
import csv
from typing import Any, Dict, List


class CSVParser:
    """CSV file parser"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self, encoding="utf-8") -> List[Dict[str, Any]]:
        """Parse CSV file and return list of dictionaries"""
        encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252", "iso-8859-1"]

        for enc in encodings:
            try:
                records = []

                with open(self.file_path, "r", encoding=enc, newline="") as file:
                    # Auto-detect delimiter
                    sample = file.read(1024)
                    file.seek(0)

                    try:
                        sniffer = csv.Sniffer()
                        delimiter = sniffer.sniff(sample).delimiter
                    except:
                        delimiter = ","  # Default to comma

                    reader = csv.DictReader(file, delimiter=delimiter)

                    for row in reader:
                        # Clean up the row data
                        cleaned_row = {}
                        for key, value in row.items():
                            # Clean key (column name) - remove BOM
                            clean_key = (
                                str(key).strip().lstrip("\ufeff\ufffe") if key else ""
                            )
                            # Clean value
                            if value is None:
                                clean_value = None
                            else:
                                clean_value = str(value).strip()
                                if clean_value == "":
                                    clean_value = None

                            cleaned_row[clean_key] = clean_value

                        records.append(cleaned_row)

                return records

            except UnicodeDecodeError:
                continue  # Try next encoding
            except Exception as e:
                raise CSVParseError(f"Failed to parse CSV file: {str(e)}")

        raise CSVParseError("Unable to read CSV file with any supported encoding")


class CSVParseError(Exception):
    """CSV parsing error"""

    pass
