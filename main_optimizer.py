"""
Main Solar Stringing Optimizer

This is the main entry point for the solar stringing optimization system.
It orchestrates the complete process from data loading to final configuration output.
"""

import json
import sys
import signal
from typing import Dict, Any
from solar_stringing_optimizer import SolarStringingOptimizer
from data_parsers import load_all_data
from json_input_parser import parse_json_input


class TimeoutError(Exception):
    """Custom exception for timeout"""
    pass


def timeout_handler(signum, frame):
    """Handle timeout signal"""
    raise TimeoutError("Optimization timed out after 10 seconds")


def run_optimization_from_json(json_input_path: str, state_name: str, 
                              output_path: str = None, temp_range: str = "extreme") -> Dict[str, Any]:
    """
    Run optimization using JSON input format with embedded specifications
    
    Args:
        json_input_path: Path to JSON file containing auto-design and specifications
        state_name: Name of the state for temperature data
        output_path: Optional path to save the results JSON file
        temp_range: Temperature strategy ("extreme" or "average")
        
    Returns:
        Dictionary containing the optimal stringing configuration
    """
    print("=" * 60)
    print("SOLAR STRINGING OPTIMIZER (JSON INPUT)")
    print("=" * 60)
    
    try:
        # Set up timeout handler
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout
        
        # Load all required data from JSON input
        panel_specs, inverter_specs, temperature_data = parse_json_input(json_input_path, state_name)
        
        print(f"\nSystem Overview:")
        print(f"  Total panels: {len(panel_specs)}")
        print(f"  Inverter: {inverter_specs.inverter_id}")
        print(f"  Available MPPTs: {inverter_specs.number_of_mppts}")
        print(f"  Temperature range: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
        
        # Group panels by roof plane for analysis
        from collections import defaultdict
        roof_groups = defaultdict(list)
        for panel in panel_specs:
            roof_groups[panel.roof_plane_id].append(panel)
        
        print(f"\nPanel Distribution by Roof Plane:")
        for roof_id, panels in roof_groups.items():
            print(f"  Roof Plane {roof_id}: {len(panels)} panels")
        
        # Create optimizer and run optimization
        optimizer = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, temp_range, min_heur_panels=12)
        optimal_plan = optimizer.optimize()
        
        # Format final results
        final_config = optimizer._format_final_configuration(optimal_plan)
        
        # Add detailed information
        final_config["system_details"] = {
            "inverter_specifications": {
                "model": inverter_specs.inverter_id,
                "max_dc_voltage": inverter_specs.max_dc_voltage,
                "mppt_voltage_range": f"{inverter_specs.mppt_min_voltage}V - {inverter_specs.mppt_max_voltage}V",
                "max_current_per_mppt": inverter_specs.max_dc_current_per_mppt,
                "number_of_mppts": inverter_specs.number_of_mppts
            },
            "temperature_conditions": {
                "min_recorded_temp": f"{temperature_data.min_temp_c}°C",
                "max_recorded_temp": f"{temperature_data.max_temp_c}°C",
                "avg_high_temp": f"{temperature_data.avg_high_temp_c}°C",
                "avg_low_temp": f"{temperature_data.avg_low_temp_c}°C",
                "state": state_name,
                "temp_range_used": temp_range
            },
            "panel_specifications": {
                "total_panels": len(panel_specs),
                "voc_stc": f"{panel_specs[0].voc_stc}V" if panel_specs else "N/A",
                "isc_stc": f"{panel_specs[0].isc_stc}A" if panel_specs else "N/A",
                "temperature_functions": "Using linear functions from solar_cell_temperature_coefficients.py"
            }
        }
        
        # Save results if output path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(final_config, f, indent=2)
            print(f"\nResults saved to: {output_path}")
        
        # Cancel the alarm since we completed successfully
        signal.alarm(0)
        
        return final_config
        
    except TimeoutError as e:
        signal.alarm(0)  # Cancel the alarm
        print(f"\n{e}")
        print("The system is too large for the current algorithm. Consider:")
        print("1. Using a smaller subset of panels for testing")
        print("2. Implementing algorithm optimizations for large systems")
        print("3. Using a different optimization strategy")
        return None
        
    except Exception as e:
        signal.alarm(0)  # Cancel the alarm
        print(f"\nError during optimization: {e}")
        raise


def run_optimization(auto_design_path: str, panel_specs_path: str, 
                    inverter_specs_path: str, temperature_data_path: str, 
                    state_name: str, output_path: str = None, temp_range: str = "extreme") -> Dict[str, Any]:
    """
    Run the complete solar stringing optimization process
    
    Args:
        auto_design_path: Path to auto-design.json file
        panel_specs_path: Path to panel_specs.csv file
        inverter_specs_path: Path to inverter_specs.csv file
        temperature_data_path: Path to consolidated_temperature_data.csv file
        state_name: Name of the state for temperature data
        output_path: Optional path to save the results JSON file
        
    Returns:
        Dictionary containing the optimal stringing configuration
    """
    import time
    import os
    
    start_time = time.time()
    print("=" * 60)
    print("SOLAR STRINGING OPTIMIZER")
    print("=" * 60)
    print(f"Starting optimization at {time.strftime('%H:%M:%S')}")
    print(f"Temperature range strategy: {temp_range}")
    
    # Check file sizes for logging
    auto_design_size = os.path.getsize(auto_design_path) / 1024  # KB
    print(f"Auto-design file size: {auto_design_size:.1f} KB")
    
    try:
        # Set up timeout handler
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout
        
        # Load all required data
        print("Loading all required data...")
        panel_specs, inverter_specs, temperature_data = load_all_data(
            auto_design_path, panel_specs_path, inverter_specs_path, 
            temperature_data_path, state_name
        )
        
        print(f"\nSystem Overview:")
        print(f"  Total panels: {len(panel_specs)}")
        print(f"  Inverter: {inverter_specs.inverter_id}")
        print(f"  Available MPPTs: {inverter_specs.number_of_mppts}")
        print(f"  Temperature range: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
        
        # Group panels by roof plane for analysis
        from collections import defaultdict
        roof_groups = defaultdict(list)
        for panel in panel_specs:
            roof_groups[panel.roof_plane_id].append(panel)
        
        print(f"\nPanel Distribution by Roof Plane:")
        for roof_id, panels in roof_groups.items():
            print(f"  Roof Plane {roof_id}: {len(panels)} panels")
        
        # Create optimizer and run optimization
        optimizer = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, temp_range, min_heur_panels=12)
        optimal_plan = optimizer.optimize()
        
        # Format final results
        final_config = optimizer._format_final_configuration(optimal_plan)
        
        # Add detailed information
        final_config["system_details"] = {
            "inverter_specifications": {
                "model": inverter_specs.inverter_id,
                "max_dc_voltage": inverter_specs.max_dc_voltage,
                "mppt_voltage_range": f"{inverter_specs.mppt_min_voltage}V - {inverter_specs.mppt_max_voltage}V",
                "max_current_per_mppt": inverter_specs.max_dc_current_per_mppt,
                "number_of_mppts": inverter_specs.number_of_mppts
            },
            "temperature_conditions": {
                "min_recorded_temp": f"{temperature_data.min_temp_c}°C",
                "max_recorded_temp": f"{temperature_data.max_temp_c}°C",
                "avg_high_temp": f"{temperature_data.avg_high_temp_c}°C",
                "avg_low_temp": f"{temperature_data.avg_low_temp_c}°C",
                "state": state_name,
                "temp_range_used": temp_range
            },
            "panel_specifications": {
                "total_panels": len(panel_specs),
                "voc_stc": f"{panel_specs[0].voc_stc}V" if panel_specs else "N/A",
                "isc_stc": f"{panel_specs[0].isc_stc}A" if panel_specs else "N/A",
                "temperature_functions": "Using linear functions from solar_cell_temperature_coefficients.py"
            }
        }
        
        # Save results if output path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(final_config, f, indent=2)
            print(f"\nResults saved to: {output_path}")
        
        total_time = time.time() - start_time
        print(f"\nTotal optimization time: {total_time:.2f} seconds")
        
        # Cancel the alarm since we completed successfully
        signal.alarm(0)
        
        return final_config
        
    except TimeoutError as e:
        signal.alarm(0)  # Cancel the alarm
        print(f"\n{e}")
        print("The system is too large for the current algorithm. Consider:")
        print("1. Using a smaller subset of panels for testing")
        print("2. Implementing algorithm optimizations for large systems")
        print("3. Using a different optimization strategy")
        return None
        
    except Exception as e:
        signal.alarm(0)  # Cancel the alarm
        print(f"\nError during optimization: {e}")
        raise


def print_results_summary(config: Dict[str, Any]):
    """Print a human-readable summary of the optimization results"""
    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS SUMMARY")
    print("=" * 60)
    
    summary = config.get("summary", {})
    print(f"Total Inverters: {summary.get('total_inverters', 'N/A')}")
    print(f"Total MPPTs Used: {summary.get('total_mppts_used', 'N/A')}")
    print(f"Total Panels: {summary.get('total_panels', 'N/A')}")
    
    print(f"\nStringing Plan by Roof Plane:")
    group_plans = config.get("group_plans", {})
    for roof_plane, string_lengths in group_plans.items():
        total_panels = sum(string_lengths)
        print(f"  Roof Plane {roof_plane}: {string_lengths} ({total_panels} panels total)")
    
    system_details = config.get("system_details", {})
    if system_details:
        print(f"\nSystem Specifications:")
        inverter_specs = system_details.get("inverter_specifications", {})
        print(f"  Inverter Model: {inverter_specs.get('model', 'N/A')}")
        print(f"  MPPT Voltage Range: {inverter_specs.get('mppt_voltage_range', 'N/A')}")
        print(f"  Available MPPTs: {inverter_specs.get('number_of_mppts', 'N/A')}")
        
        temp_conditions = system_details.get("temperature_conditions", {})
        print(f"  Temperature Range: {temp_conditions.get('min_recorded_temp', 'N/A')} to {temp_conditions.get('max_recorded_temp', 'N/A')}")
        print(f"  Location: {temp_conditions.get('state', 'N/A')}")


def compare_temperature_strategies(auto_design_path: str, panel_specs_path: str, 
                                 inverter_specs_path: str, temperature_data_path: str, 
                                 state_name: str) -> Dict[str, Any]:
    """
    Compare optimization results using extreme vs average temperature strategies
    """
    print("=" * 80)
    print("TEMPERATURE STRATEGY COMPARISON")
    print("=" * 80)
    
    # Load data once
    panel_specs, inverter_specs, temperature_data = load_all_data(
        auto_design_path, panel_specs_path, inverter_specs_path, 
        temperature_data_path, state_name
    )
    
    print(f"\nTemperature Data for {state_name}:")
    print(f"  Record extremes: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
    print(f"  Average range: {temperature_data.avg_low_temp_c}°C to {temperature_data.avg_high_temp_c}°C")
    
    # Run optimization with extreme temperatures
    print(f"\n{'='*40} EXTREME TEMPERATURES {'='*40}")
    optimizer_extreme = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, "extreme")
    plan_extreme = optimizer_extreme.optimize()
    config_extreme = optimizer_extreme._format_final_configuration(plan_extreme)
    
    # Run optimization with average temperatures
    print(f"\n{'='*40} AVERAGE TEMPERATURES {'='*40}")
    optimizer_average = SolarStringingOptimizer(panel_specs, inverter_specs, temperature_data, "average")
    plan_average = optimizer_average.optimize()
    config_average = optimizer_average._format_final_configuration(plan_average)
    
    # Compare results
    print(f"\n{'='*40} COMPARISON RESULTS {'='*40}")
    print(f"Extreme Temperature Strategy:")
    print(f"  MPPTs used: {plan_extreme.total_mppts_used}")
    print(f"  Stringing plan: {plan_extreme.group_plans}")
    
    print(f"\nAverage Temperature Strategy:")
    print(f"  MPPTs used: {plan_average.total_mppts_used}")
    print(f"  Stringing plan: {plan_average.group_plans}")
    
    # Determine which is better
    if plan_extreme.total_mppts_used < plan_average.total_mppts_used:
        better_strategy = "Extreme temperatures"
        mppt_difference = plan_average.total_mppts_used - plan_extreme.total_mppts_used
    elif plan_average.total_mppts_used < plan_extreme.total_mppts_used:
        better_strategy = "Average temperatures"
        mppt_difference = plan_extreme.total_mppts_used - plan_average.total_mppts_used
    else:
        better_strategy = "Both strategies are equivalent"
        mppt_difference = 0
    
    print(f"\n{'='*40} CONCLUSION {'='*40}")
    print(f"Better strategy: {better_strategy}")
    if mppt_difference > 0:
        print(f"MPPT difference: {mppt_difference} MPPT(s)")
    
    return {
        "extreme_strategy": config_extreme,
        "average_strategy": config_average,
        "comparison": {
            "extreme_mppts": plan_extreme.total_mppts_used,
            "average_mppts": plan_average.total_mppts_used,
            "better_strategy": better_strategy,
            "mppt_difference": mppt_difference
        }
    }


def main():
    """Main entry point for command-line usage"""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  CSV Input Format:")
        print("    python main_optimizer.py <auto_design.json> <panel_specs.csv> <inverter_specs.csv> <temperature_data.csv> <state_name> [output.json] [--compare]")
        print("  JSON Input Format:")
        print("    python main_optimizer.py --json <input.json> <state_name> [output.json] [temp_range]")
        print("\nExamples:")
        print("  CSV: python main_optimizer.py auto-design.json panel_specs.csv inverter_specs.csv amb_temperature_data.csv California results.json")
        print("  JSON: python main_optimizer.py --json example_input.json California results.json extreme")
        print("  Compare: python main_optimizer.py auto-design.json panel_specs.csv inverter_specs.csv amb_temperature_data.csv California --compare")
        sys.exit(1)
    
    # Check if JSON input format is requested
    if sys.argv[1] == "--json":
        if len(sys.argv) < 4:
            print("JSON format requires: --json <input.json> <state_name> [output.json] [temp_range]")
            sys.exit(1)
        
        json_input_path = sys.argv[2]
        state_name = sys.argv[3]
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
        temp_range = sys.argv[5] if len(sys.argv) > 5 else "extreme"
        
        try:
            # Run optimization with JSON input
            config = run_optimization_from_json(json_input_path, state_name, output_path, temp_range)
            
            # Print summary
            print_results_summary(config)
            
            print(f"\nOptimization completed successfully!")
            
        except Exception as e:
            print(f"Optimization failed: {e}")
            sys.exit(1)
    
    else:
        # CSV input format (original)
        if len(sys.argv) < 6:
            print("CSV format requires: <auto_design.json> <panel_specs.csv> <inverter_specs.csv> <temperature_data.csv> <state_name> [output.json] [--compare]")
            sys.exit(1)
        
        auto_design_path = sys.argv[1]
        panel_specs_path = sys.argv[2]
        inverter_specs_path = sys.argv[3]
        temperature_data_path = sys.argv[4]
        state_name = sys.argv[5]
        
        # Check if comparison mode is requested
        if "--compare" in sys.argv:
            try:
                comparison_results = compare_temperature_strategies(
                    auto_design_path, panel_specs_path, inverter_specs_path,
                    temperature_data_path, state_name
                )
                print(f"\nComparison completed successfully!")
            except Exception as e:
                print(f"Comparison failed: {e}")
                sys.exit(1)
        else:
            output_path = sys.argv[6] if len(sys.argv) > 6 else None
            temp_range = sys.argv[7] if len(sys.argv) > 7 else "extreme"
            
            try:
                # Run optimization
                config = run_optimization(
                    auto_design_path, panel_specs_path, inverter_specs_path,
                    temperature_data_path, state_name, output_path, temp_range
                )
                
                # Print summary
                print_results_summary(config)
                
                print(f"\nOptimization completed successfully!")
                
            except Exception as e:
                print(f"Optimization failed: {e}")
                sys.exit(1)


if __name__ == "__main__":
    main()
