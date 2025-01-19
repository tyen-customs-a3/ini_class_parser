import pytest
from pathlib import Path
from src.api import ClassHierarchyAPI
from src.parser import ConfigParserError

def test_path_handling(tmp_path):
    # Create minimal valid config file
    config = tmp_path / "config.ini"
    config.write_text("""
[CategoryData_Test]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
test="Test,Source,Cat,Parent,,false,10,1,model"
""")
    
    # Test with string path
    api1 = ClassHierarchyAPI(str(config))
    assert isinstance(api1._parser.file_path, str)
    
    # Test with Path object
    api2 = ClassHierarchyAPI(config)
    assert isinstance(api2._parser.file_path, str)

def test_missing_file_handling(tmp_path):
    nonexistent = tmp_path / "nonexistent.ini"
    with pytest.raises(ConfigParserError):
        ClassHierarchyAPI(nonexistent)
