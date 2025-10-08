#!/usr/bin/env python3
"""
Compare Three Stringing Strategies:
1. Current Strategy (Proximity-based)
2. Load Balancing Strategy 
3. Heuristic Search Strategy
"""

import json
import time
import matplotlib.pyplot as plt
import numpy as np
from solar_stringing_optimizer import SolarStringingOptimizer
from visualization_helper import SolarStringingVisualizer
from data_parsers import load_all_data
from json_input_parser import parse_json_input

def test_strategy(optimizer, strategy_name, use_snake_pattern=False, enable_load_balancing=False):
    """Test a specific strategy and return results"""
    print(f"\n{'='*60}")
    print(f"TESTING: {strategy_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    if strategy_name == "Heuristic Search":
        # Use the original heuristic method
        result = optimizer.optimize()
    else:
        # Use roof-section optimization with different settings
        result = optimizer.roof_section_optimization(
            use_snake_pattern=use_snake_pattern,
            enable_load_balancing=enable_load_balancing
        )
    
    end_time = time.time()
    optimization_time = end_time - start_time
    
    # Extract results
    if hasattr(result, 'total_mppts'):
        total_mppts = result.total_mppts
        total_panels = result.total_panels
        connections = result.connections
    else:
        # Handle dictionary format
        total_mppts = result.get('total_mppts', 0)
        total_panels = result.get('total_panels', 0)
        connections = result.get('connections', {})
        
        # If still 0, try to extract from the result structure
        if total_mppts == 0 and 'summary' in result:
            summary = result['summary']
            total_mppts = summary.get('total_mppts_used', 0)
            total_panels = summary.get('total_panels', 0)
    
    print(f"Results:")
    print(f"  - Total MPPTs: {total_mppts}")
    print(f"  - Total Panels: {total_panels}")
    print(f"  - Optimization time: {optimization_time:.3f}s")
    
    # Debug: print result structure
    print(f"  - Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"  - Result keys: {list(result.keys())}")
        if 'summary' in result:
            print(f"  - Summary keys: {list(result['summary'].keys())}")
    
    return {
        'strategy': strategy_name,
        'total_mppts': total_mppts,
        'total_panels': total_panels,
        'optimization_time': optimization_time,
        'connections': connections
    }

def analyze_string_lengths(connections):
    """Analyze string length distribution"""
    string_lengths = []
    
    for roof_plane, inverters in connections.items():
        for inverter_id, mppts in inverters.items():
            for mppt_id, panel_ids in mppts.items():
                if panel_ids:  # Only count non-empty strings
                    string_lengths.append(len(panel_ids))
    
    return string_lengths

def create_comparison_visualization(results, output_file):
    """Create individual visualizations for each strategy"""
    print("Creating individual visualizations for each strategy...")
    
    # Load the auto-design data for the visualizer
    with open('exampleCA.json', 'r') as f:
        full_data = json.load(f)
        auto_design_data = full_data.get('auto_system_design', full_data)
    
    for i, result in enumerate(results):
        strategy_name = result['strategy']
        connections = result['connections']
        
        # Use the complete results structure from the optimization
        stringing_results = result
        
        # Debug: Print connections structure and panel ID mismatch
        print(f"  Debug - {strategy_name} connections structure:")
        print(f"    Connections keys: {list(stringing_results.get('connections', {}).keys())}")
        
        # Check panel ID mismatch
        auto_design_panels = auto_design_data.get('solar_panels', [])
        auto_design_panel_ids = [panel.get('panel_id') for panel in auto_design_panels]
        print(f"    Auto-design has {len(auto_design_panel_ids)} panels")
        print(f"    First few auto-design panel IDs: {auto_design_panel_ids[:3]}")
        
        if 'connections' in stringing_results:
            for roof, inverters in stringing_results['connections'].items():
                print(f"    Roof {roof}: {len(inverters)} inverters")
                for inv_id, mppts in inverters.items():
                    print(f"      {inv_id}: {len(mppts)} MPPTs")
                    for mppt_id, panels in mppts.items():
                        print(f"        {mppt_id}: {len(panels)} panels")
                        if panels:
                            print(f"          First few panel IDs: {panels[:3]}")
                            # Check if these panel IDs exist in auto-design
                            matching = [pid for pid in panels[:3] if pid in auto_design_panel_ids]
                            print(f"          Matching in auto-design: {len(matching)}/{len(panels[:3])}")
        
        # Create individual visualization for this strategy
        visualizer = SolarStringingVisualizer(auto_design_data, stringing_results)
        
        # Create the visualization using the same method as other tests
        individual_output = f"{strategy_name.lower().replace(' ', '_')}_visualization.png"
        fig, ax = visualizer.create_stringing_visualization(individual_output)
        
        print(f"  - {strategy_name} visualization saved to: {individual_output}")
        
        # Add strategy-specific info to the output
        string_lengths = analyze_string_lengths(connections)
        if string_lengths:
            avg_length = sum(string_lengths) / len(string_lengths)
            print(f"    String lengths: {sorted(string_lengths)} (avg: {avg_length:.1f})")
    
    # Create a simple comparison summary
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    fig.suptitle('Stringing Strategy Comparison Summary', fontsize=16, fontweight='bold')
    
    strategies = [r['strategy'] for r in results]
    mppts = [r['total_mppts'] for r in results]
    panels = [r['total_panels'] for r in results]
    
    # Create comparison table
    y_pos = np.arange(len(strategies))
    
    ax.barh(y_pos, mppts, alpha=0.7, color=['skyblue', 'lightgreen', 'lightcoral'])
    ax.set_yticks(y_pos)
    ax.set_yticklabels(strategies)
    ax.set_xlabel('Total MPPTs Used')
    ax.set_title('MPPT Usage Comparison')
    
    # Add value labels
    for i, v in enumerate(mppts):
        ax.text(v + 0.1, i, str(v), va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Comparison summary saved to: {output_file}")
    plt.close()

def create_string_length_analysis(results, output_file):
    """Create string length distribution analysis"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('String Length Distribution Analysis', fontsize=16, fontweight='bold')
    
    # Flatten axes for easier indexing
    axes_flat = axes.flatten()
    
    for i, result in enumerate(results):
        ax = axes_flat[i]
        strategy_name = result['strategy']
        connections = result['connections']
        
        # Analyze string lengths
        string_lengths = analyze_string_lengths(connections)
        
        if string_lengths:
            # Create histogram
            ax.hist(string_lengths, bins=range(min(string_lengths), max(string_lengths)+2), 
                   alpha=0.7, edgecolor='black', linewidth=0.5)
            ax.set_title(f"{strategy_name}\nString Length Distribution")
            ax.set_xlabel("String Length (panels)")
            ax.set_ylabel("Number of Strings")
            ax.grid(True, alpha=0.3)
            
            # Add statistics
            avg_length = sum(string_lengths) / len(string_lengths)
            min_length = min(string_lengths)
            max_length = max(string_lengths)
            
            stats_text = f"Avg: {avg_length:.1f}\nMin: {min_length}\nMax: {max_length}\nTotal: {len(string_lengths)}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
                   verticalalignment='top')
        else:
            ax.text(0.5, 0.5, "No strings found", ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f"{strategy_name}\nNo Data")
    
    # Summary comparison plot
    ax_summary = axes_flat[3]
    strategies = [r['strategy'] for r in results]
    avg_lengths = []
    total_mppts = []
    
    for result in results:
        string_lengths = analyze_string_lengths(result['connections'])
        if string_lengths:
            avg_lengths.append(sum(string_lengths) / len(string_lengths))
        else:
            avg_lengths.append(0)
        total_mppts.append(result['total_mppts'])
    
    x = range(len(strategies))
    ax_summary.bar(x, avg_lengths, alpha=0.7, color=['skyblue', 'lightgreen', 'lightcoral'])
    ax_summary.set_title("Average String Length Comparison")
    ax_summary.set_xlabel("Strategy")
    ax_summary.set_ylabel("Average String Length (panels)")
    ax_summary.set_xticks(x)
    ax_summary.set_xticklabels(strategies, rotation=45)
    ax_summary.grid(True, alpha=0.3)
    
    # Add MPPT count as text
    for i, (avg_len, mppts) in enumerate(zip(avg_lengths, total_mppts)):
        ax_summary.text(i, avg_len + 0.1, f"{mppts} MPPTs", ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"String length analysis saved to: {output_file}")
    plt.close()

def main():
    print("="*80)
    print("THREE STRATEGY COMPARISON: CALIFORNIA EXAMPLE")
    print("="*80)
    
    # Load data
    print("Loading data from exampleCA.json...")
    panel_specs, inverter_specs, temperature_data = load_all_data(
        'exampleCA.json', 'panel_specs.csv', 'inverter_specs.csv', 'amb_temperature_data.csv', 'California'
    )
    
    print(f"Loaded {len(panel_specs)} panels")
    
    # Test strategies
    results = []
    
    # Strategy 1: Current Strategy (Proximity-based, no load balancing)
    print("\n" + "="*60)
    print("STRATEGY 1: CURRENT (PROXIMITY-BASED)")
    print("="*60)
    optimizer1 = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data)
    result1 = test_strategy(optimizer1, "Current Strategy", use_snake_pattern=True, enable_load_balancing=False)
    results.append(result1)
    
    # Strategy 2: Load Balancing Strategy
    print("\n" + "="*60)
    print("STRATEGY 2: LOAD BALANCING")
    print("="*60)
    optimizer2 = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data)
    result2 = test_strategy(optimizer2, "Load Balancing Strategy", use_snake_pattern=True, enable_load_balancing=True)
    results.append(result2)
    
    # Strategy 3: Heuristic Search
    print("\n" + "="*60)
    print("STRATEGY 3: HEURISTIC SEARCH")
    print("="*60)
    optimizer3 = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data)
    result3 = test_strategy(optimizer3, "Heuristic Search Strategy", use_snake_pattern=False, enable_load_balancing=False)
    results.append(result3)
    
    # Print comparison summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    for result in results:
        string_lengths = analyze_string_lengths(result['connections'])
        avg_length = sum(string_lengths) / len(string_lengths) if string_lengths else 0
        
        print(f"\n{result['strategy']}:")
        print(f"  - Total MPPTs: {result['total_mppts']}")
        print(f"  - Total Panels: {result['total_panels']}")
        print(f"  - Average String Length: {avg_length:.1f} panels")
        print(f"  - Optimization Time: {result['optimization_time']:.3f}s")
        print(f"  - String Lengths: {sorted(string_lengths)}")
    
    # Create visualizations
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)
    
    create_comparison_visualization(results, "three_strategy_comparison.png")
    create_string_length_analysis(results, "string_length_analysis.png")
    
    # Save results to JSON
    results_data = []
    for result in results:
        result_copy = result.copy()
        # Remove connections from JSON (too large)
        if 'connections' in result_copy:
            del result_copy['connections']
        results_data.append(result_copy)
    
    with open('three_strategy_results.json', 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nResults saved to: three_strategy_results.json")
    print(f"Visualizations saved to: three_strategy_comparison.png, string_length_analysis.png")
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE!")
    print("="*80)

if __name__ == "__main__":
    main()
