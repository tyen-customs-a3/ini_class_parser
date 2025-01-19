import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import threading
import time
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent / 'src')
if (src_path not in sys.path):
    sys.path.insert(0, src_path)

from ini_class_parser import ClassHierarchyAPI

# Configuration constants
MIN_CATEGORY_SIZE = 200  # Minimum number of classes for a category to be analyzed

class ProgressTracker:
    def __init__(self, total: int, desc: str):
        self.pbar = tqdm(total=total, desc=desc, leave=False)
        self.lock = threading.Lock()
        
    def increment(self):
        with self.lock:
            self.pbar.update(1)
            return self.pbar.n
    
    def write(self, msg: str):
        self.pbar.write(msg)
    
    def close(self):
        self.pbar.close()

def analyze_category(api: ClassHierarchyAPI, category: str, progress: ProgressTracker) -> Dict[str, Any]:
    """Analyze a single category"""
    classes = api.get_all_classes(category)
    if len(classes) < MIN_CATEGORY_SIZE:
        progress.increment()
        return None
        
    # Collect category data
    category_data = {
        'name': category,
        'size': len(classes),
        'root_classes': [name for name, info in classes.items() if not info.parent_class],
        'inheritance_chains': [],
        'children_counts': []
    }
    
    # Analyze inheritance
    for class_name in classes:
        path = api.get_inheritance_path(category, class_name)
        category_data['inheritance_chains'].append((class_name, path))
    
    # Analyze children
    for class_name in classes:
        children = api.get_children(category, class_name)
        if children:
            category_data['children_counts'].append((class_name, len(children)))
    
    count = progress.increment()
    print(f"Completed {count}/{progress.total}: {category} ({len(classes)} classes)")
    
    return category_data

def analyze_category_batch(api: ClassHierarchyAPI, categories: List[str], 
                         progress: ProgressTracker) -> List[Dict[str, Any]]:
    """Analyze multiple categories in a batch for better cache utilization"""
    results = []
    
    # Pre-load all classes and precompute paths for the batch
    all_classes = {}
    for category in categories:
        classes = api.get_all_classes(category)
        if len(classes) >= MIN_CATEGORY_SIZE:
            all_classes[category] = classes
            # Ensure paths are precomputed
            api._parser._cache.precompute_all_paths(category)
    
    # Process categories
    for category in categories:
        if category not in all_classes:
            progress.increment()
            continue
            
        classes = all_classes[category]
        if len(classes) < 20:
            progress.increment()
            continue
            
        # Collect category data
        category_data = {
            'name': category,
            'size': len(classes),
            'root_classes': [],
            'inheritance_chains': [],
            'children_counts': []
        }
        
        # Process all class relationships at once
        class_names = list(classes.keys())
        paths = {
            name: api.get_inheritance_path(category, name)
            for name in class_names
        }
        
        children_map = {}
        for name in class_names:
            children = api.get_children(category, name)
            if children:
                children_map[name] = children
                
        # Build results
        category_data['root_classes'] = [
            name for name, info in classes.items() 
            if not info.parent_class
        ]
        category_data['inheritance_chains'] = [
            (name, paths[name]) for name in class_names
        ]
        category_data['children_counts'] = [
            (name, len(children)) 
            for name, children in children_map.items()
        ]
        
        count = progress.increment()
        progress.write(f"Completed: {category} ({len(classes)} classes)")
        
        results.append(category_data)
    
    return results

def analyze_config(config_path: str, output_path: str, max_workers: int = None, min_size: int = None):
    """Analyze a config file and save results to output file."""
    print(f"Analyzing {config_path}")
    start_time = time.time()
    
    # Update minimum category size if specified
    global MIN_CATEGORY_SIZE
    if min_size is not None:
        MIN_CATEGORY_SIZE = min_size
    
    print(f"Analyzing categories with {MIN_CATEGORY_SIZE}+ classes...")
    
    api = ClassHierarchyAPI(config_path)
    categories = api.get_available_categories()
    print(f"Found {len(categories)} total categories")
    
    try:
        with tqdm(total=0, desc="Status", position=0, bar_format='{desc}') as status_bar:
            # Initialize progress tracking for categories
            progress = ProgressTracker(len(categories), "Processing")
            status_bar.write(f"Found {len(categories)} total categories")
            status_bar.write(f"Using minimum size of {MIN_CATEGORY_SIZE} classes")
            
            # Calculate batch size and create batches
            cpu_count = os.cpu_count() or 4
            max_workers = max_workers or min(cpu_count * 2, 32)
            batch_size = max(1, len(categories) // (max_workers * 2))
            
            # Split categories into batches
            category_batches = [
                categories[i:i + batch_size]
                for i in range(0, len(categories), batch_size)
            ]
            
            # Process batches in parallel
            analysis_data = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit batches for analysis
                future_to_batch = {
                    executor.submit(analyze_category_batch, api, batch, progress): batch
                    for batch in category_batches
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_batch):
                    batch = future_to_batch[future]
                    try:
                        results = future.result()
                        analysis_data.extend(results)
                    except Exception as e:
                        tqdm.write(f"Error analyzing batch: {str(e)}")
            
            progress.close()
            
            # Initialize report writing progress
            status_bar.write("\nPreparing report...")
            report_tracker = ProgressTracker(len(analysis_data), "Writing")
            
            # Write report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("Class Hierarchy Analysis\n")
                f.write("======================\n\n")
                f.write(f"Found {len(analysis_data)} categories with 20+ classes\n")
                f.write(f"Total categories: {len(categories)}\n\n")
                
                for data in analysis_data:
                    f.write(f"\n{data['name']} ({data['size']} classes)\n")
                    f.write("-" * (len(data['name']) + 12) + "\n")
                    
                    f.write(f"Root classes: {len(data['root_classes'])}\n")
                    
                    # Write deepest inheritance
                    chains = sorted(data['inheritance_chains'], key=lambda x: len(x[1]), reverse=True)
                    if chains:
                        deepest = chains[0]
                        f.write(f"Deepest inheritance: {deepest[0]} (depth: {len(deepest[1])})\n")
                        f.write(f"Path: {' -> '.join(deepest[1])}\n")
                    
                    # Write most children
                    children_data = sorted(data['children_counts'], key=lambda x: x[1], reverse=True)
                    if children_data:
                        top_parent = children_data[0]
                        f.write(f"Most children: {top_parent[0]} ({top_parent[1]} direct children)\n")
                    
                    f.write("\n")
                    report_tracker.increment()

            report_tracker.close()
            
            elapsed = time.time() - start_time
            status_bar.write(f"\nCompleted in {elapsed:.2f} seconds")
            status_bar.write(f"Results written to {output_path}")
    
    except Exception as e:
        print(f"\nError during analysis: {e}")
        raise

if __name__ == "__main__":
    config_file = r"D:\git\mission_checker\data\ConfigExtract_pcanext.ini"
    output_file = "config_analysis.txt"
    
    # Use 8 worker threads by default
    cpu_count = os.cpu_count() or 4
    
    # Can be overridden via command line argument
    min_category_size = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    analyze_config(
        config_file, 
        output_file, 
        max_workers=cpu_count,
        min_size=min_category_size
    )
