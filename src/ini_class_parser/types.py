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
        try:
            row = next(csv.reader([csv_string]))
            if len(row) != 9:
                raise MalformedEntryError(f"Expected 9 fields, got {len(row)}")
            
            # Handle empty/missing fields
            inherits_from = row[4] if row[4] != '' else None
            model = row[8].strip('"') if row[8] != '""' else ''
            
            return cls(
                class_name=row[0],
                source=row[1],
                category=row[2],
                parent=row[3],
                inherits_from=inherits_from or '',  # Convert None to empty string
                is_simple_object=row[5].lower() == 'true',
                num_properties=int(row[6]),
                scope=int(row[7]),
                model=model
            )
        except StopIteration:
            raise MalformedEntryError("Empty entry")
        except ValueError as e:
            # Check if this might be a header row
            if csv_string.startswith('"ClassName,') or 'NumProperties' in csv_string:
                raise MalformedEntryError("Skipping header row")
            raise MalformedEntryError(f"Failed to parse numeric value: {e}")
        except Exception as e:
            raise MalformedEntryError(f"Failed to parse entry: {e}")

@dataclass
class ClassInfo:
    name: str
    source_file: str
    properties: Dict[str, str]
    parent_class: Optional[str] = None
    inherits_from: Optional[str] = None
