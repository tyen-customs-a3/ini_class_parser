from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import configparser
import csv
from io import StringIO
import logging

logger = logging.getLogger(__name__)

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
    def from_csv(cls, line: str) -> Tuple['ConfigEntry', Optional[str]]:
        try:
            # Handle double-quoted values and strip them
            line = line.strip('"')
            reader = csv.reader(StringIO(line))
            values = next(reader)
            
            if len(values) != 9:
                raise MalformedEntryError(f"Expected 9 values, got {len(values)}")
            
            return cls(
                class_name=values[0].strip(),
                source=values[1].strip(),
                category=values[2].strip(),
                parent=values[3].strip(),
                inherits_from=values[4].strip(),
                is_simple_object=values[5].lower().strip() == 'true',
                num_properties=int(values[6].strip()),
                scope=int(values[7].strip()),
                model=values[8].strip()
            ), None
        except (IndexError, ValueError) as e:
            return None, str(e)

@dataclass
class ClassInfo:
    """Class to store information about a class definition"""
    name: str
    source_file: str
    properties: Dict[str, str]
    parent_class: Optional[str] = None

class INIClassParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.config = configparser.ConfigParser(strict=True)
        try:
            if not self.config.read(file_path):
                raise ConfigParserError(f"Could not read file: {file_path}")
        except configparser.Error as e:
            raise ConfigParserError(f"Error parsing config: {e}")

    def get_categories(self) -> List[str]:
        return [section for section in self.config.sections() if section.startswith("CategoryData_")]

    def get_category_header(self, category: str) -> Optional[List[str]]:
        if category not in self.config:
            return None
        try:
            header = self.config[category].get('header', '')
            # Handle empty headers explicitly
            if not header or header == '""':
                return None
            # Handle double-quoted headers
            header = header.strip('"')
            result = next(csv.reader(StringIO(header)))
            if len(result) != 9:  # Validate header structure
                logger.warning(f"Invalid header structure in {category}: {result}")
                return None
            # Strip any remaining quotes from individual fields
            result = [field.strip('"') for field in result]
            return result
        except (StopIteration, csv.Error) as e:
            logger.error(f"Error parsing header in {category}: {e}")
            return None

    def get_category_entries(self, category: str) -> List[ConfigEntry]:
        if category not in self.config:
            return []
        
        entries = []
        section = self.config[category]
        errors = []
        
        # Skip empty sections
        if len(section) <= 1 and 'header' in section:  # Only header present
            return []
        
        for key in section:
            if key == 'header':
                continue
            
            try:
                value = section[key].strip()
                # Skip empty entries
                if not value or value == '""':
                    continue
                    
                entry, error = ConfigEntry.from_csv(value)
                if entry:
                    # Normalize empty fields
                    entry.inherits_from = entry.inherits_from or ''
                    entry.model = entry.model or ''
                    entries.append(entry)
                if error:
                    errors.append(f"Entry {key}: {error}")
            except Exception as e:
                errors.append(f"Unexpected error in entry {key}: {e}")
        
        if errors:
            logger.warning(f"Errors in category {category}:\n" + "\n".join(errors))
        
        return sorted(entries, key=lambda x: x.class_name)

    def get_validation_info(self) -> Dict[str, str]:
        if "Validation" in self.config:
            return dict(self.config.items("Validation"))
        return {}

    def get_inheritance_tree(self, category: str) -> Dict[str, List[str]]:
        """Get the inheritance tree for a category"""
        entries = self.get_category_entries(category)
        tree = {}
        for entry in entries:
            if entry.inherits_from:
                if entry.inherits_from not in tree:
                    tree[entry.inherits_from] = []
                tree[entry.inherits_from].append(entry.class_name)
        return tree

# Example usage:
# parser = INIClassParser('/path/to/config.ini')
# categories = parser.get_categories()
# for category in categories:
#     header = parser.get_category_header(category)
#     entries = parser.get_category_entries(category)
#     print(f"Header for {category}: {header}")
#     for entry in entries:
#         print(f"Entry: {entry}")
# validation_info = parser.get_validation_info()
# print(f"Validation Info: {validation_info}")

__all__ = ['ConfigEntry', 'ClassInfo', 'INIClassParser', 'ConfigParserError', 'MalformedEntryError']
