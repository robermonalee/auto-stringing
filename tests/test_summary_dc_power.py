#!/usr/bin/env python3
"""
Test script to verify DC power and DC/AC ratio are now in the summary section
Tests locally without calling the deployed API
"""

import json
from simple_stringing import SimpleStringingOptimizer
import data_parsers

def test_local_summary_fields():
    """Test that summary now includes DC power and DC/AC ratio"""
    
    print("="*80)
    print("TESTING SUMMARY DC POWER AND DC/AC RATIO FIELDS")
    print("="*80)
    
    # Create simple test data (using list format that data_parsers expects)
    auto_design_data = {
        "roof_planes": {
            "1": {"azimuth": 180.0, "orientation": "landscape", "pitch": 20.0}
        },
        "solar_panels": [
            {
                "panel_id": f"panel_{i}", 
                "azimuth": 180.0,
                "pitch": 20.0,
                "panel_orientation": "landscape",
                "pix_coords": {"c0": [100.0 + i*50, 200.0]}
            }
            for i in range(1, 10)
        ]
    }
    
    solar_panel_specs = {
        "voc": 52.79,
        "isc": 14.19,
        "vmp": 43.88,
        "imp": 13.56
    }
    
    inverter_specs_input = {
        "maxDCInputVoltage": 600.0,
        "numberOfMPPTs": 2,
        "startUpVoltage": 100.0,
        "maxDCInputCurrentPerMPPT": 12.5,
        "maxDCInputCurrentPerString": 12.5,
        "mpptOperatingVoltageMinRange": 90.0,
        "mpptOperatingVoltageMaxRange": 560.0,
        "maxShortCircuitCurrentPerMPPT": 18.0,
        "ratedACPowerW": 8000  # 8kW inverter
    }
    
    # Create objects
    print("\n1. Creating optimizer objects...")
    panels = data_parsers.create_panel_specs_objects(auto_design_data, solar_panel_specs)
    inverter_spec = data_parsers.create_inverter_specs_object(inverter_specs_input)
    temp = data_parsers.TemperatureData(-42.8, 56.7, 25.0, 5.0)  # California
    
    print(f"   ✓ Created {len(panels)} panels")
    print(f"   ✓ Inverter: {inverter_spec.rated_ac_power_w}W AC capacity")
    
    # Test with output_frontend=True (this is what the API uses)
    print("\n2. Running optimization (output_frontend=True)...")
    optimizer = SimpleStringingOptimizer(
        panel_specs=panels,
        inverter_specs=inverter_spec,
        temperature_data=temp,
        output_frontend=True
    )
    
    result = optimizer.optimize(validate_power=False)
    output = result.formatted_output
    
    # Check summary
    print("\n3. Checking SUMMARY section...")
    summary = output.get('summary', {})
    
    print(f"\n   Summary keys: {list(summary.keys())}")
    
    # Check for the new fields
    checks = {
        "system_total_dc_power_W": "System Total DC Power",
        "system_total_ac_power_W": "System Total AC Power",
        "system_dc_ac_ratio": "System DC/AC Ratio",
        "inverter_dc_ac_ratios": "Per-Inverter DC/AC Ratios"
    }
    
    all_present = True
    for field, description in checks.items():
        if field in summary:
            value = summary[field]
            print(f"   ✓ {description}: {value}")
        else:
            print(f"   ❌ {description}: NOT FOUND")
            all_present = False
    
    # Also check that data is in inverter_specs (should still be there)
    print("\n4. Verifying inverter_specs still has detailed info...")
    inverter_specs = output.get('inverter_specs', {})
    
    if inverter_specs:
        first_inv_id = list(inverter_specs.keys())[0]
        first_inv = inverter_specs[first_inv_id]
        power = first_inv.get('power', {})
        
        print(f"   ✓ {first_inv_id} has power section with keys: {list(power.keys())}")
        print(f"     - total_dc_power_W: {power.get('total_dc_power_W', 'MISSING')}")
        print(f"     - dc_ac_ratio: {power.get('dc_ac_ratio', 'MISSING')}")
    else:
        print(f"   ❌ No inverter_specs found")
        all_present = False
    
    # Save output for inspection
    print("\n5. Saving output...")
    with open('test_summary_output.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("   ✓ Saved to: test_summary_output.json")
    
    # Final result
    print("\n" + "="*80)
    if all_present:
        print("✅ SUCCESS! All DC power and DC/AC ratio fields are present in summary")
    else:
        print("❌ FAILURE! Some fields are missing from summary")
    print("="*80)
    
    return all_present

if __name__ == "__main__":
    success = test_local_summary_fields()
    exit(0 if success else 1)

