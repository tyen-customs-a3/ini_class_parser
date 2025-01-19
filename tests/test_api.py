import pytest
from pathlib import Path
from src.api import ClassHierarchyAPI
from src import ClassInfo, ConfigParserError

@pytest.fixture
def config_path():
    base_path = Path(__file__).parent.parent
    return str(base_path / 'sample_data' / 'config.ini')

@pytest.fixture
def api(config_path):
    return ClassHierarchyAPI(config_path)

def test_get_available_categories(api):
    categories = api.get_available_categories()
    assert 'CategoryData_CfgVehicles' in categories
    assert 'CategoryData_CfgWeapons' in categories

def test_get_class(api):
    class_info = api.get_class('CategoryData_CfgVehicles', 'Car')
    assert class_info is not None
    assert class_info.name == 'Car'
    assert class_info.source_file == '@em'
    assert class_info.parent_class == 'LandVehicle'

def test_get_class_nonexistent(api):
    class_info = api.get_class('CategoryData_CfgVehicles', 'NonExistentClass')
    assert class_info is None

def test_get_all_classes(api):
    classes = api.get_all_classes('CategoryData_CfgVehicles')
    assert len(classes) > 0
    assert 'Car' in classes
    assert 'Tank' in classes
    assert isinstance(classes['Car'], ClassInfo)

def test_get_children(api):
    children = api.get_children('CategoryData_CfgVehicles', 'LandVehicle')
    assert 'Car' in children
    assert 'Tank' in children

def test_get_descendants(api):
    descendants = api.get_descendants('CategoryData_CfgVehicles', 'Land')
    assert 'Car' in descendants
    assert 'Tank' in descendants
    assert 'LandVehicle' in descendants

def test_get_inheritance_path(api):
    path = api.get_inheritance_path('CategoryData_CfgVehicles', 'Car')
    assert path == ['Car', 'LandVehicle', 'Land', 'AllVehicles', 'All']

def test_get_inheritance_path_nonexistent(api):
    path = api.get_inheritance_path('CategoryData_CfgVehicles', 'NonExistentClass')
    assert path == []

def test_find_common_ancestor(api):
    # Test with Car and Tank which share LandVehicle as ancestor
    ancestor = api.find_common_ancestor('CategoryData_CfgVehicles', 'Car', 'Tank')
    assert ancestor == 'LandVehicle'

    # Test with unrelated classes
    ancestor = api.find_common_ancestor('CategoryData_CfgWeapons', 'PistolCore', 'RifleCore')
    assert ancestor == 'Default'  # Both inherit from Default

def test_find_common_ancestor_nonexistent(api):
    ancestor = api.find_common_ancestor('CategoryData_CfgVehicles', 'Car', 'NonExistentClass')
    assert ancestor is None

def test_is_descendant_of(api):
    # Direct descendant
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'Car', 'LandVehicle') is True
    
    # Indirect descendant
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'Car', 'Land') is True
    
    # Not a descendant
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'Land', 'Car') is False
    
    # Same class
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'Car', 'Car') is False

@pytest.mark.parametrize('category,class_name,expected_type', [
    ('CategoryData_CfgVehicles', 'Car', dict),
    ('CategoryData_CfgWeapons', 'Default', dict),
    ('NonExistentCategory', 'Whatever', dict),
])
def test_cache_behavior(api, category, class_name, expected_type):
    # First call should populate cache
    result1 = api.get_all_classes(category)
    assert isinstance(result1, expected_type)
    
    # Second call should use cache
    result2 = api.get_all_classes(category)
    assert result1 is result2  # Check if it's the same object (cached)

def test_complex_inheritance_scenarios(api):
    # Simplified to test only API-specific inheritance features
    # Test deep inheritance chain verification
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'House', 'Building')
    assert api.is_descendant_of('CategoryData_CfgVehicles', 'Building', 'Static')
    
    # Test ancestor lookup with branches
    ancestor = api.find_common_ancestor(
        'CategoryData_CfgVehicles',
        'ThingEffectFeather',
        'FxExploArmor1'
    )
    assert ancestor == 'ThingEffect'
