#!/usr/bin/env python3
"""
Simple script to test different optimization methods and auto-design files
Just change the variables at the top to test different configurations
"""

import json
import time
from data_parsers import load_all_data
from json_input_parser import parse_json_input
from solar_stringing_optimizer import SolarStringingOptimizer

# =============================================================================
# CONFIGURATION - CHANGE THESE TO TEST DIFFERENT OPTIONS
# =============================================================================

# Auto-design file to use
AUTO_DESIGN_FILE = "exampleCA.json"  # Options: "auto-design.json", "second-test.json", "exampleCA.json", "example_input.json"

# Optimization method to use
OPTIMIZATION_METHOD = "roof_section"  # Options: "exhaustive", "heuristic", "roof_section", "force_heuristic"

# Stringing organization strategies
USE_SNAKE_PATTERN = False  # True: snake-pattern, False: proximity-based (default)
ENABLE_LOAD_BALANCING = False  # Enable load balancing for string lengths

# Three main strategies we compared:
# 1. Current Strategy: proximity-based (USE_SNAKE_PATTERN=False, ENABLE_LOAD_BALANCING=False)
# 2. Load Balancing: proximity-based + load balancing (USE_SNAKE_PATTERN=False, ENABLE_LOAD_BALANCING=True)  
# 3. Heuristic Search: modulus-based (OPTIMIZATION_METHOD="force_heuristic")

# Temperature strategy
TEMP_STRATEGY = "extreme"  # Options: "extreme", "average"

# State for temperature data
STATE_NAME = "California"  # Options: "California", "New Jersey", etc.

# Output file name
OUTPUT_FILE = "test_results.json"

# Create visualization?
CREATE_VISUALIZATION = True
VISUALIZATION_FILE = "test_visualization.png"

# =============================================================================
# MAIN SCRIPT - NO NEED TO MODIFY BELOW THIS LINE
# =============================================================================

def run_optimization():
    print("=" * 80)
    print("SOLAR STRINGING OPTIMIZATION TEST")
    print("=" * 80)
    print(f"Auto-design file: {AUTO_DESIGN_FILE}")
    print(f"Optimization method: {OPTIMIZATION_METHOD}")
    print(f"Temperature strategy: {TEMP_STRATEGY}")
    print(f"State: {STATE_NAME}")
    print("=" * 80)
    
    # Load data
    print("Loading data...")
    auto_design_data = parse_json_input(AUTO_DESIGN_FILE, STATE_NAME)
    panel_specs, inverter_specs, temperature_data = load_all_data(
        AUTO_DESIGN_FILE, 'panel_specs.csv', 'inverter_specs.csv', 'amb_temperature_data.csv', STATE_NAME
    )
    
    # Create optimizer instance
    optimizer = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, TEMP_STRATEGY, min_heur_panels=12)
    print(f"Loaded {len(optimizer.panel_specs)} panels across {len(optimizer.panel_groups)} roof planes")
    
    # Show roof plane analysis
    print("\nRoof Plane Analysis:")
    for roof_id, panels in optimizer.panel_groups.items():
        print(f"  Roof Plane {roof_id}: {len(panels)} panels")
    
    # Run optimization based on selected method
    print(f"\nRunning {OPTIMIZATION_METHOD} optimization...")
    start_time = time.time()
    
    if OPTIMIZATION_METHOD == "exhaustive":
        # Force exhaustive by temporarily changing the threshold
        original_use_heuristic = optimizer.use_heuristic
        optimizer.use_heuristic = False
        results = optimizer.optimize()
        optimizer.use_heuristic = original_use_heuristic
        results_dict = optimizer._format_final_configuration(results)
        
    elif OPTIMIZATION_METHOD == "heuristic":
        # Force heuristic by temporarily changing the threshold
        original_use_heuristic = optimizer.use_heuristic
        optimizer.use_heuristic = True
        results = optimizer.optimize()
        optimizer.use_heuristic = original_use_heuristic
        results_dict = optimizer._format_final_configuration(results)
        
    elif OPTIMIZATION_METHOD == "roof_section":
        results_dict = optimizer.roof_section_optimization(
            temperature_strategy=TEMP_STRATEGY,
            use_snake_pattern=USE_SNAKE_PATTERN,
            enable_load_balancing=ENABLE_LOAD_BALANCING
        )
        
    elif OPTIMIZATION_METHOD == "force_heuristic":
        results_dict = optimizer.force_heuristic_optimization()
        
    else:
        raise ValueError(f"Unknown optimization method: {OPTIMIZATION_METHOD}")
    
    optimization_time = time.time() - start_time
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results_dict, f, indent=2)
    
    # Analyze results
    print(f"\nOptimization completed in {optimization_time:.3f} seconds")
    print(f"Results saved to: {OUTPUT_FILE}")
    
    # Count MPPTs and panels
    total_mppts = 0
    total_panels = 0
    string_lengths = []
    
    connections = results_dict.get('connections', {})
    for roof_plane, inverters in connections.items():
        for inv_id, mppts in inverters.items():
            total_mppts += len(mppts)
            for mppt_id, panel_ids in mppts.items():
                string_lengths.append(len(panel_ids))
                total_panels += len(panel_ids)
    
    print(f"\nResults Summary:")
    print(f"  Total MPPTs: {total_mppts}")
    print(f"  Total Panels: {total_panels}")
    print(f"  String lengths: {sorted(string_lengths)}")
    print(f"  Average string length: {sum(string_lengths)/len(string_lengths):.1f}")
    print(f"  MPPT efficiency: {total_panels/total_mppts:.1f} panels per MPPT")
    
    # Create visualization if requested
    if CREATE_VISUALIZATION:
        try:
            from helper_functions.visualization_helper import create_visualization_from_files
            print(f"\nCreating visualization...")
            create_visualization_from_files(AUTO_DESIGN_FILE, OUTPUT_FILE, VISUALIZATION_FILE)
            print(f"Visualization saved to: {VISUALIZATION_FILE}")
        except ImportError:
            print("Warning: matplotlib not available. Skipping visualization.")
        except Exception as e:
            print(f"Warning: Could not create visualization: {e}")
    
    print(f"\nFiles created:")
    print(f"  - {OUTPUT_FILE}")
    if CREATE_VISUALIZATION:
        print(f"  - {VISUALIZATION_FILE}")

if __name__ == "__main__":
    run_optimization()
