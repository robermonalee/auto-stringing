"""
Run Stringing Calculator for All Test Cases

This script runs the stringing calculator for oct9design.json, second-test.json, 
and test-3.json, and generates visualizations for each case.
"""

import json
import sys
from pathlib import Path
from data_parsers import parse_auto_design_json, create_panel_specs_objects, create_inverter_specs_object
from simple_stringing import SimpleStringingOptimizer, TemperatureData
from visualization_helper import SolarStringingVisualizer

def run_stringing_for_test_case(test_name: str, json_file: str):
    """
    Run stringing calculator for a single test case
    
    Args:
        test_name: Name of the test case
        json_file: Path to the JSON file containing test data
    """
    print("\n" + "="*80)
    print(f"RUNNING TEST CASE: {test_name}")
    print("="*80)
    
    try:
        # Load the test data
        print(f"Loading data from {json_file}...")
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Parse auto design data
        # Handle different JSON structures
        if 'autoDesign' in data:
            auto_design_data = data['autoDesign'].get('auto_system_design', {})
        elif 'auto_system_design' in data:
            auto_design_data = data['auto_system_design']
        elif 'auto_design' in data:
            auto_design_data = data['auto_design']
        else:
            print(f"ERROR: Could not find auto design data in {json_file}")
            return None
        
        # Extract panel specs
        if 'solarPanelSpecs' in data:
            panel_specs_input = data['solarPanelSpecs']
        else:
            # Use default specs if not provided
            panel_specs_input = {
                'voc': 34.79,
                'vmp': 28.8,
                'isc': 11.18,
                'imp': 10.52
            }
        
        # Extract inverter specs
        if 'inverterSpecs' in data:
            inverter_specs_input = data['inverterSpecs']
        else:
            # Use default specs if not provided
            inverter_specs_input = {
                'maxDCInputVoltage': 600,
                'numberOfMPPTs': 6,
                'startUpVoltage': 60,
                'maxDCInputCurrentPerMPPT': 15,
                'maxDCInputCurrentPerString': 15,
                'mpptOperatingVoltageMinRange': 60,
                'mpptOperatingVoltageMaxRange': 480,
                'maxShortCircuitCurrentPerMPPT': 19
            }
        
        # Get state for temperature data
        state = data.get('state', 'CA')
        
        # Create temperature data (using default California values)
        temp_data = TemperatureData(
            min_temp_c=-10.0,
            max_temp_c=45.0,
            avg_high_temp_c=22.0,
            avg_low_temp_c=12.0
        )
        
        # Create panel specs objects
        formatted_auto_design = {
            'solar_panels': auto_design_data.get('solar_panels', []),
            'roof_planes': auto_design_data.get('roof_planes', {})
        }
        panel_specs = create_panel_specs_objects(formatted_auto_design, panel_specs_input)
        
        # Create inverter specs object
        inverter_specs = create_inverter_specs_object(inverter_specs_input)
        
        print(f"Loaded {len(panel_specs)} panels")
        print(f"Inverter: {inverter_specs.inverter_id} with {inverter_specs.number_of_mppts} MPPTs")
        
        # Run the stringing optimizer
        print("\nRunning stringing optimizer...")
        optimizer = SimpleStringingOptimizer(
            panel_specs=panel_specs,
            inverter_specs=inverter_specs,
            temperature_data=temp_data,
            output_frontend=True
        )
        
        result = optimizer.optimize(validate_power=False)
        
        # Save the stringing output
        output_file = json_file.replace('.json', '_stringing_output.json')
        with open(output_file, 'w') as f:
            json.dump(result.formatted_output, f, indent=2)
        print(f"\nStringing output saved to: {output_file}")
        
        # Print summary
        summary = result.formatted_output.get('summary', {})
        print("\n" + "="*60)
        print("STRINGING SUMMARY")
        print("="*60)
        print(f"Total Panels: {summary.get('total_panels', 0)}")
        print(f"Panels Stringed: {summary.get('total_panels_stringed', 0)}")
        print(f"Total Strings: {summary.get('total_strings', 0)}")
        print(f"Total MPPTs: {summary.get('total_mppts_used', 0)}")
        print(f"Total Inverters: {summary.get('total_inverters_used', 0)}")
        print(f"Stringing Efficiency: {summary.get('stringing_efficiency', 0)}%")
        
        # Generate visualization
        print("\nGenerating visualization...")
        viz_output = json_file.replace('.json', '_visualization.png')
        
        try:
            visualizer = SolarStringingVisualizer(
                auto_design_data=formatted_auto_design,
                stringing_results=result.formatted_output
            )
            visualizer.create_stringing_visualization(output_path=viz_output, figsize=(20, 16))
            print(f"Visualization saved to: {viz_output}")
        except Exception as viz_error:
            print(f"Warning: Could not generate visualization: {viz_error}")
        
        return result
        
    except FileNotFoundError:
        print(f"ERROR: File not found: {json_file}")
        return None
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run stringing calculator for all test cases"""
    print("\n" + "="*80)
    print("SOLAR STRINGING CALCULATOR - TEST SUITE")
    print("="*80)
    print("\nThis script will run the stringing calculator for three test cases:")
    print("  1. oct9design.json")
    print("  2. second-test.json")
    print("  3. test-3.json")
    print("\nFor each test case, it will:")
    print("  - Run the stringing calculator")
    print("  - Generate a JSON output file with results")
    print("  - Create a visualization PNG showing the stringing layout")
    print("="*80)
    
    # Define test cases
    test_cases = [
        ("Test 1: Oct9 Design", "oct9design.json"),
        ("Test 2: Second Test", "second-test.json"),
        ("Test 3: Test 3", "test-3.json")
    ]
    
    results = {}
    
    # Run each test case
    for test_name, json_file in test_cases:
        result = run_stringing_for_test_case(test_name, json_file)
        results[test_name] = result
    
    # Print final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - ALL TEST CASES")
    print("="*80)
    
    for test_name, result in results.items():
        if result:
            summary = result.formatted_output.get('summary', {})
            print(f"\n{test_name}:")
            print(f"  ✅ Success")
            print(f"  Panels: {summary.get('total_panels_stringed', 0)}/{summary.get('total_panels', 0)}")
            print(f"  Strings: {summary.get('total_strings', 0)}")
            print(f"  Inverters: {summary.get('total_inverters_used', 0)}")
            print(f"  Efficiency: {summary.get('stringing_efficiency', 0)}%")
        else:
            print(f"\n{test_name}:")
            print(f"  ❌ Failed")
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()


