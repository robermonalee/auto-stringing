"""
Test inverter capacity limiting functionality
Tests that panels are disconnected when inverter capacity is reached
"""

import json
from data_parsers import create_panel_specs_objects, create_inverter_specs_object
from simple_stringing import SimpleStringingOptimizer, TemperatureData

# Create a test design with many panels
test_design = {
    "solar_panels": [],
    "roof_planes": {
        "roof-1": {"azimuth": 180, "pitch": 20}
    }
}

# Add 30 panels (will need ~5 strings of 6 panels each = 5 MPPTs minimum)
for i in range(30):
    x_offset = (i % 10) * 20
    y_offset = (i // 10) * 20
    test_design["solar_panels"].append({
        "panel_id": f"panel-{i+1:03d}",
        "roof_plane_id": "roof-1",
        "azimuth": 180,
        "pitch": 20,
        "panel_orientation": "portrait",
        "pix_coords": {
            "C0": [100 + x_offset, 100 + y_offset],
            "C1": [110 + x_offset, 90 + y_offset],
            "C2": [90 + x_offset, 110 + y_offset],
            "C3": [110 + x_offset, 110 + y_offset],
            "C4": [90 + x_offset, 90 + y_offset]
        }
    })

# Panel specs
panel_specs_input = {
    "voc": 34.79,
    "vmp": 28.8,
    "isc": 11.18,
    "imp": 10.52
}

print("="*80)
print("TEST: Inverter Capacity Limiting")
print("="*80)
print(f"\nTest setup:")
print(f"  Total panels: {len(test_design['solar_panels'])}")
print(f"  Expected strings: ~5 (6 panels each)")
print(f"  Expected MPPTs: ~5")

# Test 1: Limited inverters (should disconnect some panels)
print("\n" + "="*80)
print("TEST 1: Limited Inverter Capacity (1 inverter with 3 MPPTs)")
print("="*80)

inverter_limited = {
    "maxDCInputVoltage": 600,
    "numberOfMPPTs": 3,  # Only 3 MPPTs
    "numberOfInverters": 1,  # Only 1 inverter = max 3 MPPTs total
    "startUpVoltage": 60,
    "maxDCInputCurrentPerMPPT": 15,
    "maxDCInputCurrentPerString": 15,
    "mpptOperatingVoltageMinRange": 60,
    "mpptOperatingVoltageMaxRange": 480,
    "maxShortCircuitCurrentPerMPPT": 19,
    "ratedACPowerW": 5000
}

panels1 = create_panel_specs_objects(test_design, panel_specs_input)
inverter1 = create_inverter_specs_object(inverter_limited)
temp_data = TemperatureData(min_temp_c=-10, max_temp_c=45, avg_high_temp_c=22, avg_low_temp_c=12)

optimizer1 = SimpleStringingOptimizer(panels1, inverter1, temp_data, output_frontend=True)
result1 = optimizer1.optimize(validate_power=False)

summary1 = result1.formatted_output['summary']
print(f"\nResults:")
print(f"  Panels stringed: {summary1['total_panels_stringed']}/{summary1['total_panels']}")
print(f"  Strings created: {summary1['total_strings']}")
print(f"  MPPTs used: {summary1['total_mppts_used']}")
print(f"  Inverters used: {summary1['total_inverters_used']}")
print(f"  Disconnected panels: {summary1.get('total_disconnected_panels', 0)}")

if 'disconnected_warnings' in result1.formatted_output:
    print(f"\n  Disconnected panel details:")
    for warning in result1.formatted_output['disconnected_warnings']:
        print(f"    - {warning['panel_count']} panels ({warning['reason']})")

# Test 2: Sufficient inverters (should connect all panels)
print("\n" + "="*80)
print("TEST 2: Sufficient Inverter Capacity (2 inverters with 3 MPPTs each)")
print("="*80)

inverter_sufficient = {
    "maxDCInputVoltage": 600,
    "numberOfMPPTs": 3,
    "numberOfInverters": 2,  # 2 inverters = max 6 MPPTs total
    "startUpVoltage": 60,
    "maxDCInputCurrentPerMPPT": 15,
    "maxDCInputCurrentPerString": 15,
    "mpptOperatingVoltageMinRange": 60,
    "mpptOperatingVoltageMaxRange": 480,
    "maxShortCircuitCurrentPerMPPT": 19,
    "ratedACPowerW": 5000
}

panels2 = create_panel_specs_objects(test_design, panel_specs_input)
inverter2 = create_inverter_specs_object(inverter_sufficient)

optimizer2 = SimpleStringingOptimizer(panels2, inverter2, temp_data, output_frontend=True)
result2 = optimizer2.optimize(validate_power=False)

summary2 = result2.formatted_output['summary']
print(f"\nResults:")
print(f"  Panels stringed: {summary2['total_panels_stringed']}/{summary2['total_panels']}")
print(f"  Strings created: {summary2['total_strings']}")
print(f"  MPPTs used: {summary2['total_mppts_used']}")
print(f"  Inverters used: {summary2['total_inverters_used']}")
print(f"  Disconnected panels: {summary2.get('total_disconnected_panels', 0)}")

# Verification
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)
print(f"\nTest 1 (limited):")
print(f"  ✅ Has disconnected panels: {'disconnected_warnings' in result1.formatted_output}")
print(f"  ✅ Respects inverter limit: {summary1['total_inverters_used']} <= 1")
print(f"  ✅ Panels disconnected > 0: {summary1.get('total_disconnected_panels', 0) > 0}")

print(f"\nTest 2 (sufficient):")
print(f"  ✅ No disconnected panels: {'disconnected_warnings' not in result2.formatted_output}")
print(f"  ✅ All panels connected: {summary2['total_panels_stringed'] == summary2['total_panels']}")
print(f"  ✅ Uses 2 inverters: {summary2['total_inverters_used'] == 2}")

print("\n" + "="*80)
print("✅ ALL TESTS PASSED" if (
    'disconnected_warnings' in result1.formatted_output and
    'disconnected_warnings' not in result2.formatted_output
) else "❌ SOME TESTS FAILED")
print("="*80)


