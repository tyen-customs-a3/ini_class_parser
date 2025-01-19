from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import configparser
import csv
from io import StringIO
import logging
from multiprocessing import Pool, cpu_count

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
    inherits_from: Optional[str] = None  # Add this field

class INIClassParser:
    def __init__(self, file_path: str, use_parallel: bool = True, max_workers: int = None):
        self.file_path = file_path
        self.use_parallel = use_parallel
        self.max_workers = max_workers or max(1, cpu_count() - 1)
        self.parallel_threshold = 1000  # Increased threshold for better performance
        self.config = configparser.ConfigParser(strict=True)
        try:
            if not self.config.read(file_path):
                raise ConfigParserError(f"Could not read file: {file_path}")
        except configparser.Error as e:
            raise ConfigParserError(f"Error parsing config: {e}")

    @staticmethod
    def _parse_entry(entry_data: tuple) -> tuple[Optional[ConfigEntry], Optional[str]]:
        key, value = entry_data
        try:
            value = value.strip()
            if not value or value == '""':
                return None, None
            return ConfigEntry.from_csv(value)
        except Exception as e:
            return None, f"Unexpected error in entry {key}: {e}"

    def _process_entries_parallel(self, entries_to_process: list) -> list:
        chunk_size = max(250, len(entries_to_process) // (self.max_workers * 2))
        with Pool(processes=self.max_workers) as pool:
            return pool.map(self._parse_entry, entries_to_process, chunksize=chunk_size)

    def get_category_entries(self, category: str) -> List[ConfigEntry]:
        if category not in self.config:
            return []
        
        section = self.config[category]
        errors = []
        
        # Skip empty sections
        if len(section) <= 1 and 'header' in section:
            return []
        
        # Filter out header and prepare entries for processing
        entries_to_process = [(k, v) for k, v in section.items() if k != 'header']
        
        if not self.use_parallel or len(entries_to_process) < self.parallel_threshold:
            results = [self._parse_entry(entry) for entry in entries_to_process]
        else:
            try:
                results = self._process_entries_parallel(entries_to_process)
            except Exception as e:
                logger.warning(f"Parallel processing failed, falling back to sequential: {e}")
                results = [self._parse_entry(entry) for entry in entries_to_process]
        
        entries = []
        for entry, error in results:
            if entry:
                entry.inherits_from = entry.inherits_from or ''
                entry.model = entry.model or ''
                entries.append(entry)
            if error:
                errors.append(error)
        
        if errors:
            logger.warning(f"Errors in category {category}:\n" + "\n".join(errors))
        
        return sorted(entries, key=lambda x: x.class_name)

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

    def get_class_info(self, category: str, class_name: str) -> Optional[ClassInfo]:
        """Get information about a specific class."""
        entries = self.get_category_entries(category)
        entry = next((e for e in entries if e.class_name == class_name), None)
        if not entry:
            return None
        return ClassInfo(
            name=entry.class_name,
            source_file=entry.source,
            properties={'model': entry.model},
            parent_class=entry.inherits_from,
            inherits_from=entry.inherits_from  # Set both parent_class and inherits_from
        )

    def get_all_classes(self, category: str) -> Dict[str, ClassInfo]:
        """Get all classes in a category with their complete information."""
        entries = self.get_category_entries(category)
        return {
            entry.class_name: ClassInfo(
                name=entry.class_name,
                source_file=entry.source,
                properties={'model': entry.model},
                parent_class=entry.inherits_from,
                inherits_from=entry.inherits_from  # Set both parent_class and inherits_from
            )
            for entry in entries
        }

    def get_direct_children(self, category: str, class_name: str) -> List[str]:
        """Get immediate children of a class."""
        entries = self.get_category_entries(category)
        return [
            entry.class_name
            for entry in entries
            if entry.inherits_from == class_name
        ]

    def get_all_descendants(self, category: str, class_name: str) -> Set[str]:
        """Get all descendants (children, grandchildren, etc.) of a class."""
        result = set()
        entries = self.get_category_entries(category)
        
        def add_descendants(parent: str) -> None:
            children = [e.class_name for e in entries if e.inherits_from == parent]
            for child in children:
                if child not in result:
                    result.add(child)
                    add_descendants(child)
        
        add_descendants(class_name)
        return result

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
