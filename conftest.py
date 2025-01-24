import pytest
import logging
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_logging():
    logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def sample_config():
    return Path(__file__).parent / 'sample_data' / 'config.ini'
