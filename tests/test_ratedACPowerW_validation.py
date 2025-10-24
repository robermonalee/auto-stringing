"""
Test script to verify ratedACPowerW validation
Tests both local function and API endpoint behavior
"""

import json
from data_parsers import create_inverter_specs_object

def test_local_validation():
    """Test local validation in data_parsers.py"""
    print("\n" + "="*80)
    print("TEST 1: Local Function Validation")
    print("="*80)
    
    # Test case 1: With ratedACPowerW (should succeed)
    print("\n✅ Case 1: With ratedACPowerW = 8000")
    inverter_with_power = {
        'maxDCInputVoltage': 600,
        'numberOfMPPTs': 6,
        'startUpVoltage': 60,
        'maxDCInputCurrentPerMPPT': 15,
        'maxDCInputCurrentPerString': 15,
        'mpptOperatingVoltageMinRange': 60,
        'mpptOperatingVoltageMaxRange': 480,
        'ratedACPowerW': 8000
    }
    try:
        inv = create_inverter_specs_object(inverter_with_power)
        print(f"   ✅ SUCCESS: Inverter created with AC power = {inv.rated_ac_power_w}W")
    except ValueError as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test case 2: Without ratedACPowerW (should fail with clear error)
    print("\n❌ Case 2: Without ratedACPowerW (should fail)")
    inverter_missing_power = {
        'maxDCInputVoltage': 600,
        'numberOfMPPTs': 6,
        'startUpVoltage': 60,
        'maxDCInputCurrentPerMPPT': 15,
        'maxDCInputCurrentPerString': 15,
        'mpptOperatingVoltageMinRange': 60,
        'mpptOperatingVoltageMaxRange': 480
    }
    try:
        inv = create_inverter_specs_object(inverter_missing_power)
        print(f"   ❌ FAILED: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ SUCCESS: Error caught as expected")
        print(f"   Error message: {e}")
    
    # Test case 3: With ratedACPowerW = None (should fail)
    print("\n❌ Case 3: With ratedACPowerW = None (should fail)")
    inverter_none_power = {
        'maxDCInputVoltage': 600,
        'numberOfMPPTs': 6,
        'startUpVoltage': 60,
        'maxDCInputCurrentPerMPPT': 15,
        'maxDCInputCurrentPerString': 15,
        'mpptOperatingVoltageMinRange': 60,
        'mpptOperatingVoltageMaxRange': 480,
        'ratedACPowerW': None
    }
    try:
        inv = create_inverter_specs_object(inverter_none_power)
        print(f"   ❌ FAILED: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ SUCCESS: Error caught as expected")
        print(f"   Error message: {e}")
    
    print("\n" + "="*80)
    print("LOCAL VALIDATION TESTS COMPLETE")
    print("="*80)


def test_api_validation():
    """Test API validation (requires Flask server to be running)"""
    print("\n" + "="*80)
    print("TEST 2: API Endpoint Validation")
    print("="*80)
    print("\nNOTE: This test requires the Flask API server to be running.")
    print("To run the server: python api_server.py")
    print("Then run this test script again to test API validation.")
    print("\nTest payload that would trigger validation error:")
    
    test_payload = {
        "design": {
            "solar_panels": [],
            "roof_planes": {}
        },
        "solarPanelSpecs": {
            "voc": 34.79,
            "vmp": 28.8,
            "isc": 11.18,
            "imp": 10.52
        },
        "inverterSpecs": {
            "maxDCInputVoltage": 600,
            "numberOfMPPTs": 6,
            "startUpVoltage": 60,
            "maxDCInputCurrentPerMPPT": 15,
            "maxDCInputCurrentPerString": 15,
            "mpptOperatingVoltageMinRange": 60,
            "mpptOperatingVoltageMaxRange": 480
            # Missing ratedACPowerW - should return 400 error
        },
        "state": "CA"
    }
    
    print(json.dumps(test_payload, indent=2))
    print("\nExpected API Response:")
    print(json.dumps({
        "success": False,
        "error": "Missing required field 'ratedACPowerW' in inverter specifications. Please provide the rated AC power in watts (e.g., 'ratedACPowerW': 8000 for an 8kW inverter).",
        "error_type": "ValidationError"
    }, indent=2))
    print("\nExpected HTTP Status: 400 Bad Request")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING: ratedACPowerW VALIDATION")
    print("="*80)
    
    # Run local tests
    test_local_validation()
    
    # Show API test info
    test_api_validation()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)


