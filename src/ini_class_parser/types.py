# common_types.py
from dataclasses import dataclass
from typing import Dict, Optional
import csv
import re

def clean_path(path: str) -> str:
    """Clean invalid characters from paths while preserving structure."""
    try:
        if not path:
            return ''
        
        # Try to decode bytes if needed
        if isinstance(path, bytes):
            try:
                path = path.decode('utf-8', errors='replace')
            except:
                path = path.decode('cp1252', errors='replace')
        
        # Determine original path separator style
        use_forward_slash = '/' in path
        use_backslash = '\\' in path
        target_sep = '/' if (use_forward_slash and not use_backslash) else '\\'
                
        # Remove common invalid sequences
        path = path.replace('?', '_')
        path = path.replace('*', '_')
        
        # Replace non-ASCII chars with closest ASCII equivalent or underscore
        cleaned = ''
        for char in path:
            if ord(char) < 128:
                cleaned += char
            elif char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя':
                # Map Cyrillic to Latin equivalents
                trans = str.maketrans('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                                    'abvgdeejzijklmnoprstufhzcssyyyeua')
                cleaned += char.translate(trans)
            else:
                cleaned += '_'
        
        # Normalize path separators to target style
        cleaned = cleaned.replace('\\', '/').strip()  # First normalize to forward slashes
        cleaned = cleaned.replace('//', '/')  # Remove double separators
        
        # Convert to target separator style
        if target_sep == '\\':
            cleaned = cleaned.replace('/', '\\')
            
        return cleaned
        
    except Exception as e:
        logging.warning(f"Error cleaning path: {e}")
        return path.replace('?', '_') if path else ''

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
            
            # Clean all path-like fields with enhanced cleaning
            class_name = clean_path(row[0])
            source = clean_path(row[1])
            category = clean_path(row[2])
            parent = clean_path(row[3])
            inherits_from = clean_path(row[4]) if row[4] != '' else None
            model = clean_path(row[8].strip('"')) if row[8] != '""' else ''
            
            # Handle non-path fields separately
            try:
                is_simple = row[5].lower() == 'true'
                num_props = int(row[6])
                scope = int(row[7])
            except ValueError as e:
                raise MalformedEntryError(f"Failed to parse numeric/boolean value: {e}")
            
            return cls(
                class_name=class_name,
                source=source,
                category=category,
                parent=parent,
                inherits_from=inherits_from or '',
                is_simple_object=is_simple,
                num_properties=num_props,
                scope=scope,
                model=model
            )
            
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Try to salvage what we can from the string
            try:
                cleaned = csv_string.encode('ascii', 'replace').decode('ascii')
                return cls.from_csv(cleaned)
            except:
                raise MalformedEntryError("Failed to handle character encoding")
        except StopIteration:
            raise MalformedEntryError("Empty entry")
        except Exception as e:
            if csv_string.startswith('"ClassName,') or 'NumProperties' in csv_string:
                raise MalformedEntryError("Skipping header row")
            raise MalformedEntryError(f"Failed to parse entry: {e}")

@dataclass
class ClassInfo:
    name: str
    source_file: str
    properties: Dict[str, str]
    parent_class: Optional[str] = None
    inherits_from: Optional[str] = None
