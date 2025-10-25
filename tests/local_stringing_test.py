#!/usr/bin/env python3
"""
Local Stringing Optimizer Test Script

This script tests the SimpleStringingOptimizer directly without calling the API.
It loads a design, sets panel and inverter specs, and runs the optimizer
to verify that the number of inverters is correctly constrained.

USAGE:
    python tests/local_stringing_test.py
"""

import json
import os
import sys
import time
import requests
import dotenv

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stringer.simple_stringing import SimpleStringingOptimizer
from stringer import data_parsers
from stringer.visualization_helper import SolarStringingVisualizer


# ============================================================================
# CONFIGURATION
# ============================================================================


# Example with two large roof sections
LATITUDE = 33.781667
LONGITUDE = -118.410278

# Example with several meidum roof sections (oct 9 design)
#LATITUDE = 33.94393950
#LONGITUDE = -117.50492295

# Example with several small roof sections and some with similar pitch and azimuth (oct 23 design)
#LATITUDE =28.3599937
#LONGITUDE = -81.3276217


STATE = "CA"  # State for temperature data

# Number of inverters to use
INVERTERS_QUANTITY = 5

OVERRIDE_INV_QUANTITY = True

# Solar Panel Specifications
SOLAR_PANEL_SPECS = {
    "voc": 34.79,
    "vmp": 28.8,
    "isc": 11.18,
    "imp": 10.52
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
    "ratedACPowerW": 8000
}

# API Configuration
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
ECS_ASD_API_URL = os.getenv("API_KEY_SYSTEM_DESIGNS")

# Output files (named based on coordinates)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output_examples')
OUTPUT_PREFIX = f"design_{LATITUDE}_{LONGITUDE}".replace(".", "_").replace("-", "neg")
OUTPUT_ASD_JSON = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_asd_design.json")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_local_stringing_output.json")
OUTPUT_VISUALIZATION = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_local_visualization.png")

# ============================================================================
# SCRIPT
# ============================================================================

def fetch_asd_design(latitude, longitude, state_code):
    """Fetch autoDesign from ECS ASD API"""
    print(f"🌍 Fetching autoDesign from ECS ASD API...")
    print(f"  Location: {latitude}, {longitude}")
    print(f"  State: {state_code}")
    
    request_id = f"stringing_test_{int(time.time())}"
    
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
        
        if 'autoDesign' in data:
            auto_design = data['autoDesign']
        elif 'auto_system_design' in data:
            auto_design = data
        else:
            auto_design = data
        
        print(f"  ✓ Successfully fetched autoDesign")
        
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

def save_output_json(data, filepath):
    """Save the output to a JSON file"""
    print(f"\n💾 Saving output to: {filepath}")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Saved")

def create_visualization(auto_design, stringing_output, output_path):
    """Create visualization of the stringing results"""
    print(f"\n🎨 Creating visualization...")
    
    try:
        # Extract the system design part, which is what the visualizer expects
        if 'auto_system_design' in auto_design:
            design_for_viz = auto_design['auto_system_design']
        else:
            design_for_viz = auto_design

        # The visualizer now expects the direct output from the optimizer
        visualizer = SolarStringingVisualizer(design_for_viz, stringing_output)
        
        # Create visualization
        fig, ax = visualizer.create_stringing_visualization(output_path, figsize=(16, 12))
        
        print(f"  ✓ Visualization saved to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test script"""
    print("="*80)
    print("LOCAL SOLAR STRINGING OPTIMIZER TEST")
    print("="*80)

    # Clean up previous output files
    if os.path.exists(OUTPUT_JSON):
        os.remove(OUTPUT_JSON)
    if os.path.exists(OUTPUT_VISUALIZATION):
        os.remove(OUTPUT_VISUALIZATION)

    # Load design
    auto_design = None
    if os.path.exists(OUTPUT_ASD_JSON):
        print(f"  ✅ Found existing autoDesign file: {OUTPUT_ASD_JSON}")
        try:
            with open(OUTPUT_ASD_JSON, 'r') as f:
                auto_design = json.load(f)
            print(f"  ✓ Loaded autoDesign from cache.")
        except Exception as e:
            print(f"  ❌ Error loading cached autoDesign: {e}. Attempting to fetch from API.")
            auto_design = fetch_asd_design(LATITUDE, LONGITUDE, STATE)
    else:
        print(f"  No cached autoDesign found. Fetching from API.")
        auto_design = fetch_asd_design(LATITUDE, LONGITUDE, STATE)

    if not auto_design:
        print(f"❌ Failed to get autoDesign. Exiting.")
        sys.exit(1)

    # Save the ASD design for reference if it was fetched
    if not os.path.exists(OUTPUT_ASD_JSON):
        save_output_json(auto_design, OUTPUT_ASD_JSON)

    # Extract the system design part
    if 'auto_system_design' in auto_design:
        design = auto_design['auto_system_design']
    else:
        design = auto_design

    print(f"  ✓ Design loaded successfully.")

    # Create panel specs objects
    panels = data_parsers.create_panel_specs_objects(design, SOLAR_PANEL_SPECS)
    print(f"  ✓ Created {len(panels)} panel objects.")

    # Create inverter specs object
    inverter = data_parsers.create_inverter_specs_object(INVERTER_SPECS)
    print(f"  ✓ Created inverter object.")

    # Parse temperature data
    temp_data_path = os.path.join(os.path.dirname(__file__), '..', 'stringer', 'amb_temperature_data.csv')
    temp = data_parsers.parse_temperature_data_csv(temp_data_path, STATE)
    print(f"  ✓ Loaded temperature data for {STATE}.")

    # Initialize optimizer
    print("\n🚀 Initializing optimizer...")
    optimizer = SimpleStringingOptimizer(
        panels,
        inverter,
        temp,
        auto_design_data=design,
        inverters_quantity=INVERTERS_QUANTITY
    )
    print(f"  ✓ Optimizer initialized with {INVERTERS_QUANTITY} inverters.")

    # Run optimization
    print("\n⚙️  Running optimization...")
    result = optimizer.optimize(override_inv_quantity=OVERRIDE_INV_QUANTITY)

    # Print summary
    summary = result.formatted_output.get('summary', {})
    print("\n" + "="*80)
    print("OPTIMIZATION RESULTS")
    print("="*80)
    print(f"  Total panels: {summary.get('total_panels', 0)}")
    print(f"  Panels stringed: {summary.get('total_panels_stringed', 0)}")
    print(f"  Total strings: {summary.get('total_strings', 0)}")
    print(f"  Total MPPTs used: {summary.get('total_mppts_used', 0)}")
    print(f"  Total inverters used: {summary.get('total_inverters_used', 0)}")
    print(f"  Stringing efficiency: {summary.get('stringing_efficiency', 0):.2f}%")
    print("="*80)

    # Verification
    if not OVERRIDE_INV_QUANTITY:
        inverters_used = summary.get('total_inverters_used', -1)
        if inverters_used == INVERTERS_QUANTITY:
            print(f"\n✅ SUCCESS: The number of inverters used ({inverters_used}) matches the expected quantity ({INVERTERS_QUANTITY}).")
        else:
            print(f"\n❌ FAILURE: The number of inverters used ({inverters_used}) does NOT match the expected quantity ({INVERTERS_QUANTITY}).")
    else:
        print("\n✅ Power validation is enabled, skipping inverter quantity check.")

    # Save the detailed output
    save_output_json(result.formatted_output, OUTPUT_JSON)

    # Create visualization
    create_visualization(auto_design, result.formatted_output, OUTPUT_VISUALIZATION)

    print("\n✅ Test complete.")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  📄 ASD Design: {OUTPUT_ASD_JSON}")
    print(f"  📄 Stringing Output: {OUTPUT_JSON}")
    print(f"  🎨 Visualization: {OUTPUT_VISUALIZATION}")
    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
