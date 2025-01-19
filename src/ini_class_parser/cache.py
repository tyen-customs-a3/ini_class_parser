from typing import Dict, List, Optional, Set, Mapping, Tuple, Iterable
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType
from .types import ConfigEntry, ClassInfo

@dataclass(frozen=True)
class CategoryCache:
    """Immutable cache container for category-specific data."""
    entries: Mapping[str, ConfigEntry] = field(default_factory=dict)
    entries_lower: Mapping[str, str] = field(default_factory=dict)
    children: Mapping[str, frozenset[str]] = field(default_factory=dict)  # Changed from defaultdict
    descendants: Mapping[str, frozenset[str]] = field(default_factory=dict)
    inheritance_paths: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    header: Optional[tuple[str, ...]] = None

    def __post_init__(self) -> None:
        """Convert mutable collections to immutable ones after initialization.""" 
        object.__setattr__(self, 'entries', MappingProxyType(dict(self.entries)))
        object.__setattr__(self, 'entries_lower', MappingProxyType(dict(self.entries_lower)))
        object.__setattr__(self, 'children', MappingProxyType(dict(self.children)))  # Simplified
        object.__setattr__(self, 'descendants', MappingProxyType(dict(self.descendants)))
        object.__setattr__(self, 'inheritance_paths', MappingProxyType(dict(self.inheritance_paths)))

    @classmethod
    def create_bulk(cls, 
                   entries: Dict[str, ConfigEntry],
                   children: Dict[str, Set[str]] = None,
                   descendants: Dict[str, Set[str]] = None) -> 'CategoryCache':
        """Create a new cache instance with bulk data."""
        return cls(
            entries=entries,
            entries_lower={k.lower(): k for k in entries.keys()},
            children={k: frozenset(v) for k, v in (children or {}).items()},
            descendants={k: frozenset(v) for k, v in (descendants or {}).items()},
            inheritance_paths={},  # Will be computed on demand
        )

class CacheManager:
    """Manages caching of parsed configuration data with thread-safe access."""
    
    def __init__(self) -> None:
        self._categories: Dict[str, CategoryCache] = {}
        self._class_to_category: Dict[str, str] = {}
        self._class_to_category_lower: Dict[str, str] = {}
        self._logger = logging.getLogger(__name__)
        
    def _detect_inheritance_cycle(self, category: str, start_class: str, visited: Set[str]) -> Optional[List[str]]: 
        """Detect cycles in inheritance chain. Returns the cycle if found."""
        current = start_class
        path = []
        while current:
            if current in visited:
                idx = path.index(current) if current in path else -1
                if idx != -1:
                    return path[idx:]
                return None
            path.append(current)
            visited.add(current)
            
            entry = self.get_entry(category, current)
            if not entry or not entry.inherits_from:
                break
            current = entry.inherits_from
        return None

    def get_or_create_cache(self, category: str) -> CategoryCache:
        """Get existing cache or create new one for category."""
        if category not in self._categories:
            self._categories[category] = CategoryCache()
        return self._categories[category]

    def add_entry(self, category: str, entry: ConfigEntry) -> None:
        """Add a new entry to the cache with case-insensitive mapping."""
        temp_entries = dict(self._categories.get(category, CategoryCache()).entries)
        temp_entries[entry.class_name] = entry
        
        temp_entries_lower = dict(self._categories.get(category, CategoryCache()).entries_lower)
        temp_entries_lower[entry.class_name.lower()] = entry.class_name
        
        self._categories[category] = CategoryCache(
            entries=temp_entries,
            entries_lower=temp_entries_lower,
            children=self._categories.get(category, CategoryCache()).children,
            descendants=self._categories.get(category, CategoryCache()).descendants,
            inheritance_paths=self._categories.get(category, CategoryCache()).inheritance_paths,
        )
        
        self._class_to_category[entry.class_name] = category
        self._class_to_category_lower[entry.class_name.lower()] = category

    def bulk_add_entries(self, category: str, entries: Iterable[ConfigEntry]) -> None:
        """Efficiently add multiple entries to cache."""
        # Convert to dictionary for faster lookups
        entries_dict = {entry.class_name: entry for entry in entries}
        
        # Prepare children relationships
        children_map: Dict[str, Set[str]] = defaultdict(set)
        for entry in entries_dict.values():
            if entry.inherits_from:
                children_map[entry.inherits_from].add(entry.class_name)
        
        # Create new cache instance without computing paths
        new_cache = CategoryCache.create_bulk(
            entries=entries_dict,
            children=children_map
        )
        
        # Update category cache
        self._categories[category] = new_cache
        
        # Update global mappings
        for class_name in entries_dict:
            self._class_to_category[class_name] = category
            self._class_to_category_lower[class_name.lower()] = category

    def update_cache(self, category: str, updates: Dict[str, Dict]) -> None:
        """Efficiently update multiple cache aspects at once."""
        current = self._categories.get(category, CategoryCache())
        
        new_data = {
            'entries': dict(current.entries),
            'entries_lower': dict(current.entries_lower),
            'children': dict(current.children),
            'descendants': dict(current.descendants),
            'inheritance_paths': dict(current.inheritance_paths),
        }
        
        # Apply updates
        for aspect, values in updates.items():
            if aspect in new_data:
                new_data[aspect].update(values)
        
        # Create new cache instance
        self._categories[category] = CategoryCache(
            entries=new_data['entries'],
            entries_lower=new_data['entries_lower'],
            children={k: frozenset(v) for k, v in new_data['children'].items()},
            descendants={k: frozenset(v) for k, v in new_data['descendants'].items()},
            inheritance_paths={k: tuple(v) if isinstance(v, list) else v 
                             for k, v in new_data['inheritance_paths'].items()},
            header=current.header
        )

    def set_header(self, category: str, header: List[str]) -> None:
        cache = self.get_or_create_cache(category)
        cache.header = header

    def add_child(self, category: str, parent: str, child: str) -> None:
        """Add child-parent relationship to cache."""
        current_cache = self._categories.get(category, CategoryCache())
        current_children = dict(current_cache.children)
        
        # Get or create the set of children for this parent
        children_set = set(current_children.get(parent, frozenset()))
        children_set.add(child)
        
        # Update the children mapping
        current_children[parent] = frozenset(children_set)
        
        # Create new cache instance with updated children
        self._categories[category] = CategoryCache(
            entries=current_cache.entries,
            entries_lower=current_cache.entries_lower,
            children=current_children,
            descendants=current_cache.descendants,
            inheritance_paths=current_cache.inheritance_paths,
        )

    def compute_descendants(self, category: str, class_name: str) -> Set[str]:
        """Compute descendants with optimized caching."""
        cache = self.get_or_create_cache(category)
        
        # Check cache first
        if class_name in cache.descendants:
            return set(cache.descendants[class_name])
        
        # Get all potential descendants first
        all_classes = set(cache.entries.keys())
        result = set()
        
        # Build inheritance paths only once
        paths_cache = {}
        for cls in all_classes:
            if cls != class_name:
                path = self.get_inheritance_path(category, cls)
                if class_name in path:
                    result.add(cls)
                paths_cache[cls] = path
        
        # Update cache atomically
        self._categories[category] = CategoryCache(
            entries=cache.entries,
            entries_lower=cache.entries_lower,
            children=cache.children,
            descendants={**cache.descendants, class_name: frozenset(result)},
            inheritance_paths=cache.inheritance_paths,
        )
        
        return result

    def compute_descendants_bulk(self, category: str) -> None:
        """Compute all descendants at once for a category."""
        cache = self.get_or_create_cache(category)
        all_classes = set(cache.entries.keys())
        
        # Compute all paths first
        paths: Dict[str, List[str]] = {}
        descendants: Dict[str, Set[str]] = defaultdict(set)
        
        for class_name in all_classes:
            path = self.get_inheritance_path(category, class_name)
            paths[class_name] = path
            # Add this class as descendant to all its ancestors
            for ancestor in path[1:]:
                descendants[ancestor].add(class_name)
        
        # Bulk update the cache with new descendants
        self.update_cache(category, {
            'descendants': {k: frozenset(v) for k, v in descendants.items()}
        })

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
        """Get children for a class, returning empty set if none exist."""
        if category not in self._categories:
            return set()
        return set(self._categories[category].children.get(class_name, frozenset()))

    def get_inheritance_path(self, category: str, class_name: str) -> List[str]:
        """Get inheritance path for a class with cycle detection."""
        cache = self.get_or_create_cache(category)
        
        # Check if class exists first
        if class_name not in cache.entries:
            return []
            
        if class_name not in cache.inheritance_paths:
            path: List[str] = []
            visited: Set[str] = set()
            current = class_name
            
            # Check for cycles first
            cycle = self._detect_inheritance_cycle(category, class_name, set())
            if cycle:
                # self._logger.warning(f"Inheritance cycle detected in {category}: {' -> '.join(cycle)}")
                # Store the path up to the cycle
                path = cycle
            else:
                # Normal path calculation
                while current:
                    if current in visited or current not in cache.entries:
                        break
                    path.append(current)
                    visited.add(current)
                    
                    entry = self.get_entry(category, current)
                    if not entry or not entry.inherits_from:
                        break
                    current = entry.inherits_from
            
            # Store as immutable tuple
            self._categories[category] = CategoryCache(
                entries=cache.entries,
                entries_lower=cache.entries_lower,
                children=cache.children,
                descendants=cache.descendants,
                inheritance_paths={**cache.inheritance_paths, class_name: tuple(path)},
            )
            
            return path
            
        return list(cache.inheritance_paths[class_name])

    def get_inheritance_paths_bulk(self, category: str, class_names: List[str]) -> Dict[str, List[str]]:
        """Get inheritance paths for multiple classes efficiently."""
        cache = self.get_or_create_cache(category)
        result = {}
        to_compute = []
        
        # Check cache first
        for name in class_names:
            if name in cache.inheritance_paths:
                result[name] = list(cache.inheritance_paths[name])
            else:
                to_compute.append(name)
        
        if not to_compute:
            return result
            
        # Compute paths for remaining classes
        new_paths = {}
        for name in to_compute:
            if name not in cache.entries:
                result[name] = []
                continue
                
            path = []
            visited = set()
            current = name
            
            while current:
                if current in visited or current not in cache.entries:
                    break
                path.append(current)
                visited.add(current)
                
                entry = self.get_entry(category, current)
                if not entry or not entry.inherits_from:
                    break
                current = entry.inherits_from
            
            result[name] = path
            new_paths[name] = tuple(path)
        
        # Bulk update cache
        if new_paths:
            self.update_cache(category, {
                'inheritance_paths': new_paths
            })
        
        return result

    def get_children_bulk(self, category: str, class_names: List[str]) -> Dict[str, Set[str]]:
        """Get children for multiple classes efficiently."""
        if category not in self._categories:
            return {name: set() for name in class_names}
            
        cache = self._categories[category]
        return {
            name: set(cache.children.get(name, frozenset()))
            for name in class_names
        }

    def precompute_all_paths(self, category: str) -> None:
        """Precompute all inheritance paths for a category at once."""
        cache = self.get_or_create_cache(category)
        if not cache.entries:
            return

        new_paths = {}
        visited_global = set()

        # Sort classes by inheritance depth to process parents first
        classes = list(cache.entries.keys())
        classes.sort(key=lambda x: len(self._get_raw_path(category, x)))

        for class_name in classes:
            if class_name in cache.inheritance_paths:
                continue
                
            path = []
            visited = set()
            current = class_name
            
            while current:
                if current in visited or current not in cache.entries:
                    break
                path.append(current)
                visited.add(current)
                visited_global.add(current)
                
                entry = cache.entries.get(current)
                if not entry or not entry.inherits_from:
                    break
                current = entry.inherits_from

            new_paths[class_name] = tuple(path)
            
        # Bulk update the cache with all paths
        if new_paths:
            self.update_cache(category, {
                'inheritance_paths': new_paths
            })

    def _get_raw_path(self, category: str, class_name: str) -> List[str]:
        """Get inheritance path without caching - used for sorting only."""
        cache = self._categories.get(category)
        if not cache or class_name not in cache.entries:
            return []
            
        path = []
        visited = set()
        current = class_name
        
        while current:
            if current in visited or current not in cache.entries:
                break
            path.append(current)
            visited.add(current)
            
            entry = cache.entries.get(current)
            if not entry or not entry.inherits_from:
                break
            current = entry.inherits_from
            
        return path
