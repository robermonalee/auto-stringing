#!/usr/bin/env python3
"""
Simple API Test Script
Fetches autoDesign from ECS ASD API using lat/lon coordinates,
then sends to stringing optimizer API with custom panel/inverter specs,
gets the stringing output, visualizes it, and saves results.

USAGE:
    python simple_api_test.py

CUSTOMIZE:
    Edit the configuration variables at the top of the script.
"""

import json
import requests
import sys
import time
import os
import dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from stringer.visualization_helper import SolarStringingVisualizer


# ============================================================================
# CONFIGURATION - Edit these values for different tests
# ============================================================================

# Location Configuration (coordinates for the site)

# Example with two large roof sections
#LATITUDE = 33.781667
#LONGITUDE = -118.410278

# Example with several small roof sections (oct 9 design)
#LATITUDE = 33.9438888
#LONGITUDE = -117.5047221

# Example with roof sections with similar pitch and azimuth (oct 23 design)
LATITUDE =28.3599937
LONGITUDE = -81.3276217



STATE_TWO_LETTERS = "CA"  # Two-letter state code

# Solar Panel Specifications
SOLAR_PANEL_SPECS = {
    "voc": 34.79,   # Open circuit voltage (V)
    "vmp": 28.8,    # Max power voltage (V)
    "isc": 11.18,   # Short circuit current (A)
    "imp": 10.52    # Max power current (A)
}

# Inverter Specifications
INVERTER_SPECS = {
    "maxDCInputVoltage": 600,
    "numberOfMPPTs": 1,
    "startUpVoltage": 60,
    "maxDCInputCurrentPerMPPT": 15,
    "maxDCInputCurrentPerString": 15,
    "mpptOperatingVoltageMinRange": 60,
    "mpptOperatingVoltageMaxRange": 480,
    "maxShortCircuitCurrentPerMPPT": 19,
    "ratedACPowerW": 8000  # Optional: for DC/AC ratio calculation
}

# API Configuration
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
ECS_ASD_API_URL = os.getenv("API_KEY_SYSTEM_DESIGNS")
STRINGING_API_URL = os.getenv("API_BASE_URL_US_EAST_1")
VALIDATE_POWER = False
OUTPUT_FRONTEND = True
OVERRIDE_INV_QUANTITY = True

# Output files (named based on coordinates)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output_examples')
OUTPUT_PREFIX = f"design_{LATITUDE}_{LONGITUDE}".replace(".", "_").replace("-", "neg")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_stringing_output.json")
OUTPUT_VISUALIZATION = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_visualization.png")
OUTPUT_ASD_JSON = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_asd_design.json")

# ============================================================================
# SCRIPT - No need to edit below unless you want to change functionality
# ============================================================================

def fetch_asd_design(latitude, longitude, state_code):
    """Fetch autoDesign from ECS ASD API"""
    print(f"🌍 Fetching autoDesign from ECS ASD API...")
    print(f"  Location: {latitude}, {longitude}")
    print(f"  State: {state_code}")
    
    # Generate unique request ID
    request_id = f"stringing_test_{int(time.time())}"
    
    # Build URL with query parameters
    params = {
        "request_id": request_id,
        "request_type": "full_asd",
        "state_two_letters": state_code,
        "lat_geocoding": latitude,
        "lon_geocoding": longitude
    }
    
    try:
        print(f"  URL: {ECS_ASD_API_URL}")
        response = requests.get(ECS_ASD_API_URL, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract autoDesign from response
        # The response structure may vary, so we'll handle common cases
        if 'autoDesign' in data:
            auto_design = data['autoDesign']
        elif 'auto_system_design' in data:
            auto_design = data
        else:
            # Assume the whole response is the design
            auto_design = data
        
        print(f"  ✓ Successfully fetched autoDesign")
        
        # Count panels in design
        panel_count = 0
        if 'auto_system_design' in auto_design:
            asd = auto_design['auto_system_design']
            if 'roofPlanes' in asd:
                for roof in asd['roofPlanes']:
                    if 'solarPanels' in roof:
                        panel_count += len(roof['solarPanels'])
        
        print(f"  ✓ Design contains {panel_count} panels")
        
        return auto_design
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to fetch autoDesign: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Error processing response: {e}")
        return None


def send_stringing_request(auto_design, panel_specs, inverter_specs, state_code):
    """Send stringing request to stringing optimizer API"""
    print(f"\n🚀 Sending request to Stringing Optimizer API...")
    print(f"  URL: {STRINGING_API_URL}")
    
    # Build request payload
    payload = {
        "auto_design": auto_design,
        "panel_specs": panel_specs,
        "inverter_specs": inverter_specs,
        "state": state_code,
        "override_inv_quantity": VALIDATE_POWER,
        "inverters_quantity": 2,
        "override_inv_quantity": OVERRIDE_INV_QUANTITY
    }
    
    # Send request
    try:
        response = requests.post(STRINGING_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"  ✓ Stringing optimization successful!")
        
        # Check if optimization time is in the response
        metadata = result.get('metadata', {})
        if 'optimization_time_seconds' in metadata:
            print(f"  ⏱️  Time: {metadata['optimization_time_seconds']:.4f}s")
        
        return result
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return None


def save_output_json(data, filepath):
    """Save the output to a JSON file"""
    print(f"\n💾 Saving output to: {filepath}")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Saved")


def create_visualization(auto_design, stringing_output, output_path):
    """Create visualization of the stringing results"""
    print(f"\n🎨 Creating visualization...")
    
    try:
        # Extract auto_system_design if nested
        if 'auto_system_design' in auto_design:
            auto_system = auto_design['auto_system_design']
        else:
            auto_system = auto_design
        
        # Create visualizer
        visualizer = SolarStringingVisualizer(auto_system, stringing_output)
        
        # Create visualization
        fig, ax = visualizer.create_stringing_visualization(output_path, figsize=(16, 12))
        
        print(f"  ✓ Visualization saved to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(stringing_output):
    """Print a summary of the results"""
    print(f"\n{'='*80}")
    print(f"STRINGING RESULTS SUMMARY")
    print(f"{'='*80}")
    
    summary = stringing_output.get('summary', {})
    
    print(f"\n📊 Statistics:")
    print(f"  Total panels: {summary.get('total_panels', 0)}")
    print(f"  Panels stringed: {summary.get('total_panels_stringed', 0)}")
    print(f"  Total strings: {summary.get('total_strings', 0)}")
    print(f"  Total MPPTs: {summary.get('total_mppts_used', 0)}")
    print(f"  Total inverters: {summary.get('total_inverters_used', 0)}")
    print(f"  Efficiency: {summary.get('stringing_efficiency', 0):.1f}%")
    
    # Show string details
    strings = stringing_output.get('strings', {})
    if strings:
        print(f"\n🔗 String Configuration:")
        for string_id, string_data in list(strings.items())[:5]:
            panel_count = len(string_data.get('panel_ids', []))
            props = string_data.get('properties', {})
            print(f"  {string_id}: {panel_count} panels @ "
                  f"{props.get('voltage_V', 0):.1f}V, "
                  f"{props.get('power_W', 0):.0f}W")
        
        if len(strings) > 5:
            print(f"  ... and {len(strings) - 5} more strings")
    
    # Show inverter status
    inverter_specs = stringing_output.get('inverter_specs', {})
    if inverter_specs:
        print(f"\n⚡ Inverter Status:")
        for inv_id, specs in inverter_specs.items():
            validation = specs.get('validation', {})
            power = specs.get('power', {})
            print(f"  {inv_id}: {validation.get('status', 'UNKNOWN')}")
            if power.get('dc_ac_ratio', 0) > 0:
                print(f"    DC/AC Ratio: {power.get('dc_ac_ratio', 0):.2f}")
    
    print(f"\n{'='*80}")


def main():
    """Main test script"""
    print("="*80)
    print("SOLAR STRINGING API TEST SCRIPT")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Location: {LATITUDE}, {LONGITUDE}")
    print(f"  State: {STATE_TWO_LETTERS}")
    print(f"  Panel Voc/Vmp: {SOLAR_PANEL_SPECS['voc']}V / {SOLAR_PANEL_SPECS['vmp']}V")
    print(f"  Panel Isc/Imp: {SOLAR_PANEL_SPECS['isc']}A / {SOLAR_PANEL_SPECS['imp']}A")
    print(f"  Inverter MPPTs: {INVERTER_SPECS['numberOfMPPTs']}")
    print(f"  Inverter Max Voltage: {INVERTER_SPECS['maxDCInputVoltage']}V")
    print(f"  Inverter AC Power: {INVERTER_SPECS['ratedACPowerW']}W")
    print(f"  Validate Power: {VALIDATE_POWER}")
    print(f"  Override Inverter Quantity: {OVERRIDE_INV_QUANTITY}")
    
    # Step 1: Fetch autoDesign from ECS ASD API
    print(f"\n{'='*80}")
    print("STEP 1: Fetch AutoDesign")
    print("="*80)
    
    auto_design = None
    if os.path.exists(OUTPUT_ASD_JSON):
        print(f"  ✅ Found existing autoDesign file: {OUTPUT_ASD_JSON}")
        try:
            with open(OUTPUT_ASD_JSON, 'r') as f:
                auto_design = json.load(f)
            print(f"  ✓ Loaded autoDesign from cache.")
        except Exception as e:
            print(f"  ❌ Error loading cached autoDesign: {e}. Attempting to fetch from API.")
            auto_design = fetch_asd_design(LATITUDE, LONGITUDE, STATE_TWO_LETTERS)
    else:
        print(f"  No cached autoDesign found. Fetching from API.")
        auto_design = fetch_asd_design(LATITUDE, LONGITUDE, STATE_TWO_LETTERS)
    
    if not auto_design:
        print(f"❌ Failed to get autoDesign. Exiting.")
        sys.exit(1)
    
    # Save the ASD design for reference (only if fetched or if cache was corrupted)
    if not os.path.exists(OUTPUT_ASD_JSON) or (auto_design and 'auto_system_design' not in auto_design): # Simple check to ensure it's a valid design
        save_output_json(auto_design, OUTPUT_ASD_JSON)
        print(f"  ✓ Saved ASD design to: {OUTPUT_ASD_JSON}")
    
    # Step 2: Send to stringing optimizer API
    print(f"\n{'='*80}")
    print("STEP 2: Run Stringing Optimization")
    print("="*80)
    payload_auto_design = auto_design
    # If the auto_design is nested under 'auto_system_design', extract it for the stringing API
    if 'auto_system_design' in auto_design:
        payload_auto_design = auto_design['auto_system_design']

    stringing_output = send_stringing_request(
        payload_auto_design, 
        SOLAR_PANEL_SPECS, 
        INVERTER_SPECS,
        STATE_TWO_LETTERS
    )
    
    if not stringing_output:
        print(f"❌ Stringing optimization failed. Exiting.")
        sys.exit(1)
    
    # Step 3: Save stringing output JSON
    print(f"\n{'='*80}")
    print("STEP 3: Save Results")
    print("="*80)
    save_output_json(stringing_output, OUTPUT_JSON)
    
    # Step 4: Print summary
    print_summary(stringing_output)
    
    # Step 5: Create visualization
    print(f"\n{'='*80}")
    print("STEP 4: Create Visualization")
    print("="*80)
    create_visualization(auto_design, stringing_output, OUTPUT_VISUALIZATION)
    
    print(f"\n{'='*80}")
    print("✅ TEST COMPLETE!")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  📄 ASD Design: {OUTPUT_ASD_JSON}")
    print(f"  📄 Stringing Output: {OUTPUT_JSON}")
    print(f"  🎨 Visualization: {OUTPUT_VISUALIZATION}")
    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()

