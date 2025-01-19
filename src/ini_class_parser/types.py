# common_types.py
from dataclasses import dataclass
from typing import Dict, Optional
import csv

class ConfigParserError(Exception):
    """Base exception for config parsing errors"""
    pass

class MalformedEntryError(ConfigParserError):
    """Raised when an entry cannot be parsed correctly"""
    pass

@dataclass
class ConfigEntry:
    class_name: str
    source: str
    category: str
    parent: str
    inherits_from: str
    is_simple_object: bool
    num_properties: int
    scope: int
    model: str
    
    @classmethod
    def from_csv(cls, csv_string: str) -> 'ConfigEntry':
        """Create ConfigEntry from CSV string."""
        reader = csv.reader([csv_string.strip('"')])
        try:
            row = next(reader)
            if len(row) != 9:
                raise MalformedEntryError(f"Expected 9 fields, got {len(row)}")
            return cls(
                class_name=row[0],
                source=row[1],
                category=row[2],
                parent=row[3],
                inherits_from=row[4],
                is_simple_object=row[5].lower() == 'true',
                num_properties=int(row[6]),
                scope=int(row[7]),
                model=row[8]
            )
        except (StopIteration, ValueError) as e:
            raise MalformedEntryError(f"Failed to parse entry: {e}")

@dataclass
class ClassInfo:
    name: str
    source_file: str
    properties: Dict[str, str]
    parent_class: Optional[str] = None
    inherits_from: Optional[str] = None
