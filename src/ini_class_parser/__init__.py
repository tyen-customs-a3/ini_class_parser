"""INI Class Parser package."""
from .parser import INIClassParser, ConfigEntry, ConfigParserError, MalformedEntryError
from .api import ClassHierarchyAPI, ClassInfo

__version__ = "0.1.0"
__all__ = [
    'INIClassParser',
    'ConfigEntry',
    'ConfigParserError',
    'MalformedEntryError',
    'ClassHierarchyAPI',
    'ClassInfo'
]
