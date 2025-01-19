import pytest
from ini_class_parser import INIClassParser, ConfigEntry, ConfigParserError, MalformedEntryError
import os
from pathlib import Path

@pytest.fixture
def config_path():
    # Get the path relative to this test file
    base_path = Path(__file__).parent.parent
    return str(base_path / 'sample_data' / 'config.ini')

@pytest.fixture
def parser(config_path):
    return INIClassParser(config_path)

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
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    vehicles = {e.class_name: e for e in entries}
    
    # Test inheritance chain: Car -> LandVehicle -> Land -> AllVehicles -> All
    car = vehicles['Car']
    assert car.source == '@em'
    assert car.inherits_from == 'LandVehicle'
    assert vehicles['LandVehicle'].inherits_from == 'Land'
    assert vehicles['Land'].inherits_from == 'AllVehicles'
    assert vehicles['AllVehicles'].inherits_from == 'All'

def test_inheritance_tree(parser):
    tree = parser.get_inheritance_tree('CategoryData_CfgVehicles')
    assert 'All' in tree
    assert 'AllVehicles' in tree['All']
    assert 'Land' in tree['AllVehicles']
    assert 'LandVehicle' in tree['Land']
    assert 'Car' in tree['LandVehicle']
    assert 'Tank' in tree['LandVehicle']

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

def test_complex_inheritance_chain(parser):
    # Test deep inheritance chains
    entries = parser.get_category_entries('CategoryData_CfgVehicles')
    inheritance_chains = {
        'FxExploArmor1': ['ThingEffect', 'Thing', 'All'],
        'ThingEffectFeather': ['ThingEffectLight', 'ThingEffect', 'Thing', 'All'],
        'House': ['HouseBase', 'NonStrategic', 'Building', 'Static', 'All']
    }
    
    for class_name, chain in inheritance_chains.items():
        entry = next(e for e in entries if e.class_name == class_name)
        current = entry
        for parent in chain:
            assert current.inherits_from == parent, f"Wrong inheritance chain for {class_name}"
            current = next(e for e in entries if e.class_name == parent)

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
