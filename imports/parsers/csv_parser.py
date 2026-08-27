"""
CSV file parser for bulk import
"""

import logging
from typing import Dict, List, Optional

import chardet
import pandas as pd

logger = logging.getLogger(__name__)

# Initialize variables


class CSVParser:
    """
    Parser for CSV files
    """

    def __init__(
        self, file, encoding: str = "utf-8", delimiter: str = ",", header_row: int = 0
    ):
        """
        Initialize CSV parser.

        Args:
            file: File object or file path
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)
            header_row: Row number to use as header (0-indexed)
        """
        self.file = file
        self.encoding = encoding
        self.delimiter = delimiter
        self.header_row = header_row
        self.df: Optional[pd.DataFrame] = None

    def _detect_encoding(self) -> str:
        """
        Detect file encoding using chardet.

        Returns:
            Detected encoding or default encoding
        """
        try:
            # Handle file-like objects vs file paths
            if hasattr(self.file, "read"):
                # File-like object
                current_pos = 0
                try:
                    current_pos = self.file.tell()
                except (AttributeError, IOError):
                    pass

                # Read raw bytes for detection
                try:
                    if hasattr(self.file, "seek"):
                        self.file.seek(0)
                    rawdata = self.file.read(100000)  # Read chunk for detection
                    # Reset position
                    if hasattr(self.file, "seek"):
                        self.file.seek(current_pos)
                except Exception as e:
                    logger.warning(f"Error reading file for encoding detection: {e}")
                    return self.encoding
            else:
                # File path
                with open(self.file, "rb") as f:
                    rawdata = f.read(100000)

            if not rawdata:
                logger.warning("No data read for encoding detection")
                return self.encoding

            result = chardet.detect(rawdata)
            detected_encoding = result.get("encoding")
            confidence = result.get("confidence", 0)

            if detected_encoding and confidence > 0.6:  # Lowered threshold
                logger.info(
                    f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})"
                )
                return detected_encoding
            else:
                logger.warning(
                    f"Low confidence encoding detection: {detected_encoding} (confidence: {confidence:.2f}), using default"
                )
                return self.encoding

        except Exception as e:
            logger.warning(
                f"Encoding detection failed: {str(e)}, using default encoding"
            )
            return self.encoding

    def parse(self) -> pd.DataFrame:
        """
        Parse CSV file and return DataFrame.

        Returns:
            pandas DataFrame

        Raises:
            ValueError: If file cannot be parsed
        """
        encodings_to_try = []
        detected_encoding = None
        try:
            # Reset file pointer to beginning
            if hasattr(self.file, "seek"):
                try:
                    self.file.seek(0)
                except (AttributeError, IOError) as e:
                    logger.warning(f"Could not seek file: {str(e)}")

            # Try UTF-8 first
            try:
                self.df = pd.read_csv(
                    self.file,
                    encoding=self.encoding,
                    delimiter=self.delimiter,
                    header=self.header_row,
                )
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ["utf-8","latin-1", "iso-8859-1", "cp1252"]:
                    try:
                        if hasattr(self.file, "seek"):
                            self.file.seek(0)  # Reset file pointer
                        self.df = pd.read_csv(
                            self.file,
                            encoding=encoding,
                            delimiter=self.delimiter,
                            header=self.header_row,
                        )
                        self.encoding = encoding
                        break
                    except (UnicodeDecodeError, Exception):
                        continue

            # Add detected encoding first
            if detected_encoding and detected_encoding != self.encoding:
                encodings_to_try.append(detected_encoding)

            # Add comprehensive fallback list
            fallback_encodings = [
                "utf-8-sig",
                "utf-8",
                "windows-1252",
                "cp1252",
                "latin1",
                "iso-8859-1",
                "ascii",
                "cp437",
                "windows-1251",
                "iso-8859-15",
            ]

            # Remove duplicates while preserving order
            for enc in fallback_encodings:
                if enc not in encodings_to_try:
                    encodings_to_try.append(enc)

            # Try each encoding
            for i, encoding in enumerate(encodings_to_try):
                try:
                    # Reset file pointer
                    if hasattr(self.file, "seek"):
                        self.file.seek(0)

                    self.df = pd.read_csv(
                        self.file,
                        encoding=encoding,
                        delimiter=self.delimiter,
                        header=self.header_row,
                        encoding_errors="replace",  # Replace problematic characters
                    )
                    self.encoding = encoding
                    # if i == 0 and encoding == detected_encoding:
                    if detected_encoding and i == 0 and encoding == detected_encoding:
                        logger.info(
                            f"Successfully parsed with detected encoding: {encoding}"
                        )
                    else:
                        logger.info(
                            f"Successfully parsed with fallback encoding: {encoding}"
                        )
                    break
                except Exception as e:
                    logger.debug(f"Encoding {encoding} failed: {str(e)}")
                    continue

            if self.df is None:
                # Last resort: try with errors='ignore'
                try:
                    if hasattr(self.file, "seek"):
                        self.file.seek(0)
                    self.df = pd.read_csv(
                        self.file,
                        encoding="utf-8",
                        delimiter=self.delimiter,
                        header=self.header_row,
                        encoding_errors="ignore",  # Ignore problematic characters
                    )
                    self.encoding = "utf-8"
                    logger.warning("Parsed with UTF-8 ignoring encoding errors")
                except Exception:
                    raise ValueError(
                        "Could not decode CSV file with any supported encoding"
                    )

            # Check if DataFrame is empty
            if self.df is None or self.df.empty:
                raise ValueError("No columns to parse from file")

            # Clean DataFrame
            from imports.utils import clean_dataframe

            self.df = clean_dataframe(self.df)

            # Check again after cleaning
            if self.df is None or self.df.empty:
                raise ValueError("No data rows found in file after cleaning")

            return self.df

        except Exception as e:
            logger.error(f"Error parsing CSV file: {str(e)}")
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

    def get_rows(self) -> List[Dict]:
        """
        Convert DataFrame to list of dictionaries.

        Returns:
            List of row dictionaries
        """
        if self.df is None:
            self.parse()

        # Convert to list of dicts, handling NaN values
        rows = []
        for idx, row in self.df.iterrows():
            row_dict = {}
            for col in self.df.columns:
                value = row[col]
                # Convert NaN to None
                if pd.isna(value):
                    row_dict[col] = None
                else:
                    row_dict[col] = value
            rows.append(row_dict)

        return rows

    def get_column_names(self) -> List[str]:
        """
        Get column names from CSV file.

        Returns:
            List of column names
        """
        if self.df is None:
            self.parse()

        return list(self.df.columns)

    def get_row_count(self) -> int:
        """
        Get number of data rows (excluding header).

        Returns:
            Number of rows
        """
        if self.df is None:
            self.parse()

        return len(self.df)

    def validate_columns(
        self, required_columns: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that required columns exist.

        Args:
            required_columns: List of required column names

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.df is None:
            self.parse()

        missing_columns = []
        for col in required_columns:
            if col not in self.df.columns:
                missing_columns.append(col)

        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"

        return True, None
