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

```python
from ini_class_parser import INIClassParser

# Initialize the parser
parser = INIClassParser('/path/to/config.ini')

# Get available categories
categories = parser.get_categories()

# Get structured data for a category
entries = parser.get_category_entries('CategoryData_CfgVehicles')
for entry in entries:
    print(f"Class: {entry.class_name}")
    print(f"Source: {entry.source}")
    print(f"Properties: {entry.num_properties}")
    print(f"Model: {entry.model}")

# Get category header fields
header = parser.get_category_header('CategoryData_CfgVehicles')
print(f"Fields: {header}")
```

## Data Format

The parser expects INI files with the following structure:
- Sections starting with `CategoryData_` containing CSV entries
- Each category has a header field defining column names
- Entries are numbered (0, 1, 2, etc.) containing CSV data
- Optional Validation section with metadata

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
