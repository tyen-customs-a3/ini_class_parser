from typing import Dict, List, Optional, Set, Tuple, Any
import configparser
import csv
from io import StringIO
import logging
from multiprocessing import Pool, cpu_count
from .types import ConfigEntry, ClassInfo, ConfigParserError, MalformedEntryError
from .cache import CacheManager
from collections import defaultdict

logger = logging.getLogger(__name__)

class INIClassParser:
    def __init__(self, file_path: str, use_parallel: bool = True, max_workers: int = None):
        self.file_path = file_path
        self.use_parallel = use_parallel
        self.max_workers = max_workers or max(1, cpu_count() - 1)
        self.parallel_threshold = 1000  # Increased threshold for better performance
        self.config = configparser.ConfigParser(strict=True)
        self._cache = CacheManager()
        try:
            # Try UTF-8 first, then fallback to other encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        self.config.read_file(f)
                        break
                except UnicodeDecodeError:
                    if encoding == 'cp1252':  # Last attempt failed
                        raise ConfigParserError(f"Could not decode file with any supported encoding: {file_path}")
                    continue
        except (configparser.Error, OSError) as e:
            raise ConfigParserError(f"Error parsing config: {e}")
        self._parse_file()

    def _parse_file(self) -> None:
        """Parse the INI file format with numbered entries."""
        category_entries = defaultdict(list)
        
        for section in self.config.sections():
            if not section.startswith('CategoryData_'):
                continue
                
            # Skip processing if only header exists
            if len(self.config[section]) <= 1 and 'header' in self.config[section]:
                continue
            
            # Process numbered entries
            for key in sorted(self.config[section].keys()):
                if key == 'header':
                    continue
                    
                try:
                    # Handle double-quoted values
                    value = self.config[section][key].strip('"')
                    if not value:
                        continue
                        
                    entry = ConfigEntry.from_csv(value)
                    category_entries[section].append(entry)
                except MalformedEntryError as e:
                    if "Skipping header row" in str(e):
                        continue  # Silently skip headers
                    logger.warning(f"Skipping malformed entry in {section} #{key}: {e}")

        # Bulk add entries for each category
        for category, entries in category_entries.items():
            if entries:  # Only process categories with actual entries
                self._cache.bulk_add_entries(category, entries)
                
                # Pre-compute paths and descendants for large categories
                if len(entries) > 100:
                    self._cache.precompute_all_paths(category)
                    self._cache.compute_descendants_bulk(category)

    @staticmethod
    def _parse_entry(entry_data: tuple) -> tuple[Optional[ConfigEntry], Optional[str]]:
        """Parse a single entry from the INI file."""
        key, value = entry_data
        try:
            value = value.strip()
            if not value or value == '""':
                return None, None
                
            try:
                entry = ConfigEntry.from_csv(value)
                # Ensure empty strings for optional fields
                entry.inherits_from = entry.inherits_from or ''
                entry.model = entry.model or ''
                return (entry, None)
            except MalformedEntryError as e:
                if "Skipping header row" in str(e):
                    return None, None  # Silently skip header rows
                return None, f"Skipping entry {key}: {e}"
                
        except Exception as e:
            return None, f"Unexpected error in entry {key}: {e}"

    def _process_entries_parallel(self, entries_to_process: list) -> list:
        chunk_size = max(250, len(entries_to_process) // (self.max_workers * 2))
        with Pool(processes=self.max_workers) as pool:
            return pool.map(self._parse_entry, entries_to_process, chunksize=chunk_size)

    def get_category_entries(self, category: str) -> List[ConfigEntry]:
        """Get entries for a category, handling the numbered format."""
        if category not in self.config:
            return []

        # Return cached entries if available
        cache = self._cache.get_or_create_cache(category)
        if cache.entries:
            return sorted(cache.entries.values(), key=lambda x: x.class_name)

        entries = []
        section = self.config[category]
        
        # Process numbered entries
        for key in sorted(section.keys()):
            if key == 'header':
                continue
                
            try:
                value = section[key].strip('"')
                if not value:
                    continue
                    
                entry = ConfigEntry.from_csv(value)
                entries.append(entry)
            except MalformedEntryError as e:
                if not "Skipping header row" in str(e):
                    logger.warning(f"Skipping entry {category}#{key}: {e}")

        # Cache results
        if entries:
            for entry in entries:
                self._cache.add_entry(category, entry)
                if entry.inherits_from:
                    self._cache.add_child(category, entry.inherits_from, entry.class_name)

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
        entry = self._cache.get_entry(category, class_name)
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
        return sorted(self._cache.get_children(category, class_name))

    def get_all_descendants(self, category: str, class_name: str) -> Set[str]:
        """Get all descendants (children, grandchildren, etc.) of a class."""
        return self._cache.compute_descendants(category, class_name)

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
