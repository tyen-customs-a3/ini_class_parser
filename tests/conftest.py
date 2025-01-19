from ini_class_parser.parser import (
    INIClassParser,
    ConfigEntry,
    ConfigParserError,
    MalformedEntryError
)
import pytest
import logging

@pytest.fixture(autouse=True)
def setup_logging():
    logging.basicConfig(level=logging.DEBUG)