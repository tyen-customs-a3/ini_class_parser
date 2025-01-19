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

def test_parallel_sequential_consistency(tmp_path):
    """Test that parallel and sequential parsing produce identical results"""
    # Create a config file with a decent number of entries
    config = tmp_path / "parallel_test.ini"
    config.write_text("""
[CategoryData_Test]
header="ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"
""" + "\n".join(f'entry{i}="Class{i},Source{i},Cat{i},Parent{i},Inherits{i},false,{i},1,model{i}"' for i in range(1000)))
    
    # Parse with parallel processing
    parallel_parser = INIClassParser(str(config), use_parallel=True)
    parallel_results = parallel_parser.get_category_entries('CategoryData_Test')
    
    # Parse with sequential processing
    sequential_parser = INIClassParser(str(config), use_parallel=False)
    sequential_results = sequential_parser.get_category_entries('CategoryData_Test')
    
    # Verify both parsers found the same number of entries
    assert len(parallel_results) == len(sequential_results)
    
    # Verify all entries are identical
    for par_entry, seq_entry in zip(
        sorted(parallel_results, key=lambda x: x.class_name),
        sorted(sequential_results, key=lambda x: x.class_name)
    ):
        assert par_entry.class_name == seq_entry.class_name
        assert par_entry.source == seq_entry.source
        assert par_entry.category == seq_entry.category
        assert par_entry.parent == seq_entry.parent
        assert par_entry.inherits_from == seq_entry.inherits_from
        assert par_entry.is_simple_object == seq_entry.is_simple_object
        assert par_entry.num_properties == seq_entry.num_properties
        assert par_entry.scope == seq_entry.scope
        assert par_entry.model == seq_entry.model
