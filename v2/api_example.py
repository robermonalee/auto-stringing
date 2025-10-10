"""
Solar Stringing Optimizer - API Example
Demonstrates how to use the stringing API with different configurations
"""

from simple_stringing import SimpleStringingOptimizer
import data_parsers
import json


def example_basic():
    """Basic usage - minimal configuration"""
    print("="*80)
    print("EXAMPLE 1: Basic Usage (No Optional Parameters)")
    print("="*80)
    
    # Load data
    panels = data_parsers.create_panel_specs_objects(
        data_parsers.parse_auto_design_json('oct9design.json'),
        data_parsers.parse_panel_specs_csv('panel_specs.csv')
    )
    inverter = data_parsers.create_inverter_specs_object(
        data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    )
    temp = data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', 'California')
    
    # Create optimizer (default: technical format, no power validation)
    optimizer = SimpleStringingOptimizer(panels, inverter, temp)
    
    # Run optimization
    result = optimizer.optimize()
    
    print(f"\n📊 Results:")
    print(f"  Panels: {result.stringed_panels}/{result.total_panels}")
    print(f"  Strings: {result.total_strings}")
    print(f"  String lengths: {result.string_lengths}")
    print("\n✅ Basic optimization complete\n")


def example_with_power_validation():
    """With power validation enabled"""
    print("="*80)
    print("EXAMPLE 2: With Power Validation")
    print("="*80)
    
    panels = data_parsers.create_panel_specs_objects(
        data_parsers.parse_auto_design_json('oct9design.json'),
        data_parsers.parse_panel_specs_csv('panel_specs.csv')
    )
    inverter = data_parsers.create_inverter_specs_object(
        data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    )
    temp = data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', 'California')
    
    # Enable frontend format for easier API consumption
    optimizer = SimpleStringingOptimizer(panels, inverter, temp, output_frontend=True)
    
    # Enable power validation
    result = optimizer.optimize(validate_power=True)
    output = result.formatted_output
    
    print(f"\n📊 Results:")
    print(f"  Panels: {output['summary']['total_panels_stringed']}/{output['summary']['total_panels']}")
    print(f"  Strings: {output['summary']['total_strings']}")
    print(f"  Inverters: {output['summary']['total_inverters_used']}")
    
    # Show suggestions
    if output.get('suggestions'):
        print(f"\n💡 Suggestions:")
        for suggestion in output['suggestions']:
            print(f"  • {suggestion}")
    
    # Check inverter statuses
    statuses = {}
    for inv_specs in output['inverter_specs'].values():
        status = inv_specs['validation']['status']
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\n⚡ Inverter Status Summary: {statuses}")
    print("\n✅ Power-validated optimization complete\n")


def example_frontend_format():
    """Frontend format output"""
    print("="*80)
    print("EXAMPLE 3: Frontend Format Output")
    print("="*80)
    
    panels = data_parsers.create_panel_specs_objects(
        data_parsers.parse_auto_design_json('oct9design.json'),
        data_parsers.parse_panel_specs_csv('panel_specs.csv')
    )
    inverter = data_parsers.create_inverter_specs_object(
        data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    )
    temp = data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', 'California')
    
    # Frontend format - flat structure with references
    optimizer = SimpleStringingOptimizer(panels, inverter, temp, output_frontend=True)
    result = optimizer.optimize()
    output = result.formatted_output
    
    print(f"\n📦 Output Structure:")
    print(f"  Top-level keys: {list(output.keys())}")
    print(f"  Strings: {len(output['strings'])} entries")
    print(f"  Inverter specs: {len(output['inverter_specs'])} inverters")
    print(f"  MPPT specs: {len(output['mppt_specs'])} MPPTs")
    
    # Show first string as example
    first_string_id = list(output['strings'].keys())[0]
    first_string = output['strings'][first_string_id]
    
    print(f"\n📝 Example String ({first_string_id}):")
    print(f"  Panels: {len(first_string['panel_ids'])} panels")
    print(f"  Inverter: {first_string['inverter']}")
    print(f"  MPPT: {first_string['mppt']}")
    print(f"  Roof: {first_string['roof_section']}")
    print(f"  Voltage: {first_string['properties']['voltage_V']:.1f}V")
    print(f"  Current: {first_string['properties']['current_A']:.1f}A")
    print(f"  Power: {first_string['properties']['power_W']:.0f}W")
    
    # Save to file
    with open('example_output.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n💾 Saved output to: example_output.json")
    print("\n✅ Frontend format example complete\n")


def example_error_handling():
    """Demonstrating error handling and warnings"""
    print("="*80)
    print("EXAMPLE 4: Error Handling & Warnings")
    print("="*80)
    
    panels = data_parsers.create_panel_specs_objects(
        data_parsers.parse_auto_design_json('oct9design.json'),
        data_parsers.parse_panel_specs_csv('panel_specs.csv')
    )
    inverter = data_parsers.create_inverter_specs_object(
        data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    )
    temp = data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', 'California')
    
    optimizer = SimpleStringingOptimizer(panels, inverter, temp, output_frontend=True)
    result = optimizer.optimize(validate_power=True)
    output = result.formatted_output
    
    # Check for stragglers
    if output.get('straggler_warnings'):
        print(f"\n⚠️  Straggler Warnings:")
        for warning in output['straggler_warnings']:
            roof_id = warning.get('roof_plane_id', warning.get('roof_section', 'unknown'))
            print(f"  Roof {roof_id}: {warning['panel_count']} panels")
            print(f"    Reason: {warning.get('reason', 'N/A')}")
            if 'panel_ids' in warning:
                print(f"    Panel IDs: {warning['panel_ids'][:3]}..." if len(warning['panel_ids']) > 3 else warning['panel_ids'])
    
    # Check inverter validation
    print(f"\n🔍 Inverter Validation:")
    issues = []
    for inv_id, inv_specs in output['inverter_specs'].items():
        status = inv_specs['validation']['status']
        if status not in ['OPTIMAL', 'ACCEPTABLE']:
            issues.append(f"{inv_id}: {status}")
    
    if issues:
        print(f"  ⚠️  Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"  ✅ All inverters validated successfully")
    
    # Check if all panels were stringed
    total = output['summary']['total_panels']
    stringed = output['summary']['total_panels_stringed']
    
    print(f"\n📊 Coverage:")
    print(f"  Stringed: {stringed}/{total} panels ({100*stringed/total:.1f}%)")
    
    if stringed < total:
        unstringed = total - stringed
        print(f"  ⚠️  {unstringed} panels could not be stringed")
    
    print("\n✅ Error handling example complete\n")


if __name__ == "__main__":
    # Run all examples
    example_basic()
    example_with_power_validation()
    example_frontend_format()
    example_error_handling()
    
    print("="*80)
    print("All examples completed successfully!")
    print("="*80)

