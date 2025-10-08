"""
JSON Input Parser for Solar Stringing Optimizer

This module handles JSON input format where panel and inverter specifications
are provided directly in the JSON structure along with auto-design data.
"""

import json
from typing import Dict, List, Any, Tuple
from solar_stringing_optimizer import PanelSpecs, InverterSpecs, TemperatureData


def parse_json_input(json_file_path: str, state_name: str) -> Tuple[List[PanelSpecs], InverterSpecs, TemperatureData]:
    """
    Parse JSON input file containing auto-design data and specifications
    
    Args:
        json_file_path: Path to the JSON file containing all input data
        state_name: Name of the state for temperature data lookup
        
    Returns:
        Tuple of (panel_specs, inverter_specs, temperature_data)
    """
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Extract auto-design data
    auto_design_data = data.get('auto_design', {})
    solar_panels = auto_design_data.get('solar_panels', [])
    roof_planes = auto_design_data.get('roof_planes', {})
    
    # Extract panel specifications
    panel_specs_json = data.get('solarPanelSpecs', {})
    panel_specs = create_panel_specs_from_json(solar_panels, panel_specs_json)
    
    # Extract inverter specifications
    inverter_specs_json = data.get('inverterSpecs', {})
    inverter_specs = create_inverter_specs_from_json(inverter_specs_json)
    
    # Extract temperature data (this would need to be provided or looked up)
    temperature_data = create_temperature_data_from_state(state_name)
    
    return panel_specs, inverter_specs, temperature_data


def create_panel_specs_from_json(solar_panels: List[Dict], panel_specs_json: Dict) -> List[PanelSpecs]:
    """
    Create PanelSpecs objects from JSON panel data and specifications
    
    Args:
        solar_panels: List of solar panel data from auto-design
        panel_specs_json: Panel specifications from JSON input
        
    Returns:
        List of PanelSpecs objects
    """
    panels = []
    
    for panel_data in solar_panels:
        # Extract pixel coordinates (c0 is the center)
        pix_coords = panel_data.get('pix_coords', {})
        c0 = pix_coords.get('c0', [0, 0])
        center_coords = (float(c0[0]), float(c0[1]))
        
        panel_spec = PanelSpecs(
            panel_id=panel_data.get('panel_id', ''),
            voc_stc=panel_specs_json.get('voc', 0),
            isc_stc=panel_specs_json.get('isc', 0),
            vmpp_stc=panel_specs_json.get('vmp', 0),
            impp_stc=panel_specs_json.get('imp', 0),
            roof_plane_id=panel_data.get('roof_plane_id', ''),
            center_coords=center_coords
        )
        panels.append(panel_spec)
    
    return panels


def create_inverter_specs_from_json(inverter_specs_json: Dict) -> InverterSpecs:
    """
    Create InverterSpecs object from JSON inverter specifications
    
    Args:
        inverter_specs_json: Inverter specifications from JSON input
        
    Returns:
        InverterSpecs object
    """
    return InverterSpecs(
        inverter_id="json_inverter",
        max_dc_voltage=inverter_specs_json.get('maxDCInputVoltage', 0),
        mppt_min_voltage=inverter_specs_json.get('mpptOperatingVoltageMinRange', 0),
        mppt_max_voltage=inverter_specs_json.get('mpptOperatingVoltageMaxRange', 0),
        max_dc_current_per_mppt=inverter_specs_json.get('maxDCInputCurrentPerMPPT', 0),
        max_dc_current_per_string=inverter_specs_json.get('maxDCInputCurrentPerString', 0),
        number_of_mppts=inverter_specs_json.get('numberOfMPPTs', 0),
        startup_voltage=inverter_specs_json.get('startUpVoltage', 0)
    )


def create_temperature_data_from_state(state_name: str) -> TemperatureData:
    """
    Create TemperatureData object by looking up state data from CSV file
    
    Args:
        state_name: Name of the state for temperature data lookup
        
    Returns:
        TemperatureData object
    """
    import csv
    
    # Load temperature data from CSV using built-in csv module
    with open('amb_temperature_data.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    
    # Find the row for the specified state
    state_row = None
    for row in rows:
        if row['State_Name'].lower() == state_name.lower():
            state_row = row
            break
    
    if state_row is None:
        raise ValueError(f"State '{state_name}' not found in temperature data")
    
    return TemperatureData(
        min_temp_c=float(state_row['Min_Recorded_Temperature_Celsius']),
        max_temp_c=float(state_row['Max_Recorded_Temperature_Celsius']),
        avg_high_temp_c=float(state_row['Average_High_Temperature_2024_Celsius']),
        avg_low_temp_c=float(state_row['Average_Low_Temperature_2024_Celsius'])
    )


def create_example_json_input():
    """
    Create an example JSON input file with the structure you specified
    """
    example_data = {
        "auto_design": {
            "solar_panels": [
                {
                    "panel_id": "panel_001",
                    "roof_plane_id": "1",
                    "pix_coords": {
                        "c0": [100, 200],
                        "c1": [120, 180],
                        "c2": [80, 180],
                        "c3": [80, 220],
                        "c4": [120, 220]
                    }
                },
                {
                    "panel_id": "panel_002", 
                    "roof_plane_id": "1",
                    "pix_coords": {
                        "c0": [150, 200],
                        "c1": [170, 180],
                        "c2": [130, 180],
                        "c3": [130, 220],
                        "c4": [170, 220]
                    }
                }
            ],
            "roof_planes": {
                "1": {
                    "azimuth": 180,
                    "orientation": "south",
                    "pitch": 30,
                    "polygon": "POLYGON ((50 150, 200 150, 200 250, 50 250, 50 150))"
                }
            }
        },
        "solarPanelSpecs": {
            "voc": 40,
            "isc": 10,
            "vmp": 30,
            "imp": 15
        },
        "inverterSpecs": {
            "maxDCInputVoltage": 100.0,
            "numberOfMPPTs": 2,
            "startUpVoltage": 50,
            "maxDCInputCurrentPerMPPT": 10,
            "maxDCInputCurrentPerString": 5,
            "mpptOperatingVoltageMinRange": 200,
            "mpptOperatingVoltageMaxRange": 600,
            "maxShortCircuitCurrentPerMPPT": 15
        }
    }
    
    with open('example_input.json', 'w') as f:
        json.dump(example_data, f, indent=2)
    
    print("Created example_input.json with the specified structure")


def main():
    """Example usage of the JSON input parser"""
    print("JSON Input Parser - Example Usage")
    print("=" * 40)
    
    # Create example input file
    create_example_json_input()
    
    try:
        # Parse the example input
        panel_specs, inverter_specs, temperature_data = parse_json_input('example_input.json', 'California')
        
        print(f"\nSuccessfully parsed JSON input:")
        print(f"  Panels: {len(panel_specs)}")
        print(f"  Inverter: {inverter_specs.inverter_id}")
        print(f"  MPPTs: {inverter_specs.number_of_mppts}")
        print(f"  Temperature range: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

