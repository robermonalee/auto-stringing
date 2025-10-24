"""
Run stringing calculation with test-3.json
This script handles the combined JSON format with solarPanelSpecs and inverterSpecs in the input
"""

import json
from simple_stringing import SimpleStringingOptimizer
import data_parsers


def main():
    print("="*80)
    print("Running Stringing Calculation with test-3.json")
    print("="*80)
    
    # Load test-3.json
    print("\n📁 Loading test-3.json...")
    test3_path = 'test-3.json'
    with open(test3_path, 'r') as f:
        data = json.load(f)
    
    # Extract the different sections
    auto_design = data.get('autoDesign', {}).get('auto_system_design', {})
    solar_panels = auto_design.get('solar_panels', [])
    roof_planes = auto_design.get('roof_planes', {})
    panel_specs_raw = data.get('solarPanelSpecs', {})
    inverter_specs_raw = data.get('inverterSpecs', {})
    state = data.get('state', 'CA')
    
    print(f"  ✓ Found {len(solar_panels)} solar panels")
    print(f"  ✓ Found {len(roof_planes)} roof planes")
    print(f"  ✓ State: {state}")
    
    # Create panel specs objects using data_parsers (now supports dict input!)
    print("\n📦 Creating panel specifications...")
    auto_design_data = {'solar_panels': solar_panels, 'roof_planes': roof_planes}
    panel_specs = data_parsers.create_panel_specs_objects(auto_design_data, panel_specs_raw)
    print(f"  ✓ Created {len(panel_specs)} panel spec objects")
    print(f"  ✓ Panel specs: Voc={panel_specs_raw['voc']}V, "
          f"Vmp={panel_specs_raw['vmp']}V, "
          f"Isc={panel_specs_raw['isc']}A, "
          f"Imp={panel_specs_raw['imp']}A")
    
    # Create inverter specs object using data_parsers (now supports dict input!)
    print("\n⚡ Creating inverter specifications...")
    inverter_specs = data_parsers.create_inverter_specs_object(inverter_specs_raw)
    print(f"  ✓ Inverter: {inverter_specs.number_of_mppts} MPPTs")
    print(f"  ✓ Max DC voltage: {inverter_specs.max_dc_voltage}V")
    print(f"  ✓ MPPT range: {inverter_specs.mppt_min_voltage}V - {inverter_specs.mppt_max_voltage}V")
    print(f"  ✓ Startup voltage: {inverter_specs.startup_voltage}V")
    
    # Load temperature data
    print("\n🌡️  Loading temperature data...")
    temp_data_path = 'amb_temperature_data.csv'
    state_name = 'California' if state == 'CA' else state
    temp_data = data_parsers.parse_temperature_data_csv(temp_data_path, state_name)
    print(f"  ✓ Temperature range: {temp_data.min_temp_c}°C to {temp_data.max_temp_c}°C")
    
    # Create optimizer
    print("\n🔧 Creating optimizer...")
    optimizer = SimpleStringingOptimizer(
        panel_specs=panel_specs,
        inverter_specs=inverter_specs,
        temperature_data=temp_data,
        output_frontend=True  # Use frontend format for easier reading
    )
    
    # Run optimization
    print("\n🚀 Running stringing optimization...")
    result = optimizer.optimize(validate_power=False)  # Start without power validation
    
    # Display results
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    output = result.formatted_output
    
    print(f"\n📊 Statistics:")
    print(f"  Total panels: {output['summary']['total_panels']}")
    print(f"  Panels stringed: {output['summary']['total_panels_stringed']}")
    print(f"  Total strings: {output['summary']['total_strings']}")
    print(f"  Total MPPTs used: {output['summary']['total_mppts_used']}")
    print(f"  Total inverters used: {output['summary']['total_inverters_used']}")
    print(f"  Stringing efficiency: {output['summary']['stringing_efficiency']}%")
    
    # Show string details
    print(f"\n🔗 String Details:")
    for string_id, string_data in list(output['strings'].items())[:5]:  # Show first 5
        panel_count = len(string_data.get('panel_ids', []))
        print(f"  {string_id}: {panel_count} panels, "
              f"{string_data['properties']['voltage_V']:.1f}V, "
              f"{string_data['properties']['current_A']:.1f}A, "
              f"{string_data['properties']['power_W']:.0f}W")
        print(f"    → {string_data['inverter']} / {string_data['mppt']} / Roof {string_data['roof_section']}")
    
    if len(output['strings']) > 5:
        print(f"  ... and {len(output['strings']) - 5} more strings")
    
    # Show inverter details
    print(f"\n⚡ Inverter Details:")
    for inv_id, inv_specs in output['inverter_specs'].items():
        print(f"  {inv_id}:")
        print(f"    MPPTs: {inv_specs['num_mppts']}")
        print(f"    Total DC power: {inv_specs['power']['total_dc_power_W']:.0f}W")
        if inv_specs['power'].get('rated_ac_power_W'):
            print(f"    Rated AC power: {inv_specs['power']['rated_ac_power_W']:.0f}W")
            print(f"    DC/AC ratio: {inv_specs['power']['dc_ac_ratio']:.2f}")
        print(f"    Status: {inv_specs['validation']['status']}")
    
    # Show straggler warnings if any
    if output.get('straggler_warnings'):
        print(f"\n⚠️  Straggler Warnings:")
        for warning in output['straggler_warnings']:
            print(f"  Roof {warning['roof_id']}: {warning['panel_count']} panels cannot be connected")
            print(f"    Reason: {warning['reason']}")
            print(f"    Voltage deficit: {warning['voltage_deficit_V']:.1f}V")
    
    # Show suggestions if any
    if output.get('suggestions'):
        print(f"\n💡 Suggestions:")
        for suggestion in output['suggestions']:
            print(f"  • {suggestion}")
    
    # Save output
    output_file = 'test3_stringing_output.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Full output saved to: {output_file}")
    
    print("\n" + "="*80)
    print("✅ Stringing calculation complete!")
    print("="*80)


if __name__ == "__main__":
    main()

