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

@pytest.fixture
def large_config(tmp_path):
    """Create a large config file for performance testing"""
    config = tmp_path / "large_config.ini"
    with open(config, 'w') as f:
        f.write('[CategoryData_Large]\n')
        f.write('header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"\n')
        # Generate 100000 entries (increased from 10000)
        for i in range(100000):
            f.write(f'{i}="Class{i},Source,Cat,Parent,Inherits,false,10,1,model"\n')
    return str(config)

def test_get_categories(parser):
    categories = parser.get_categories()
    expected_categories = {
        'CategoryData_CfgVehicles',
        'CategoryData_CfgWeapons',
        'CategoryData_ForcedMissionDifficultyArgo',
        'CategoryData_MonetizedServers',
        'CategoryData_OfficialServersArma',
        'CategoryData_OfficialServersArgo',
        'CategoryData_SteamManagerConfig',
        'CategoryData_ScrollBar',
        'CategoryData_CfgMods'
    }
    assert set(categories) == expected_categories

def test_category_headers(parser):
    header = parser.get_category_header('CategoryData_CfgVehicles')
    expected_headers = ['ClassName', 'Source', 'Category', 'Parent', 'InheritsFrom', 
                       'IsSimpleObject', 'NumProperties', 'Scope', 'Model']
    assert header == expected_headers

def test_vehicle_hierarchy(parser):
    # Simplified to focus on parsing
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    car = next(e for e in entries if e.class_name == 'Car')
    assert car.source == '@em'
    assert car.inherits_from == 'LandVehicle'
    assert isinstance(car.inherits_from, str)

def test_weapon_entries(parser):
    entries = parser.get_category_entries('CategoryData_CfgWeapons')
    weapons = {e.class_name: e for e in entries}
    
    # Test specific weapon properties
    default = weapons['Default']
    assert default.num_properties == 133
    assert default.inherits_from == ''
    
    # Test inheritance
    assert weapons['PistolCore'].inherits_from == 'Default'
    assert weapons['RifleCore'].inherits_from == 'Default'

def test_scope_values(parser):
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    scopes = {
        'HeliH': 2,        # Public
        'Building': 1,     # Protected
        'AllVehicles': 0   # Private
    }
    
    for class_name, expected_scope in scopes.items():
        entry = next(e for e in entries if e.class_name == class_name)
        assert entry.scope == expected_scope, f"Wrong scope for {class_name}"

def test_model_paths(parser):
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    expected_models = {
        'ParachuteBase': r'\A3\air_f_beta\Parachute_01\Parachute_01_F.p3d',
        'LaserTarget': r'\A3\Weapons_f\laserTgt.p3d',
        'PaperCar': r'\ca\data\papAuto.p3d'
    }
    
    for class_name, expected_model in expected_models.items():
        entry = next(e for e in entries if e.class_name == class_name)
        assert entry.model == expected_model, f"Wrong model path for {class_name}"

def test_source_attribution(parser):
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    expected_sources = {
        'Car': '@em',
        'LaserTarget': '@cup_terrain_core',
        'FireSectorTarget': '@cba_a3'
    }
    
    for class_name, expected_source in expected_sources.items():
        entry = next(e for e in entries if e.class_name == class_name)
        assert entry.source == expected_source, f"Wrong source for {class_name}"

def test_empty_values(parser):
    vehicles = parser.get_category_entries('CategoryData_CfgVehicles')
    weapons = parser.get_category_entries('CategoryData_CfgWeapons')
    
    # Test Default weapon with empty inherits_from
    default_weapon = next(w for w in weapons if w.class_name == 'Default')
    assert default_weapon.inherits_from == ''
    
    # Test Man with empty model
    man = next(v for v in vehicles if v.class_name == 'Man')
    assert man.model == ''

@pytest.mark.parametrize("invalid_category", [
    "NonexistentCategory",
    "CategoryData_Invalid",
    "",
    "Validation"
])
def test_invalid_categories(parser, invalid_category):
    assert parser.get_category_entries(invalid_category) == []
    assert parser.get_category_header(invalid_category) is None

def test_malformed_entries(parser, tmp_path):
    # Create temporary malformed config file
    malformed = tmp_path / "malformed.ini"
    malformed.write_text("""
[CategoryData_Test]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
0="Malformed,,,,,,,"
1="Valid,Source,Cat,Parent,Inherits,false,10,1,model"
""")
    
    bad_parser = INIClassParser(str(malformed))
    entries = bad_parser.get_category_entries('CategoryData_Test')
    assert len(entries) == 1  # Only valid entry should be parsed

def test_empty_section_handling(parser):
    """Test handling of empty sections"""
    # MonetizedServers section is empty in sample config
    assert parser.get_category_entries('CategoryData_MonetizedServers') == []
    assert parser.get_category_header('CategoryData_MonetizedServers') is not None

def test_empty_header_handling(parser, tmp_path):
    """Test handling of empty headers"""
    config = tmp_path / "empty_header.ini"
    config.write_text("""
[CategoryData_Test]
header=
0="TestClass,Source,Cat,Parent,Inherits,false,10,1,model"
""")
    
    test_parser = INIClassParser(str(config))
    assert test_parser.get_category_header('CategoryData_Test') is None
    assert len(test_parser.get_category_entries('CategoryData_Test')) == 1

def test_double_quoted_values(parser):
    """Test handling of double-quoted values"""
    # CategoryData_ForcedMissionDifficultyArgo has double-quoted header and entry
    entries = parser.get_category_entries('CategoryData_ForcedMissionDifficultyArgo')
    assert len(entries) == 1
    entry = entries[0]
    assert entry.class_name == 'Metagame'
    assert entry.model == ''  # Empty model field

def test_empty_inherits_from_handling(parser):
    """Test handling of empty inherits_from fields"""
    entries = parser.get_category_entries('CategoryData_CfgWeapons')
    default_weapon = next(e for e in entries if e.class_name == 'Default')
    assert default_weapon.inherits_from == ''
    assert isinstance(default_weapon.inherits_from, str)

def test_parallel_disabled_for_small_datasets(parser):
    """Test that parallel processing is skipped for small datasets"""
    start = time.time()
    entries = parser.get_category_entries('CategoryData_CfgWeapons')
    processing_time = time.time() - start
    
    # Process again with parallel explicitly enabled
    start = time.time()
    parser_parallel = INIClassParser(parser.file_path, use_parallel=True)
    entries_parallel = parser_parallel.get_category_entries('CategoryData_CfgWeapons')
    parallel_time = time.time() - start

    # Results should be identical
    assert len(entries) == len(entries_parallel)
    
    # Times should be similar as parallel processing should be skipped
    assert abs(processing_time - parallel_time) < 0.1  # Allow 100ms variance

def test_complete_ini_parsing(parser):
    """Test that all items from the ini file are properly parsed."""
    # Known totals from the sample config.ini
    expected_counts = {
        'CategoryData_ForcedMissionDifficultyArgo': 1,
        'CategoryData_MonetizedServers': 0,
        'CategoryData_OfficialServersArma': 0,
        'CategoryData_OfficialServersArgo': 0,
        'CategoryData_SteamManagerConfig': 11,
        'CategoryData_ScrollBar': 0,
        'CategoryData_CfgMods': 24,
        'CategoryData_CfgVehicles': 50,
        'CategoryData_CfgWeapons': 19
    }
    
    # Test each category
    for category, expected_count in expected_counts.items():
        entries = parser.get_category_entries(category)
        assert len(entries) == expected_count, f"Category {category} has {len(entries)} entries, expected {expected_count}"
        
        # Verify each entry has all required attributes
        if entries:
            for entry in entries:
                assert hasattr(entry, 'class_name')
                assert hasattr(entry, 'source')
                assert hasattr(entry, 'category')
                assert hasattr(entry, 'parent')
                assert hasattr(entry, 'inherits_from')
                assert hasattr(entry, 'is_simple_object')
                assert hasattr(entry, 'num_properties')
                assert hasattr(entry, 'scope')
                assert hasattr(entry, 'model')
                
                # Check that string fields are not None
                assert entry.class_name is not None
                assert entry.source is not None
                assert entry.category is not None
                assert entry.parent is not None
                assert entry.inherits_from is not None
                assert entry.model is not None
                
                # Verify boolean and numeric fields
                assert isinstance(entry.is_simple_object, bool)
                assert isinstance(entry.num_properties, int)
                assert isinstance(entry.scope, int)
                
                # Basic value validation
                assert entry.num_properties >= 0
                assert entry.scope >= 0
                assert len(entry.class_name) > 0

def test_comprehensive_ini_validation(parser, config_path):
    """
    Comprehensively validate that every entry in the INI file is properly parsed
    by manually reading the file and comparing against parsed results.
    """
    # Manually parse the INI file to get raw class names
    manual_counts = {}
    manual_class_names = {}
    current_section = None
    
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin1', 'ascii']
    content = None
    
    for encoding in encodings:
        try:
            with open(config_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.readlines()
                break
        except Exception:
            continue
            
    assert content is not None, f"Could not read file with any supported encoding: {config_path}"
    
    for line in content:
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            manual_counts[current_section] = 0
            manual_class_names[current_section] = set()
        elif line and current_section and not line.startswith('header'):
            if '=' in line:
                # Extract class name from the value (first element after split)
                try:
                    value = line.split('=', 1)[1].strip('" ')
                    if value:  # Skip empty lines
                        class_name = value.split(',')[0]
                        manual_counts[current_section] += 1
                        manual_class_names[current_section].add(class_name)
                except IndexError:
                    continue

    # Compare against parser results
    for category in parser.get_categories():
        entries = parser.get_category_entries(category)
        parsed_class_names = {entry.class_name for entry in entries}
        
        # Verify counts match
        assert len(entries) == manual_counts[category], \
            f"Count mismatch in {category}: parser found {len(entries)}, actual {manual_counts[category]}"
        
        # Verify every manually found class name exists in parsed results
        for class_name in manual_class_names[category]:
            assert class_name in parsed_class_names, \
                f"Class {class_name} from {category} not found in parsed results"
        
        # Verify every parsed class name exists in manual results
        for class_name in parsed_class_names:
            assert class_name in manual_class_names[category], \
                f"Parser found unexpected class {class_name} in {category}"
        
        # Verify no entry was lost or duplicated
        assert len(parsed_class_names) == len(manual_class_names[category]), \
            f"Size mismatch in {category}: parser {len(parsed_class_names)}, actual {len(manual_class_names[category])}"
        
        # If there are entries, verify their contents
        for entry in entries:
            assert entry.class_name, "Found entry with empty class_name"
            assert hasattr(entry, 'source'), f"Missing source for {entry.class_name}"
            assert hasattr(entry, 'category'), f"Missing category for {entry.class_name}"
            assert hasattr(entry, 'num_properties'), f"Missing num_properties for {entry.class_name}"
            assert isinstance(entry.num_properties, int), f"Invalid num_properties type for {entry.class_name}"
            assert entry.num_properties >= 0, f"Negative num_properties for {entry.class_name}"
