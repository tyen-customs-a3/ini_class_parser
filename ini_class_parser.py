from dataclasses import dataclass
from typing import Dict, List, Optional, Set

@dataclass
class ClassInfo:
    name: str
    source: str
    category: str
    parent: str
    inherits_from: str
    is_simple_object: bool
    num_properties: int
    scope: int
    model: str
    children: List[str] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

class INIClassParser:
    # ...existing code...

    def get_class_info(self, category: str, class_name: str) -> Optional[ClassInfo]:
        """Get detailed information about a specific class."""
        entries = self.get_category_entries(category)
        for entry in entries:
            if entry.class_name == class_name:
                return ClassInfo(
                    name=entry.class_name,
                    source=entry.source,
                    category=entry.category,
                    parent=entry.parent,
                    inherits_from=entry.inherits_from,
                    is_simple_object=entry.is_simple_object,
                    num_properties=entry.num_properties,
                    scope=entry.scope,
                    model=entry.model
                )
        return None

    def get_all_classes(self, category: str) -> Dict[str, ClassInfo]:
        """Get a dictionary of all classes in a category with their information."""
        entries = self.get_category_entries(category)
        classes = {}
        
        # First pass: Create ClassInfo objects
        for entry in entries:
            classes[entry.class_name] = ClassInfo(
                name=entry.class_name,
                source=entry.source,
                category=entry.category,
                parent=entry.parent,
                inherits_from=entry.inherits_from,
                is_simple_object=entry.is_simple_object,
                num_properties=entry.num_properties,
                scope=entry.scope,
                model=entry.model
            )
        
        # Second pass: Populate children lists
        for class_name, class_info in classes.items():
            if class_info.inherits_from and class_info.inherits_from in classes:
                classes[class_info.inherits_from].children.append(class_name)
        
        return classes

    def get_direct_children(self, category: str, class_name: str) -> List[str]:
        """Get a list of class names that directly inherit from the given class."""
        classes = self.get_all_classes(category)
        return classes[class_name].children if class_name in classes else []

    def get_all_descendants(self, category: str, class_name: str) -> Set[str]:
        """Get all descendants of a class (children, grandchildren, etc.)"""
        classes = self.get_all_classes(category)
        if class_name not in classes:
            return set()

        descendants = set()
        to_process = [class_name]
        
        while to_process:
            current = to_process.pop()
            children = classes[current].children
            descendants.update(children)
            to_process.extend(children)
            
        return descendants
