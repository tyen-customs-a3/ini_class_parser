from multiprocessing import cpu_count
import pytest
from ini_class_parser import INIClassParser, ConfigEntry, ConfigParserError, MalformedEntryError
import os
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
def config_path():
    # Get the path relative to this test file
    base_path = Path(__file__).parent.parent
    return str(base_path / 'sample_data' / 'config.ini')

@pytest.fixture
def parser(config_path):
    return INIClassParser(config_path)

def test_classnames_file_validation(config_path):
    """
    Verify that all classnames listed in config_classnames.txt exist in the parsed config.
    """
    # Get classnames file path relative to config file
    base_path = Path(config_path).parent
    classnames_path = base_path / 'config_classnames.txt'
    
    # Read expected classnames
    with open(classnames_path, 'r') as f:
        expected_classnames = {line.strip() for line in f if line.strip()}
    
    # Create parser instance
    parser = INIClassParser(config_path)
    
    # Get all parsed classnames across all categories
    parsed_classnames = set()
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        parsed_classnames.update(e.class_name for e in entries)
    
    # Verify each expected classname exists
    missing_classes = expected_classnames - parsed_classnames
    assert not missing_classes, f"Classes from classnames file not found in config: {missing_classes}"
    
    # Optional: Verify no unexpected classes (comment out if too restrictive)
    # unexpected_classes = parsed_classnames - expected_classnames
    # assert not unexpected_classes, f"Classes found in config but not in classnames file: {unexpected_classes}"

def test_validate_category_headers(parser):
    """Verify all categories have the correct header format."""
    expected_fields = ["ClassName", "Source", "Category", "Parent", "InheritsFrom", 
                      "IsSimpleObject", "NumProperties", "Scope", "Model"]
    for category in parser.get_categories():
        header = parser.get_category_header(category)
        if isinstance(header, str):
            header = [h.strip() for h in header.split(',')]
        assert header == expected_fields, f"Invalid header in category {category}"

def test_validate_entry_format(parser):
    """Verify all entries follow the expected format."""
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        for entry in entries:
            # Verify required fields are present
            assert hasattr(entry, 'class_name'), f"Missing class_name in {category}"
            assert hasattr(entry, 'source'), f"Missing source in {category}"
            assert hasattr(entry, 'category'), f"Missing category in {category}"
            
            # Basic validation - category can be with or without prefix
            full_category = category.replace("CategoryData_", "")
            assert entry.category in [category, full_category], \
                f"Category mismatch in {entry.class_name}: {entry.category} not in [{category}, {full_category}]"
            assert isinstance(entry.is_simple_object, bool), f"Invalid is_simple_object in {entry.class_name}"
            assert isinstance(entry.num_properties, int), f"Invalid num_properties in {entry.class_name}"
            assert isinstance(entry.scope, int), f"Invalid scope in {entry.class_name}"

def test_validate_inheritance_chain(parser):
    """Verify inheritance relationships are valid."""
    # Add known base classes that might not be in config
    known_base_classes = {
        "InventoryItem_Base_F",  # Base class for equipment items
        "Binocular",            # Base class for binoculars and optics
        "Default",              # Root class for weapons
        "All",                  # Root class for vehicles
        "Item_Base_F",         # Base class for items
        "ItemCore",            # Base class for core items
        "Man",                 # Base class for all human units
        "Logic",               # Base class for logic entities
        "Static",              # Base class for static objects
        "Thing",               # Base class for effects and small objects
        "Building",            # Base class for buildings
        "Land",                # Base class for land objects
        "Module_F",            # Base class for modules
        "House",               # Base class for houses
        "muzzle_snds_H",      # Base class for suppressor attachments
    }
    
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        for entry in entries:
            if entry.inherits_from:
                if entry.inherits_from in known_base_classes:
                    continue
                    
                # Find parent class across all categories
                parent_found = False
                for cat in parser.get_categories():
                    cat_entries = parser.get_category_entries(cat)
                    if any(e.class_name == entry.inherits_from for e in cat_entries):
                        parent_found = True
                        break
                assert parent_found, f"Parent class {entry.inherits_from} not found for {entry.class_name}"

def test_category_consistency(parser):
    """Verify category naming and structure consistency."""
    categories = parser.get_categories()
    
    # All categories should start with "CategoryData_"
    for category in categories:
        assert category.startswith("CategoryData_"), f"Invalid category name format: {category}"
    
    # Check for required categories
    required_categories = [
        "CategoryData_CfgMods",
        "CategoryData_CfgVehicles",
        "CategoryData_CfgWeapons"
    ]
    for required in required_categories:
        assert required in categories, f"Missing required category: {required}"

def test_model_paths(parser):
    """Verify model paths follow expected format."""
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        for entry in entries:
            if entry.model:
                # Model paths should start with \ or be relative path
                assert entry.model == "" or entry.model.startswith("\\") or "." in entry.model, \
                    f"Invalid model path format in {entry.class_name}: {entry.model}"

def test_source_validity(parser):
    """Verify source fields contain valid values."""
    valid_sources = {"A3", "curator", "expansion", "enoch", "@cup_terrain_core", 
                    "@cup_units", "@ace", "@pca_gear", "@em", "@cba_a3", "@em_rework",
                    "@bearskins", "@milgp", "@usp", "kart", "heli", "mark", "jets",
                    "argo", "orange", "tacops", "tank"}
    
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        for entry in entries:
            assert entry.source in valid_sources, f"Invalid source in {entry.class_name}: {entry.source}"
