from typing import Dict, List, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field
from .types import ConfigEntry, ClassInfo

@dataclass
class CategoryCache:
    entries: Dict[str, ConfigEntry] = field(default_factory=dict)
    entries_lower: Dict[str, str] = field(default_factory=dict)
    children: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    descendants: Dict[str, Set[str]] = field(default_factory=dict)
    inheritance_paths: Dict[str, List[str]] = field(default_factory=dict)
    header: Optional[List[str]] = None

class CacheManager:
    def __init__(self):
        self._categories: Dict[str, CategoryCache] = {}
        self._class_to_category: Dict[str, str] = {}
        self._class_to_category_lower: Dict[str, str] = {}

    def get_or_create_cache(self, category: str) -> CategoryCache:
        if category not in self._categories:
            self._categories[category] = CategoryCache()
        return self._categories[category]

    def add_entry(self, category: str, entry: ConfigEntry) -> None:
        cache = self.get_or_create_cache(category)
        cache.entries[entry.class_name] = entry
        cache.entries_lower[entry.class_name.lower()] = entry.class_name
        self._class_to_category[entry.class_name] = category
        self._class_to_category_lower[entry.class_name.lower()] = category

    def set_header(self, category: str, header: List[str]) -> None:
        cache = self.get_or_create_cache(category)
        cache.header = header

    def add_child(self, category: str, parent: str, child: str) -> None:
        cache = self.get_or_create_cache(category)
        cache.children[parent].add(child)

    def compute_descendants(self, category: str, class_name: str) -> Set[str]:
        cache = self.get_or_create_cache(category)
        if class_name not in cache.descendants:
            result = set()
            to_process = {child for children in cache.children.values() for child in children}  # Get all children
            
            # Build complete inheritance paths for efficient lookup
            inheritance_paths = {
                cls: set(self.get_inheritance_path(category, cls))
                for cls in to_process
            }
            
            # Find all classes that have class_name in their inheritance path
            result = {
                cls for cls, path in inheritance_paths.items()
                if class_name in path and cls != class_name
            }
            
            cache.descendants[class_name] = result
        return cache.descendants[class_name].copy()  # Return copy to prevent modification

    def get_entry(self, category: str, class_name: str, case_sensitive: bool = True) -> Optional[ConfigEntry]:
        if category not in self._categories:
            return None
        cache = self._categories[category]
        
        if not case_sensitive:
            original_name = cache.entries_lower.get(class_name.lower())
            return cache.entries.get(original_name) if original_name else None
        return cache.entries.get(class_name)

    def get_category_for_class(self, class_name: str, case_sensitive: bool = True) -> Optional[str]:
        if case_sensitive:
            return self._class_to_category.get(class_name)
        return self._class_to_category_lower.get(class_name.lower())

    def get_children(self, category: str, class_name: str) -> Set[str]:
        if category not in self._categories:
            return set()
        return self._categories[category].children.get(class_name, set())

    def get_inheritance_path(self, category: str, class_name: str) -> List[str]:
        cache = self.get_or_create_cache(category)
        if class_name not in cache.inheritance_paths:
            path = []
            current = class_name
            entry = cache.entries.get(current)
            
            # Return empty list if class doesn't exist
            if not entry:
                return []
                
            visited = {current}
            while current:
                path.append(current)
                entry = cache.entries.get(current)
                if not entry or not entry.inherits_from:
                    break
                current = entry.inherits_from
                if current in visited:  # Prevent circular inheritance
                    break
                visited.add(current)
            cache.inheritance_paths[class_name] = path
        return cache.inheritance_paths[class_name].copy()  # Return copy to prevent modification
