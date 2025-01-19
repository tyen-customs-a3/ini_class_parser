from ini_class_parser import (
    INIClassParser,
    ConfigEntry,
    ConfigParserError,
    MalformedEntryError,
    ClassHierarchyAPI
)
import pytest
import logging

@pytest.fixture(autouse=True)
def setup_logging():
    logging.basicConfig(level=logging.DEBUG)