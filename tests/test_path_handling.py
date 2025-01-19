import pytest
from pathlib import Path
import os
from contextlib import contextmanager
from ini_class_parser.parser import INIClassParser, ConfigParserError
from ini_class_parser.api import ClassHierarchyAPI

@contextmanager
def cwd(path):
    """Context manager for changing working directory"""
    old_pwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_pwd)

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

def test_relative_path_handling(tmp_path):
    """Test handling of relative paths"""
    config = tmp_path / "config.ini"
    config.write_text("""
[CategoryData_Test]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
test="Test,Source,Cat,Parent,,false,10,1,model"
""")
    
    # Test with relative path
    rel_path = config.relative_to(tmp_path)
    with cwd(tmp_path):
        parser = INIClassParser(str(rel_path))
        entries = parser.get_category_entries('CategoryData_Test')
        assert len(entries) == 1
        assert entries[0].class_name == 'Test'
