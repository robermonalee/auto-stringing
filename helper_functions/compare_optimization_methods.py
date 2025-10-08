#!/usr/bin/env python3
"""
Compare exhaustive vs modulus-based heuristic optimization on the same small system
"""

import json
import time
from solar_stringing_optimizer import SolarStringingOptimizer

def run_comparison():
    print("=" * 80)
    print("COMPARISON: EXHAUSTIVE vs MODULUS-BASED HEURISTIC OPTIMIZATION")
    print("=" * 80)
    print("Testing on auto-design.json (11 panels)")
    print("=" * 80)
    
    # Load data first
    print("Loading data...")
    from data_parsers import load_all_data
    from json_input_parser import parse_json_input
    
    # Parse JSON input and load specifications
    auto_design_data = parse_json_input('auto-design.json', 'California')
    panel_specs, inverter_specs, temperature_data = load_all_data(
        'auto-design.json', 'panel_specs.csv', 'inverter_specs.csv', 'amb_temperature_data.csv', 'California'
    )
    
    # Create optimizer instance with loaded data
    optimizer = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, "extreme", min_heur_panels=12)
    print(f"Loaded {len(optimizer.panel_specs)} panels")
    
    # Method 1: Exhaustive Algorithm (default for small systems)
    print("\n" + "=" * 60)
    print("METHOD 1: EXHAUSTIVE ALGORITHM")
    print("=" * 60)
    
    start_time = time.time()
    exhaustive_plan = optimizer.optimize()
    exhaustive_time = time.time() - start_time
    
    # Convert to dictionary format
    exhaustive_results = optimizer._format_final_configuration(exhaustive_plan)
    
    # Save exhaustive results
    with open('results_small_exhaustive.json', 'w') as f:
        json.dump(exhaustive_results, f, indent=2)
    
    # Method 2: Modulus-Based Heuristic Algorithm (forced)
    print("\n" + "=" * 60)
    print("METHOD 2: MODULUS-BASED HEURISTIC ALGORITHM")
    print("=" * 60)
    
    start_time = time.time()
    heuristic_plan = optimizer.force_heuristic_optimization()
    heuristic_time = time.time() - start_time
    
    # Convert to dictionary format
    heuristic_results = optimizer._format_final_configuration(heuristic_plan)
    
    # Save heuristic results
    with open('results_small_heuristic.json', 'w') as f:
        json.dump(heuristic_results, f, indent=2)
    
    # Analysis and Comparison
    print("\n" + "=" * 80)
    print("COMPARISON ANALYSIS")
    print("=" * 80)
    
    def analyze_results(results, method_name):
        print(f"\n{method_name.upper()}:")
        print("-" * 40)
        
        total_inverters = len(results['connections'])
        total_mppts = 0
        total_panels = 0
        string_lengths = []
        
        for roof_plane, inverters in results['connections'].items():
            for inv_id, mppts in inverters.items():
                total_mppts += len(mppts)
                for mppt_id, panel_ids in mppts.items():
                    string_lengths.append(len(panel_ids))
                    total_panels += len(panel_ids)
        
        print(f"Total Inverters: {total_inverters}")
        print(f"Total MPPTs: {total_mppts}")
        print(f"Total Panels: {total_panels}")
        print(f"String Lengths: {sorted(string_lengths)}")
        print(f"Average String Length: {sum(string_lengths)/len(string_lengths):.1f}")
        print(f"MPPT Efficiency: {total_panels/total_mppts:.1f} panels per MPPT")
        
        # String length distribution
        from collections import Counter
        length_counts = Counter(string_lengths)
        print("String Length Distribution:")
        for length, count in sorted(length_counts.items()):
            print(f"  Length {length}: {count} strings")
        
        return {
            'inverters': total_inverters,
            'mppts': total_mppts,
            'panels': total_panels,
            'avg_string_length': sum(string_lengths)/len(string_lengths),
            'mppt_efficiency': total_panels/total_mppts,
            'string_lengths': string_lengths
        }
    
    # Analyze both methods
    exhaustive_analysis = analyze_results(exhaustive_results, 'Exhaustive Algorithm')
    heuristic_analysis = analyze_results(heuristic_results, 'Modulus Heuristic Algorithm')
    
    # Performance comparison
    print(f"\nPERFORMANCE COMPARISON:")
    print(f"Exhaustive Algorithm Time: {exhaustive_time:.3f} seconds")
    print(f"Heuristic Algorithm Time: {heuristic_time:.3f} seconds")
    print(f"Speed Improvement: {exhaustive_time/heuristic_time:.1f}x faster")
    
    # Efficiency comparison
    print(f"\nEFFICIENCY COMPARISON:")
    print(f"Exhaustive - MPPTs: {exhaustive_analysis['mppts']}, Efficiency: {exhaustive_analysis['mppt_efficiency']:.1f} panels/MPPT")
    print(f"Heuristic - MPPTs: {heuristic_analysis['mppts']}, Efficiency: {heuristic_analysis['mppt_efficiency']:.1f} panels/MPPT")
    
    if exhaustive_analysis['mppts'] < heuristic_analysis['mppts']:
        print(f"✅ Exhaustive uses {heuristic_analysis['mppts'] - exhaustive_analysis['mppts']} fewer MPPTs")
    elif heuristic_analysis['mppts'] < exhaustive_analysis['mppts']:
        print(f"✅ Heuristic uses {exhaustive_analysis['mppts'] - heuristic_analysis['mppts']} fewer MPPTs")
    else:
        print("✅ Both methods use the same number of MPPTs")
    
    # String length comparison
    print(f"\nSTRING LENGTH COMPARISON:")
    print(f"Exhaustive: {exhaustive_analysis['string_lengths']}")
    print(f"Heuristic: {heuristic_analysis['string_lengths']}")
    
    print(f"\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    
    if exhaustive_analysis['mppts'] == heuristic_analysis['mppts']:
        print("Both methods achieve the same MPPT efficiency!")
        print("The modulus-based heuristic successfully matches the exhaustive solution.")
    else:
        print("The methods produce different results.")
        print("This shows the trade-off between optimality and speed.")
    
    print(f"\nFiles created:")
    print(f"- results_small_exhaustive.json")
    print(f"- results_small_heuristic.json")

if __name__ == "__main__":
    run_comparison()
