from ini_class_parser.parser import (
    INIClassParser,
    ConfigEntry,
    ConfigParserError,
    MalformedEntryError
)

def test_imports():
    assert INIClassParser is not None
    assert ConfigEntry is not None
    assert ConfigParserError is not None
    assert MalformedEntryError is not None
