"""
Excel file parser for bulk import
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Parser for Excel files (.xlsx, .xls)
    """

    def __init__(self, file, sheet_name: Optional[str] = None, header_row: int = 0):
        """
        Initialize Excel parser.

        Args:
            file: File object or file path
            sheet_name: Name of sheet to read (None for first sheet)
            header_row: Row number to use as header (0-indexed)
        """
        self.file = file
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.df: Optional[pd.DataFrame] = None

    def parse(self) -> pd.DataFrame:
        """
        Parse Excel file and return DataFrame.

        Returns:
            pandas DataFrame

        Raises:
            ValueError: If file cannot be parsed
        """
        try:
            # Reset file pointer to beginning
            if hasattr(self.file, "seek"):
                try:
                    self.file.seek(0)
                except (AttributeError, IOError) as e:
                    logger.warning(f"Could not seek file: {str(e)}")

            if self.sheet_name:
                self.df = pd.read_excel(
                    self.file, sheet_name=self.sheet_name, header=self.header_row
                )
            else:
                self.df = pd.read_excel(self.file, header=self.header_row)

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
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")

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
        Get column names from Excel file.

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
