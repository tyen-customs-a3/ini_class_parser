# INI Class Parser

A high-performance parser for extracting class hierarchy information from INI configuration files. Supports both sequential and parallel processing for large datasets.

## Features

- Fast parallel processing for large config files
- Case-sensitive and case-insensitive class lookups
- Memory-efficient caching of parsed data
- Rich inheritance analysis tools
- Support for both Path and string file paths
- Comprehensive error handling and validation

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage
```python
from ini_class_parser import ClassHierarchyAPI

# Initialize with automatic parallel processing
api = ClassHierarchyAPI('config.ini')

# Get available categories
categories = api.get_available_categories()

# Get information about a specific class
class_info = api.get_class('CategoryData_CfgVehicles', 'Car')
if class_info:
    print(f"Source: {class_info.source_file}")
    print(f"Parent: {class_info.parent_class}")
```

### Inheritance Analysis
```python
# Get complete inheritance path
path = api.get_inheritance_path('CategoryData_CfgVehicles', 'Car')
print(f"Inheritance: {' -> '.join(path)}")

# Find common ancestor
ancestor = api.find_common_ancestor('CategoryData_CfgVehicles', 'Car', 'Tank')
print(f"Common ancestor: {ancestor}")

# Check inheritance relationship
is_descendant = api.is_descendant_of('CategoryData_CfgVehicles', 'Car', 'Vehicle')
print(f"Is descendant: {is_descendant}")
```

### Case-Insensitive Lookups
```python
# Case-insensitive class lookup (default)
info = api.get_class('CategoryData_CfgVehicles', 'CAR')

# Case-sensitive lookup when needed
info = api.get_class('CategoryData_CfgVehicles', 'Car', case_sensitive=True)

# Find which category contains a class
category = api.find_class_category('Car', case_sensitive=False)
```

### Low-Level Parser Usage
```python
from ini_class_parser import INIClassParser

# Initialize parser with parallel processing control
parser = INIClassParser('config.ini', use_parallel=True, max_workers=4)

# Get raw entries
entries = parser.get_category_entries('CategoryData_CfgVehicles')
for entry in entries:
    print(f"{entry.class_name}: {entry.model}")

# Access header information
header = parser.get_category_header('CategoryData_CfgVehicles')
```

## Config File Format

The parser expects INI files with this structure:

```ini
[CategoryData_CfgVehicles]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
0="Car,@em,Vehicles,LandVehicle,LandVehicle,false,10,2,\model\car.p3d"
1="Tank,@em,Vehicles,LandVehicle,LandVehicle,false,15,2,\model\tank.p3d"
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=ini_class_parser

# Run specific test files
pytest tests/test_path_handling.py
pytest tests/test_ini_class_parser.py
```

### Performance Testing
The test suite includes performance tests that verify:
- Parallel processing efficiency
- Processing consistency between parallel and sequential modes
- Automatic parallel/sequential mode selection based on dataset size

## Error Handling

The library provides specific exceptions for common issues:
- `ConfigParserError`: Base exception for parsing errors
- `MalformedEntryError`: Raised when an entry cannot be parsed correctly

## License

This project is licensed under the MIT License.
