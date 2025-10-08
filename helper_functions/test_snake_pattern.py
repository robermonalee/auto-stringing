#!/usr/bin/env python3
"""
Test script for Snake Pattern Stringing Organization
Demonstrates the difference between modulus-based and snake-pattern organization
"""

import json
import time
from data_parsers import load_all_data
from json_input_parser import parse_json_input
from solar_stringing_optimizer import SolarStringingOptimizer

def test_snake_pattern():
    """Test snake pattern organization vs standard modulus approach"""
    
    print("=" * 80)
    print("SNAKE PATTERN STRINGING ORGANIZATION TEST")
    print("=" * 80)
    
    # Load data
    print("Loading data from exampleCA.json...")
    auto_design_data = parse_json_input("exampleCA.json", "California")
    panel_specs, inverter_specs, temperature_data = load_all_data(
        "exampleCA.json", 'panel_specs.csv', 'inverter_specs.csv', 'amb_temperature_data.csv', "California"
    )
    
    print(f"Loaded {len(panel_specs)} panels across {len(set(p.roof_plane_id for p in panel_specs))} roof planes")
    
    # Test 1: Standard modulus approach
    print("\n" + "="*60)
    print("TEST 1: STANDARD MODULUS APPROACH")
    print("="*60)
    
    optimizer_standard = SolarStringingOptimizer(
        panel_specs, inverter_specs, temperature_data, 
        temp_range="extreme", min_heur_panels=12, use_snake_pattern=False
    )
    
    start_time = time.time()
    results_standard = optimizer_standard.roof_section_optimization()
    standard_time = time.time() - start_time
    
    print(f"Standard optimization completed in {standard_time:.3f} seconds")
    
    # Test 2: Snake pattern approach
    print("\n" + "="*60)
    print("TEST 2: SNAKE PATTERN APPROACH")
    print("="*60)
    
    optimizer_snake = SolarStringingOptimizer(
        panel_specs, inverter_specs, temperature_data, 
        temp_range="extreme", min_heur_panels=12, use_snake_pattern=True
    )
    
    start_time = time.time()
    results_snake = optimizer_snake.roof_section_optimization()
    snake_time = time.time() - start_time
    
    print(f"Snake pattern optimization completed in {snake_time:.3f} seconds")
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    standard_mppts = results_standard['summary']['total_mppts_used']
    standard_panels = results_standard['summary']['total_panels']
    snake_mppts = results_snake['summary']['total_mppts_used']
    snake_panels = results_snake['summary']['total_panels']
    
    print(f"Standard Approach:")
    print(f"  - Total MPPTs: {standard_mppts}")
    print(f"  - Total Panels: {standard_panels}")
    print(f"  - Optimization time: {standard_time:.3f}s")
    
    print(f"\nSnake Pattern Approach:")
    print(f"  - Total MPPTs: {snake_mppts}")
    print(f"  - Total Panels: {snake_panels}")
    print(f"  - Optimization time: {snake_time:.3f}s")
    
    # Analyze string organization
    print(f"\nString Organization Analysis:")
    print(f"  - Standard approach uses modulus-based grouping")
    print(f"  - Snake pattern organizes panels in top-right to bottom-left snake pattern")
    print(f"  - Snake pattern creates more visually organized stringing")
    
    # Save results
    with open('snake_pattern_results.json', 'w') as f:
        json.dump(results_snake, f, indent=2)
    
    with open('standard_results.json', 'w') as f:
        json.dump(results_standard, f, indent=2)
    
    print(f"\nResults saved:")
    print(f"  - snake_pattern_results.json")
    print(f"  - standard_results.json")
    
    # Create visualization if possible
    try:
        from visualization_helper import create_visualization_from_files
        print(f"\nCreating visualizations...")
        
        # Create standard visualization
        create_visualization_from_files("exampleCA.json", "standard_results.json", "standard_organization.png")
        print(f"  - standard_organization.png")
        
        # Create snake pattern visualization
        create_visualization_from_files("exampleCA.json", "snake_pattern_results.json", "snake_pattern_organization.png")
        print(f"  - snake_pattern_organization.png")
        
    except ImportError:
        print("Warning: matplotlib not available. Skipping visualization.")
    except Exception as e:
        print(f"Warning: Could not create visualization: {e}")
    
    print(f"\n" + "="*60)
    print("SNAKE PATTERN ORGANIZATION BENEFITS:")
    print("="*60)
    print("✅ More organized stringing patterns")
    print("✅ Panels connected in logical sequence (snake pattern)")
    print("✅ Easier to trace and understand wiring")
    print("✅ Better visual organization in diagrams")
    print("✅ Reduced wiring complexity")
    print("✅ Can be easily enabled/disabled with use_snake_pattern parameter")

if __name__ == "__main__":
    test_snake_pattern()
