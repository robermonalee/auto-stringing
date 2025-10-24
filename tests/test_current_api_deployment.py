#!/usr/bin/env python3
"""
Test the CURRENT deployed API (before the fix) to document what it returns
This will show that DC power and DC/AC ratio are NOT in the summary section
"""

import json
import requests
from datetime import datetime

# API Configuration
API_URL = "https://ywarxlkyexfqbdh5srw6f3vysq0ukojs.lambda-url.us-east-2.on.aws/"

def test_current_deployment():
    """Test current API deployment and save output"""
    
    print("="*80)
    print("TESTING CURRENT API DEPLOYMENT (BEFORE FIX)")
    print("="*80)
    print(f"\nAPI URL: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test payload - 9 panels with 8kW inverter
    # Using the format from API_KEYS_AND_URL.txt Example 2
    payload = {
        "autoDesign": {
            "auto_system_design": {
                "roof_planes": {
                    "1": {"azimuth": 180.0, "orientation": "landscape", "tilt": 20.0}
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
        },
        "state": "California",
        "solarPanelSpecs": {
            "voc": 52.79,
            "isc": 14.19,
            "vmp": 43.88,
            "imp": 13.56
        },
        "inverterSpecs": {
            "maxDCInputVoltage": 600.0,
            "numberOfMPPTs": 2,
            "startUpVoltage": 100.0,
            "maxDCInputCurrentPerMPPT": 12.5,
            "maxDCInputCurrentPerString": 12.5,
            "mpptOperatingVoltageMinRange": 90.0,
            "mpptOperatingVoltageMaxRange": 560.0,
            "maxShortCircuitCurrentPerMPPT": 18.0,
            "ratedACPowerW": 8000  # 8kW inverter
        },
        "validate_power": True,
        "output_frontend": True
    }
    
    print("\n" + "="*80)
    print("TEST PARAMETERS")
    print("="*80)
    print(f"Panels: 9")
    print(f"Inverter AC capacity: 8000W")
    print(f"Panel specs: Voc={payload['solarPanelSpecs']['voc']}V, Vmp={payload['solarPanelSpecs']['vmp']}V")
    print(f"Panel specs: Isc={payload['solarPanelSpecs']['isc']}A, Imp={payload['solarPanelSpecs']['imp']}A")
    print(f"Power validation: {payload['validate_power']}")
    print(f"Frontend output: {payload['output_frontend']}")
    
    # Call API
    print("\n" + "="*80)
    print("CALLING API...")
    print("="*80)
    
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"\n❌ API returned error status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Save error response
            error_output = {
                "status_code": response.status_code,
                "error": response.text,
                "timestamp": datetime.now().isoformat(),
                "test": "current_deployment_before_fix"
            }
            
            filename = "test_current_api_ERROR.json"
            with open(filename, 'w') as f:
                json.dump(error_output, f, indent=2)
            
            print(f"\n💾 Error saved to: {filename}")
            return None
        
        result = response.json()
        
        if not result.get('success'):
            print(f"\n❌ API request failed: {result.get('error', 'Unknown error')}")
            
            # Save failed response
            filename = "test_current_api_FAILED.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\n💾 Failed response saved to: {filename}")
            return None
        
        print("✅ API call successful!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        
        error_output = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "test": "current_deployment_before_fix"
        }
        
        filename = "test_current_api_CONNECTION_ERROR.json"
        with open(filename, 'w') as f:
            json.dump(error_output, f, indent=2)
        
        print(f"\n💾 Connection error saved to: {filename}")
        return None
    
    # Analyze response
    print("\n" + "="*80)
    print("ANALYZING RESPONSE")
    print("="*80)
    
    data = result['data']
    
    # Check summary section
    print("\n📋 SUMMARY Section:")
    summary = data.get('summary', {})
    print(f"   Fields present: {list(summary.keys())}")
    
    # Check for DC power fields
    print("\n🔍 Looking for DC power and DC/AC ratio in SUMMARY:")
    
    dc_fields_in_summary = {
        'system_total_dc_power_W': summary.get('system_total_dc_power_W'),
        'system_total_ac_power_W': summary.get('system_total_ac_power_W'),
        'system_dc_ac_ratio': summary.get('system_dc_ac_ratio'),
        'inverter_dc_ac_ratios': summary.get('inverter_dc_ac_ratios')
    }
    
    any_present = False
    for field, value in dc_fields_in_summary.items():
        if value is not None:
            print(f"   ✓ {field}: {value}")
            any_present = True
        else:
            print(f"   ❌ {field}: NOT FOUND")
    
    if not any_present:
        print("\n   ⚠️  ISSUE CONFIRMED: DC power and DC/AC ratio NOT in summary!")
    
    # Check inverter_specs section
    print("\n📋 INVERTER_SPECS Section:")
    inverter_specs = data.get('inverter_specs', {})
    
    if inverter_specs:
        inv_id = list(inverter_specs.keys())[0]
        inv = inverter_specs[inv_id]
        power = inv.get('power', {})
        
        print(f"   {inv_id} power section has:")
        print(f"   ✓ total_dc_power_W: {power.get('total_dc_power_W', 'MISSING')}")
        print(f"   ✓ rated_ac_power_W: {power.get('rated_ac_power_W', 'MISSING')}")
        print(f"   ✓ dc_ac_ratio: {power.get('dc_ac_ratio', 'MISSING')}")
        print(f"\n   📍 Location: response.data.inverter_specs['{inv_id}'].power.*")
    else:
        print("   ❌ No inverter_specs found")
    
    # Check preliminary_sizing_check
    print("\n📋 PRELIMINARY_SIZING_CHECK Section:")
    prelim = data.get('preliminary_sizing_check', {})
    
    if prelim:
        print(f"   ✓ total_system_dc_power_W: {prelim.get('total_system_dc_power_W', 'MISSING')}")
        print(f"   ✓ preliminary_dc_ac_ratio: {prelim.get('preliminary_dc_ac_ratio', 'MISSING')}")
        print(f"\n   📍 Location: response.data.preliminary_sizing_check.*")
    else:
        print("   ⚠️  No preliminary_sizing_check found")
    
    # Save full response
    filename = f"test_current_api_before_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Add metadata for tracking
    result['_test_metadata'] = {
        'test_name': 'current_deployment_before_fix',
        'timestamp': datetime.now().isoformat(),
        'api_url': API_URL,
        'test_description': 'Testing CURRENT deployed API to confirm DC power not in summary',
        'expected_issue': 'DC power and DC/AC ratio should NOT be in summary section'
    }
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n" + "="*80)
    print("SUMMARY OF FINDINGS")
    print("="*80)
    
    if any_present:
        print("\n⚠️  UNEXPECTED: Some DC power fields ARE in summary")
        print("    This suggests the API may already have the fix deployed")
    else:
        print("\n✅ CONFIRMED: DC power and DC/AC ratio NOT in summary section")
        print("    (This is the expected bug that needs to be fixed)")
    
    print(f"\n💾 Full response saved to: {filename}")
    print(f"📏 Response size: {len(json.dumps(result))} bytes")
    
    # Print summary values for reference
    print("\n" + "="*80)
    print("REFERENCE VALUES")
    print("="*80)
    print(f"Total panels: {summary.get('total_panels', 'N/A')}")
    print(f"Panels stringed: {summary.get('total_panels_stringed', 'N/A')}")
    print(f"Total strings: {summary.get('total_strings', 'N/A')}")
    print(f"Total inverters: {summary.get('total_inverters_used', 'N/A')}")
    
    if inverter_specs:
        inv_id = list(inverter_specs.keys())[0]
        power = inverter_specs[inv_id].get('power', {})
        print(f"\nFrom inverter_specs['{inv_id}'].power:")
        print(f"  DC Power: {power.get('total_dc_power_W', 'N/A')}W")
        print(f"  AC Power: {power.get('rated_ac_power_W', 'N/A')}W")
        print(f"  DC/AC Ratio: {power.get('dc_ac_ratio', 'N/A')}")
    
    print("\n" + "="*80)
    
    return result

if __name__ == "__main__":
    result = test_current_deployment()
    
    if result:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed or API returned error")

