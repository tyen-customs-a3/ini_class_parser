import sys
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ini_class_parser import ClassHierarchyAPI
import time

def analyze_config(config_path: str, output_path: str):
    """Analyze a config file and save results to output file."""
    print(f"Analyzing {config_path}")
    start_time = time.time()
    
    api = ClassHierarchyAPI(config_path)
    categories = api.get_available_categories()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Config Analysis Report\n")
        f.write(f"===================\n\n")
        f.write(f"Source file: {config_path}\n")
        f.write(f"Number of categories: {len(categories)}\n\n")
        
        for category in sorted(categories):
            try:
                f.write(f"\nCategory: {category}\n")
                f.write("=" * (len(category) + 10) + "\n")
                
                # Get all classes in category
                classes = api.get_all_classes(category)
                f.write(f"Total classes: {len(classes)}\n\n")
                
                # Sample some inheritance relationships
                for class_name in sorted(list(classes.keys()))[:5]:  # First 5 classes as sample
                    info = classes[class_name]
                    f.write(f"\nClass: {class_name}\n")
                    f.write(f"Source: {info.source_file}\n")
                    if info.parent_class:
                        f.write(f"Parent: {info.parent_class}")
                        if info.parent_class not in classes:
                            f.write(" (external)")
                        f.write("\n")
                    else:
                        f.write("Parent: None\n")
                    
                    # Get inheritance path
                    path = api.get_inheritance_path(category, class_name)
                    if len(path) > 1:
                        f.write(f"Inheritance path within category: {' -> '.join(path)}\n")
                    
                    # Get direct children
                    try:
                        children = api.get_children(category, class_name)
                        if children:
                            f.write(f"Direct children: {', '.join(sorted(children)[:5])}")
                            if len(children) > 5:
                                f.write(f" (and {len(children)-5} more)")
                            f.write("\n")
                    except Exception as e:
                        f.write(f"Error getting children: {str(e)}\n")
                
                f.write("\n" + "-"*50 + "\n")
            except Exception as e:
                f.write(f"\nError processing category {category}: {str(e)}\n")
                f.write("-"*50 + "\n")
                continue

    elapsed = time.time() - start_time
    print(f"Analysis completed in {elapsed:.2f} seconds")
    print(f"Results written to {output_path}")

if __name__ == "__main__":
    config_file = r"D:\git\mission_checker\data\ConfigExtract_pcanext.ini"
    output_file = "config_analysis.txt"
    
    analyze_config(config_file, output_file)
