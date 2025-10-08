"""
Data Parsers for Solar Stringing Optimizer

This module contains functions to parse and load data from various file formats
including auto-design.json, panel_specs.csv, inverter_specs.csv, and temperature data.
"""

import json
import csv
from typing import List, Dict, Tuple, Any
from solar_stringing_optimizer import PanelSpecs, InverterSpecs, TemperatureData


def parse_auto_design_json(file_path: str) -> Dict[str, Any]:
    """
    Parse the auto-design.json file to extract solar panel and roof plane information
    
    Args:
        file_path: Path to the auto-design.json file
        
    Returns:
        Dictionary containing parsed solar panel and roof plane data
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Extract the auto_system_design section
    auto_design = data.get('auto_system_design', {})
    
    return {
        'solar_panels': auto_design.get('solar_panels', []),
        'roof_planes': auto_design.get('roof_planes', {}),
        'array_stats': auto_design.get('array_stats', {}),
        'system_production_parameters': auto_design.get('system_production_parameters', {})
    }


def parse_panel_specs_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the panel_specs.csv file
    
    Args:
        file_path: Path to the panel_specs.csv file
        
    Returns:
        List of dictionaries containing panel specifications
    """
    panels = []
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert string values to appropriate types
            panel_spec = {
                'model': row.get('model', ''),
                'voc': float(row.get('voc (V)', 0)),
                'isc': float(row.get('isc (A)', 0)),
                'vmp': float(row.get('vmp (V)', 0)),
                'imp': float(row.get('imp (A)', 0)),
                'temp_coeff_voc': float(row.get('temp_coeff_voc (%/°C)', 0)),
                'temp_coeff_vmpp': float(row.get('temp_coeff_vmpp (%/°C)', 0)),
                'temp_coeff_isc': float(row.get('temp_coeff_isc (%/°C)', 0))
            }
            panels.append(panel_spec)
    
    return panels


def parse_inverter_specs_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the inverter_specs.csv file
    
    Args:
        file_path: Path to the inverter_specs.csv file
        
    Returns:
        List of dictionaries containing inverter specifications
    """
    inverters = []
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert string values to appropriate types
            inverter_spec = {
                'model': f"{row.get('manufacturer', '')} {row.get('model number', '')}".strip(),
                'max_dc_input_voltage': float(row.get('maxDCInputVoltage (V)', 0)),
                'number_of_mppts': int(row.get('numberOfMPPTs', 0)),
                'startup_voltage': float(row.get('startUpVoltage (V)', 0)),
                'max_dc_input_current_per_mppt': float(row.get('maxDCInputCurrentPerMPPT (A)', 0)),
                'max_dc_input_current_per_string': float(row.get('maxDCInputCurrentPerString (A)', 0)),
                'mppt_operating_voltage_min_range': float(row.get('mpptOperatingVoltageMinRange (V)', 0)),
                'mppt_operating_voltage_max_range': float(row.get('mpptOperatingVoltageMaxRange (V)', 0)),
                'max_short_circuit_current_per_mppt': float(row.get('maxShortCircuitCurrentPerMPPT (A)', 0))
            }
            inverters.append(inverter_spec)
    
    return inverters


def parse_temperature_data_csv(file_path: str, state_name: str) -> TemperatureData:
    """
    Parse the consolidated temperature data CSV to get temperature data for a specific state
    
    Args:
        file_path: Path to the consolidated_temperature_data.csv file
        state_name: Name of the state to get temperature data for
        
    Returns:
        TemperatureData object with min and max temperatures
    """
    # Read CSV file using built-in csv module
    with open(file_path, 'r', encoding='utf-8') as file:
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


def create_panel_specs_objects(auto_design_data: Dict[str, Any], 
                              panel_specs_data: List[Dict[str, Any]]) -> List[PanelSpecs]:
    """
    Create PanelSpecs objects by combining auto-design.json data with panel specifications
    
    Args:
        auto_design_data: Parsed data from auto-design.json
        panel_specs_data: Parsed data from panel_specs.csv
        
    Returns:
        List of PanelSpecs objects
    """
    panels = []
    solar_panels = auto_design_data['solar_panels']
    
    # For now, assume all panels use the first panel specification
    # In a real implementation, you'd match panel types based on some identifier
    representative_spec = panel_specs_data[0] if panel_specs_data else {}
    
    for panel_data in solar_panels:
        # Extract pixel coordinates (c0 is the center)
        pix_coords = panel_data.get('pix_coords', {})
        c0 = pix_coords.get('c0', [0, 0])
        center_coords = (float(c0[0]), float(c0[1]))
        
        panel_spec = PanelSpecs(
            panel_id=panel_data.get('panel_id', ''),
            voc_stc=representative_spec.get('voc', 0),
            isc_stc=representative_spec.get('isc', 0),
            vmpp_stc=representative_spec.get('vmp', 0),
            impp_stc=representative_spec.get('imp', 0),
            roof_plane_id=panel_data.get('roof_plane_id', ''),
            center_coords=center_coords
        )
        panels.append(panel_spec)
    
    return panels


def create_inverter_specs_object(inverter_specs_data: List[Dict[str, Any]]) -> InverterSpecs:
    """
    Create InverterSpecs object from parsed inverter data
    
    Args:
        inverter_specs_data: Parsed data from inverter_specs.csv
        
    Returns:
        InverterSpecs object
    """
    # For now, use the first inverter specification
    # In a real implementation, you'd select based on system requirements
    inverter_data = inverter_specs_data[0] if inverter_specs_data else {}
    
    return InverterSpecs(
        inverter_id=inverter_data.get('model', 'default_inverter'),
        max_dc_voltage=inverter_data.get('max_dc_input_voltage', 0),
        mppt_min_voltage=inverter_data.get('mppt_operating_voltage_min_range', 0),
        mppt_max_voltage=inverter_data.get('mppt_operating_voltage_max_range', 0),
        max_dc_current_per_mppt=inverter_data.get('max_dc_input_current_per_mppt', 0),
        max_dc_current_per_string=inverter_data.get('max_dc_input_current_per_string', 0),
        number_of_mppts=inverter_data.get('number_of_mppts', 0),
        startup_voltage=inverter_data.get('startup_voltage', 0)
    )


def load_all_data(auto_design_path: str, panel_specs_path: str, 
                 inverter_specs_path: str, temperature_data_path: str, 
                 state_name: str) -> Tuple[List[PanelSpecs], InverterSpecs, TemperatureData]:
    """
    Load all required data for the solar stringing optimizer
    
    Args:
        auto_design_path: Path to auto-design.json
        panel_specs_path: Path to panel_specs.csv
        inverter_specs_path: Path to inverter_specs.csv
        temperature_data_path: Path to consolidated_temperature_data.csv
        state_name: Name of the state for temperature data
        
    Returns:
        Tuple of (panel_specs, inverter_specs, temperature_data)
    """
    print("Loading data files...")
    
    # Parse auto-design.json
    print(f"  Loading auto-design data from {auto_design_path}")
    auto_design_data = parse_auto_design_json(auto_design_path)
    
    # Parse panel specs
    print(f"  Loading panel specs from {panel_specs_path}")
    panel_specs_data = parse_panel_specs_csv(panel_specs_path)
    
    # Parse inverter specs
    print(f"  Loading inverter specs from {inverter_specs_path}")
    inverter_specs_data = parse_inverter_specs_csv(inverter_specs_path)
    
    # Parse temperature data
    print(f"  Loading temperature data from {temperature_data_path}")
    temperature_data = parse_temperature_data_csv(temperature_data_path, state_name)
    
    # Create objects
    print("  Creating data objects...")
    panel_specs = create_panel_specs_objects(auto_design_data, panel_specs_data)
    inverter_specs = create_inverter_specs_object(inverter_specs_data)
    
    print(f"  Loaded {len(panel_specs)} panels, {inverter_specs.number_of_mppts} MPPTs")
    print(f"  Temperature range: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
    
    return panel_specs, inverter_specs, temperature_data


def main():
    """Example usage of the data parsers"""
    print("Data Parsers - Example Usage")
    print("=" * 30)
    
    # Example file paths
    auto_design_path = "auto-design.json"
    panel_specs_path = "panel_specs.csv"
    inverter_specs_path = "inverter_specs.csv"
    temperature_data_path = "consolidated_temperature_data.csv"
    state_name = "California"  # Example state
    
    try:
        panel_specs, inverter_specs, temperature_data = load_all_data(
            auto_design_path, panel_specs_path, inverter_specs_path, 
            temperature_data_path, state_name
        )
        
        print(f"\nSuccessfully loaded data:")
        print(f"  Panels: {len(panel_specs)}")
        print(f"  Inverter: {inverter_specs.inverter_id}")
        print(f"  MPPTs: {inverter_specs.number_of_mppts}")
        print(f"  Temperature range: {temperature_data.min_temp_c}°C to {temperature_data.max_temp_c}°C")
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
