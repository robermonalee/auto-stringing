#!/usr/bin/env python3
"""
Test the roof-section-based optimization method
"""

import json
import time
from data_parsers import load_all_data
from json_input_parser import parse_json_input
from solar_stringing_optimizer import SolarStringingOptimizer

def test_roof_section_optimization():
    print("=" * 80)
    print("TESTING ROOF-SECTION-BASED OPTIMIZATION")
    print("=" * 80)
    
    # Load data for the large system (80 panels)
    print("Loading data for large system (80 panels)...")
    auto_design_data = parse_json_input('second-test.json', 'California')
    panel_specs, inverter_specs, temperature_data = load_all_data(
        'second-test.json', 'panel_specs.csv', 'inverter_specs.csv', 'amb_temperature_data.csv', 'California'
    )
    
    # Create optimizer instance
    optimizer = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, "extreme", min_heur_panels=12)
    print(f"Loaded {len(optimizer.panel_specs)} panels across {len(optimizer.panel_groups)} roof planes")
    
    # Show roof plane analysis
    print("\n" + "=" * 60)
    print("ROOF PLANE ANALYSIS")
    print("=" * 60)
    
    for roof_id, panels in optimizer.panel_groups.items():
        print(f"Roof Plane {roof_id}: {len(panels)} panels")
    
    # Test roof-section optimization
    print("\n" + "=" * 60)
    print("ROOF-SECTION OPTIMIZATION")
    print("=" * 60)
    
    start_time = time.time()
    roof_section_results = optimizer.roof_section_optimization()
    roof_section_time = time.time() - start_time
    
    # Save results
    with open('results_roof_section.json', 'w') as f:
        json.dump(roof_section_results, f, indent=2)
    
    # Compare with previous methods
    print("\n" + "=" * 80)
    print("COMPARISON WITH PREVIOUS METHODS")
    print("=" * 80)
    
    # Load previous results for comparison
    try:
        with open('results_modulus.json', 'r') as f:
            modulus_results = json.load(f)
        
        print(f"\nMODULUS HEURISTIC (80 panels):")
        print(f"  Total MPPTs: {sum(len(inv) for inv in modulus_results['connections'].values())}")
        
        # Count panels in modulus results
        total_panels_modulus = 0
        for roof_plane, inverters in modulus_results['connections'].items():
            for inv_id, mppts in inverters.items():
                for mppt_id, panel_ids in mppts.items():
                    total_panels_modulus += len(panel_ids)
        
        print(f"  Total Panels: {total_panels_modulus}")
        
    except FileNotFoundError:
        print("Modulus results not found for comparison")
    
    print(f"\nROOF-SECTION OPTIMIZATION (80 panels):")
    print(f"  Total MPPTs: {roof_section_results['total_mppts']}")
    print(f"  Optimization Time: {roof_section_time:.3f} seconds")
    print(f"  Method: {roof_section_results['optimization_method']}")
    
    # Analyze roof-section results
    print(f"\nROOF-SECTION ANALYSIS:")
    for roof_plane, inverters in roof_section_results['connections'].items():
        roof_panels = 0
        roof_mppts = 0
        for inv_id, mppts in inverters.items():
            roof_mppts += len(mppts)
            for mppt_id, panel_ids in mppts.items():
                roof_panels += len(panel_ids)
        
        print(f"  Roof {roof_plane}: {roof_panels} panels, {roof_mppts} MPPTs")
    
    print(f"\nFiles created:")
    print(f"- results_roof_section.json")

if __name__ == "__main__":
    test_roof_section_optimization()
