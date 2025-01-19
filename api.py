from typing import Dict, List, Optional, Set
from pathlib import Path
from .src import INIClassParser, ClassInfo

class ClassHierarchyAPI:
    """
    High-level API for working with class hierarchies from configuration files.
    Provides a simplified interface for common operations.
    """

    def __init__(self, config_path: str | Path):
        self._parser = INIClassParser(str(config_path))
        self._cache: Dict[str, Dict[str, ClassInfo]] = {}

    def get_available_categories(self) -> List[str]:
        """Get list of all available categories in the config."""
        return self._parser.get_categories()

    def get_class(self, category: str, class_name: str) -> Optional[ClassInfo]:
        """Get information about a specific class."""
        return self._parser.get_class_info(category, class_name)

    def get_all_classes(self, category: str) -> Dict[str, ClassInfo]:
        """Get all classes in a category with their complete information."""
        if category not in self._cache:
            self._cache[category] = self._parser.get_all_classes(category)
        return self._cache[category]

    def get_children(self, category: str, class_name: str) -> List[str]:
        """Get immediate children of a class."""
        return self._parser.get_direct_children(category, class_name)

    def get_descendants(self, category: str, class_name: str) -> Set[str]:
        """Get all descendants (children, grandchildren, etc.) of a class."""
        return self._parser.get_all_descendants(category, class_name)

    def get_inheritance_path(self, category: str, class_name: str) -> List[str]:
        """Get the complete inheritance path from the class to the root."""
        classes = self.get_all_classes(category)
        if class_name not in classes:
            return []

        path = [class_name]
        current = classes[class_name]
        
        while current.inherits_from:
            path.append(current.inherits_from)
            current = classes[current.inherits_from]
            
        return path

    def find_common_ancestor(self, category: str, class1: str, class2: str) -> Optional[str]:
        """Find the closest common ancestor of two classes."""
        path1 = self.get_inheritance_path(category, class1)
        path2 = self.get_inheritance_path(category, class2)
        
        for ancestor in path1:
            if ancestor in path2:
                return ancestor
                
        return None

    def is_descendant_of(self, category: str, child: str, ancestor: str) -> bool:
        """Check if one class is a descendant of another."""
        path = self.get_inheritance_path(category, child)
        return ancestor in path[1:]  # Exclude the child itself from the check
