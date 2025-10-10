"""
Test the deployed API with oct9design.json and plot the results
"""

import json
import requests
from visualization_helper import create_visualization_from_files
import data_parsers

# API Configuration
API_URL = "https://ywarxlkyexfqbdh5srw6f3vysq0ukojs.lambda-url.us-east-2.on.aws/"
API_KEY = "sk-solar-dev-2024-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"

def load_oct9design():
    """Load and parse oct9design.json"""
    with open('oct9design.json', 'r') as f:
        data = json.load(f)
    return data

def convert_to_api_format(oct9_data):
    """
    Convert oct9design.json format to API format
    Maps array_stats to roof_planes
    """
    auto_system = oct9_data.get('auto_system_design', {})
    
    # Get array_stats and rename to roof_planes for API
    roof_planes = auto_system.get('array_stats', {})
    solar_panels = auto_system.get('solar_panels', [])
    
    return {
        "auto_system_design": {
            "roof_planes": roof_planes,
            "solar_panels": solar_panels
        }
    }

def call_api(auto_design, validate_power=True):
    """Call the deployed API"""
    payload = {
        "autoDesign": auto_design,
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
            "ratedACPower": 2000
        },
        "validate_power": validate_power,
        "output_frontend": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    print("Calling API...")
    response = requests.post(API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def convert_api_output_for_visualization(api_response):
    """
    Convert API frontend output to format expected by visualization_helper
    
    Expected format:
    {
        "connections": {
            "roof_id": {
                "mppt_id": {
                    "string_id": [panel_ids]
                }
            }
        }
    }
    """
    if not api_response or not api_response.get('success'):
        return None
    
    data = api_response.get('data', {})
    strings = data.get('strings', {})
    
    # Build connections structure
    connections = {}
    
    for string_id, string_info in strings.items():
        roof_id = string_info.get('roof_section', '1')
        mppt_id = string_info.get('mppt', 'MPPT_1')
        panel_ids = string_info.get('panel_ids', [])
        
        # Initialize nested structure
        if roof_id not in connections:
            connections[roof_id] = {}
        if mppt_id not in connections[roof_id]:
            connections[roof_id][mppt_id] = {}
        
        connections[roof_id][mppt_id][string_id] = panel_ids
    
    return {"connections": connections}

def main():
    print("="*80)
    print("Testing API with oct9design.json and Plotting Results")
    print("="*80)
    
    # Load oct9design.json
    print("\n1. Loading oct9design.json...")
    oct9_data = load_oct9design()
    print(f"   Loaded {len(oct9_data['auto_system_design']['solar_panels'])} panels")
    
    # Convert to API format
    print("\n2. Converting to API format...")
    auto_design = convert_to_api_format(oct9_data)
    print(f"   Converted {len(auto_design['auto_system_design']['roof_planes'])} roof planes")
    
    # Call API without power validation
    print("\n3. Calling API (validate_power=False)...")
    result_no_validation = call_api(auto_design, validate_power=False)
    
    if result_no_validation and result_no_validation.get('success'):
        summary = result_no_validation['data']['summary']
        print(f"   ✓ Success!")
        print(f"   - Panels stringed: {summary['total_panels_stringed']}/{summary['total_panels']}")
        print(f"   - Strings: {summary['total_strings']}")
        print(f"   - Inverters: {summary['total_inverters_used']}")
        
        # Save output
        with open('oct9design_api_output_no_validation.json', 'w') as f:
            json.dump(result_no_validation, f, indent=2)
        print("   - Saved to: oct9design_api_output_no_validation.json")
    
    # Call API with power validation
    print("\n4. Calling API (validate_power=True)...")
    result_with_validation = call_api(auto_design, validate_power=True)
    
    if result_with_validation and result_with_validation.get('success'):
        summary = result_with_validation['data']['summary']
        print(f"   ✓ Success!")
        print(f"   - Panels stringed: {summary['total_panels_stringed']}/{summary['total_panels']}")
        print(f"   - Strings: {summary['total_strings']}")
        print(f"   - Inverters: {summary['total_inverters_used']}")
        
        # Print suggestions
        suggestions = result_with_validation['data'].get('suggestions', [])
        if suggestions:
            print(f"\n   💡 Suggestions:")
            for i, sug in enumerate(suggestions, 1):
                print(f"      {i}. {sug}")
        
        # Save output
        with open('oct9design_api_output_with_validation.json', 'w') as f:
            json.dump(result_with_validation, f, indent=2)
        print("   - Saved to: oct9design_api_output_with_validation.json")
    
    # Create visualization
    print("\n5. Creating visualization...")
    
    # Use the result with validation for plotting
    if result_with_validation and result_with_validation.get('success'):
        # Save the result to a temporary file for visualization
        temp_result_file = 'temp_api_result_for_viz.json'
        
        # Convert API output to visualization format
        viz_data = convert_api_output_for_visualization(result_with_validation)
        
        with open(temp_result_file, 'w') as f:
            json.dump(viz_data, f, indent=2)
        
        try:
            output_file = create_visualization_from_files(
                'oct9design.json',
                temp_result_file,
                'oct9design_api_stringing_plot.png'
            )
            print(f"   ✓ Plot saved to: {output_file}")
        except Exception as e:
            print(f"   ✗ Error creating visualization: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)

if __name__ == "__main__":
    main()

