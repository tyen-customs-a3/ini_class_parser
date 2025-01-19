from typing import Dict, List, Optional, Set
from pathlib import Path
from .parser import INIClassParser, ClassInfo

class ClassHierarchyAPI:
    def __init__(self, config_path: str | Path):
        self._parser = INIClassParser(str(config_path))
        # Pre-cache all entries
        self._class_cache: Dict[str, Dict[str, ClassInfo]] = {}
        for category in self._parser.get_categories():
            classes = self._parser.get_all_classes(category)
            if classes:
                self._class_cache[category] = classes

    def get_all_classes(self, category: str) -> Dict[str, ClassInfo]:
        """Get all classes with caching"""
        if category not in self._class_cache:
            self._class_cache[category] = self._parser.get_all_classes(category)
        # Return the cached dictionary - same object for cache test
        return self._class_cache[category]

    def get_class(self, category: str, class_name: str, case_sensitive: bool = False) -> Optional[ClassInfo]:
        """Get class info with case-insensitive support"""
        classes = self.get_all_classes(category)
        if not case_sensitive:
            lower_name = class_name.lower()
            for name, info in classes.items():
                if name.lower() == lower_name:
                    return info
            return None
        return classes.get(class_name)

    def get_children(self, category: str, class_name: str) -> List[str]:
        """Get immediate children of a class"""
        return self._parser.get_direct_children(category, class_name)

    def get_descendants(self, category: str, class_name: str) -> Set[str]:
        """Get all descendants of a class"""
        return self._parser.get_all_descendants(category, class_name)

    def get_inheritance_path(self, category: str, class_name: str) -> List[str]:
        """Get inheritance path, empty list for non-existent classes"""
        return self._parser._cache.get_inheritance_path(category, class_name)

    def find_common_ancestor(self, category: str, class1: str, class2: str) -> Optional[str]:
        """Find closest common ancestor of two classes"""
        path1 = self.get_inheritance_path(category, class1)
        path2 = self.get_inheritance_path(category, class2)
        if not path1 or not path2:
            return None
        for ancestor in path1:
            if ancestor in path2:
                return ancestor
        return None

    def is_descendant_of(self, category: str, child: str, ancestor: str) -> bool:
        """Check descendant relationship"""
        path = self.get_inheritance_path(category, child)
        return ancestor in path[1:] if path else False

    def has_class(self, category: str, class_name: str, case_sensitive: bool = False) -> bool:
        """Check if class exists"""
        return self.get_class(category, class_name, case_sensitive=case_sensitive) is not None

    def find_class_category(self, class_name: str, case_sensitive: bool = False) -> Optional[str]:
        """Find category containing class"""
        for category in self.get_available_categories():
            if self.get_class(category, class_name, case_sensitive=case_sensitive) is not None:
                return category
        return None

    def get_available_categories(self) -> List[str]:
        """Get list of all available categories"""
        return self._parser.get_categories()