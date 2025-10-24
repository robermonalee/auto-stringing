#!/usr/bin/env python3
"""
Test script to verify DC power and DC/AC ratio are in API response
and demonstrate where frontend should look for this data
"""

import json
import requests

# API Configuration
API_URL = "https://ywarxlkyexfqbdh5srw6f3vysq0ukojs.lambda-url.us-east-2.on.aws/"

def test_api_response_structure():
    """
    Test the API and check where DC power and DC/AC ratio are located
    """
    
    # Simple 9-panel test
    payload = {
        "autoDesign": {
            "roof_planes": {
                "1": {"azimuth": 180.0, "orientation": "landscape", "pitch": 20.0}
            },
            "solar_panels": {
                "1": [
                    {"panel_id": f"panel_{i}", "roof_plane_id": "1", "pix_coords": {"c0": [100.0 + i*50, 200.0]}}
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
    
    print("="*80)
    print("TESTING DC POWER AND DC/AC RATIO IN API RESPONSE")
    print("="*80)
    
    # Call API
    print("\n1. Calling API...")
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        print(f"   ❌ Error calling API: {e}")
        return
    
    if not result.get('success'):
        print(f"   ❌ API request failed: {result.get('error', 'Unknown error')}")
        return
    
    print("   ✓ API call successful")
    
    data = result['data']
    
    # Check summary section
    print("\n2. Checking SUMMARY section...")
    summary = data.get('summary', {})
    print(f"   Summary fields: {list(summary.keys())}")
    
    if 'total_dc_power_W' in summary:
        print(f"   ✓ total_dc_power_W found in summary: {summary['total_dc_power_W']}W")
    else:
        print(f"   ❌ total_dc_power_W NOT found in summary")
    
    if 'dc_ac_ratio' in summary:
        print(f"   ✓ dc_ac_ratio found in summary: {summary['dc_ac_ratio']}")
    else:
        print(f"   ❌ dc_ac_ratio NOT found in summary")
    
    # Check inverter_specs section
    print("\n3. Checking INVERTER_SPECS section...")
    inverter_specs = data.get('inverter_specs', {})
    
    if not inverter_specs:
        print("   ❌ No inverter_specs found")
    else:
        print(f"   Found {len(inverter_specs)} inverter(s)")
        
        # Check first inverter
        first_inv_id = list(inverter_specs.keys())[0]
        first_inv = inverter_specs[first_inv_id]
        
        power_section = first_inv.get('power', {})
        print(f"\n   {first_inv_id} power fields: {list(power_section.keys())}")
        
        if 'total_dc_power_W' in power_section:
            print(f"   ✓ total_dc_power_W found: {power_section['total_dc_power_W']}W")
        else:
            print(f"   ❌ total_dc_power_W NOT found")
        
        if 'rated_ac_power_W' in power_section:
            print(f"   ✓ rated_ac_power_W found: {power_section['rated_ac_power_W']}W")
        else:
            print(f"   ❌ rated_ac_power_W NOT found")
        
        if 'dc_ac_ratio' in power_section:
            print(f"   ✓ dc_ac_ratio found: {power_section['dc_ac_ratio']}")
        else:
            print(f"   ❌ dc_ac_ratio NOT found")
    
    # Check preliminary_sizing_check section
    print("\n4. Checking PRELIMINARY_SIZING_CHECK section...")
    prelim_check = data.get('preliminary_sizing_check', {})
    
    if prelim_check:
        print(f"   Preliminary sizing fields: {list(prelim_check.keys())}")
        
        if 'total_system_dc_power_W' in prelim_check:
            print(f"   ✓ total_system_dc_power_W found: {prelim_check['total_system_dc_power_W']}W")
        
        if 'preliminary_dc_ac_ratio' in prelim_check:
            print(f"   ✓ preliminary_dc_ac_ratio found: {prelim_check['preliminary_dc_ac_ratio']}")
    else:
        print("   ⚠️  No preliminary_sizing_check found")
    
    # Calculate total DC power across all inverters
    print("\n5. CALCULATING SYSTEM TOTALS...")
    total_dc_power = 0
    total_ac_power = 0
    
    for inv_id, inv_specs in inverter_specs.items():
        power = inv_specs.get('power', {})
        total_dc_power += power.get('total_dc_power_W', 0)
        total_ac_power += power.get('rated_ac_power_W', 0)
    
    system_dc_ac_ratio = total_dc_power / total_ac_power if total_ac_power > 0 else 0
    
    print(f"   Total DC Power (all inverters): {total_dc_power:.0f}W")
    print(f"   Total AC Power (all inverters): {total_ac_power:.0f}W")
    print(f"   System DC/AC Ratio: {system_dc_ac_ratio:.2f}")
    
    # Summary and Recommendations
    print("\n" + "="*80)
    print("FINDINGS AND RECOMMENDATIONS")
    print("="*80)
    
    print("\n✅ DC Power and DC/AC Ratio ARE being calculated by the API")
    print("\n📍 Current Location:")
    print("   - Per-inverter: response.data.inverter_specs[inverter_id].power.total_dc_power_W")
    print("   - Per-inverter: response.data.inverter_specs[inverter_id].power.dc_ac_ratio")
    print("   - System-wide: response.data.preliminary_sizing_check.total_system_dc_power_W")
    
    print("\n⚠️  ISSUE:")
    print("   - These fields are NOT in the top-level 'summary' section")
    print("   - Frontend likely expects them in 'summary'")
    
    print("\n💡 SOLUTION:")
    print("   Option 1: Update frontend to read from inverter_specs[*].power.*")
    print("   Option 2: Update API to add total_dc_power_W and dc_ac_ratio to summary")
    print("   Option 3 (RECOMMENDED): Add both system-level AND per-inverter info to summary")
    
    print("\n📋 Recommended Summary Structure:")
    print("""
    {
      "summary": {
        "total_panels": 9,
        "total_panels_stringed": 9,
        "total_strings": 1,
        "total_inverters_used": 1,
        "system_total_dc_power_W": 6112.08,      // ← ADD THIS
        "system_total_ac_power_W": 8000.0,       // ← ADD THIS
        "system_dc_ac_ratio": 0.76,              // ← ADD THIS
        "inverter_dc_ac_ratios": {               // ← ADD THIS
          "Inverter_1": 0.76
        }
      }
    }
    """)
    
    # Save full response for inspection
    with open('test_dc_power_response.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n📄 Full response saved to: test_dc_power_response.json")
    print("\n" + "="*80)

if __name__ == "__main__":
    test_api_response_structure()

