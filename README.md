# INI Class Parser

This module parses configuration extraction files and provides structured access to the data.

## Installation

### From Source
```bash
# Install build dependencies
pip install hatchling

# Install in development mode
pip install -e ".[dev]"
```

### As a Dependency
Add to your `pyproject.toml`:
```toml
[project]
dependencies = [
    "ini_class_parser @ git+https://github.com/your-repo/ini_class_parser.git@v0.1.0",
]
```

Or to your `requirements.txt`:
```text
ini_class_parser @ git+https://github.com/your-repo/ini_class_parser.git@v0.1.0
```

## Usage

### Basic Parser Usage
```python
from ini_class_parser import INIClassParser

# Initialize the parser
parser = INIClassParser('/path/to/config.ini')

# Get available categories
categories = parser.get_categories()
print(f"Categories: {categories}")
# Output: ['CategoryData_CfgVehicles', 'CategoryData_CfgWeapons', ...]

# Get structured data for a category
entries = parser.get_category_entries('CategoryData_CfgVehicles')
for entry in entries:
    print(f"Class: {entry.class_name}")
    print(f"Source: {entry.source}")
    print(f"Category: {entry.category}")
    print(f"Parent: {entry.parent}")
    print(f"Inherits From: {entry.inherits_from}")
    print(f"Is Simple Object: {entry.is_simple_object}")
    print(f"Number of Properties: {entry.num_properties}")
    print(f"Scope: {entry.scope}")
    print(f"Model: {entry.model}")
    print("---")

# Example output:
# Class: Car
# Source: @em
# Category: CategoryData_CfgVehicles
# Parent: LandVehicle
# Inherits From: LandVehicle
# Is Simple Object: False
# Number of Properties: 10
# Scope: 2
# Model: \A3\air_f_beta\Parachute_01\Parachute_01_F.p3d
# ---

# Get category header fields
header = parser.get_category_header('CategoryData_CfgVehicles')
print(f"Fields: {header}")
# Output: ['ClassName', 'Source', 'Category', 'Parent', 'InheritsFrom', 'IsSimpleObject', 'NumProperties', 'Scope', 'Model']
```

### Working with Class Hierarchies
```python
from ini_class_parser import ClassHierarchyAPI

api = ClassHierarchyAPI('/path/to/config.ini')

# Get inheritance path
path = api.get_inheritance_path('CategoryData_CfgVehicles', 'Car')
print(f"Inheritance path: {path}")
# Output: ['Car', 'LandVehicle', 'Vehicle', 'AllVehicles']

# Get children
children = api.get_children('CategoryData_CfgVehicles', 'LandVehicle')
print(f"Direct children: {children}")
# Output: ['Car', 'Tank', 'Truck']

# Find common ancestor
ancestor = api.find_common_ancestor('CategoryData_CfgVehicles', 'Car', 'Tank')
print(f"Common ancestor: {ancestor}")
# Output: 'LandVehicle'

# Check inheritance
is_descendant = api.is_descendant_of('CategoryData_CfgVehicles', 'Car', 'Vehicle')
print(f"Is Car a descendant of Vehicle? {is_descendant}")
# Output: True
```

### Working with Config Entries
```python
# Get all entries in a category
entries = api.get_all_classes('CategoryData_CfgVehicles')
for name, info in entries.items():
    print(f"Class: {name}")
    print(f"Source: {info.source_file}")
    print(f"Parent: {info.parent_class}")
    print(f"Properties: {info.properties}")
    print("---")

# Example output:
# Class: Car
# Source: @em
# Parent: LandVehicle
# Properties: {'maxSpeed': '100', 'armor': '50', 'crew': '4'}
# ---
```

## Data Format

The parser expects INI files with the following structure:

```ini
[CategoryData_CfgVehicles]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
0="Car,@em,CategoryData_CfgVehicles,LandVehicle,LandVehicle,false,10,2,\A3\air_f_beta\Parachute_01\Parachute_01_F.p3d"
1="Tank,@em,CategoryData_CfgVehicles,LandVehicle,LandVehicle,false,15,2,\A3\armor_f_beta\Tank_01\Tank_01_F.p3d"

[Validation]
version=1.0
timestamp=2024-01-01 12:00:00
```

## Development

### Installation
```bash
# Install with all dependencies (development and testing)
pip install -e ".[all]"

# Or install specific groups
pip install -e ".[test]"  # Just testing dependencies
pip install -e ".[dev]"   # Just development tools
```

### Running Tests
```bash
# Ensure test dependencies are installed
pip install -e ".[test]"

# Run tests with coverage
pytest --cov=ini_class_parser
```

### Code Style
```bash
black .
flake8
mypy src/ini_class_parser
```
