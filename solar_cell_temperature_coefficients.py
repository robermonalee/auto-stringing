#!/usr/bin/env python3
"""
Solar Cell Temperature Coefficient Functions
Based on the temperature dependence graph showing linear relationships
for Isc, Voc, and Pmax as functions of cell temperature.
Source: https://jinkosolarcdn.shwebspace.com/uploads/JKM420-440N-54HL4R-B-F1.3-EN.pdf
"""

def calculate_isc_normalized(cell_temperature_celsius):
    """
    Calculates the normalized Short-Circuit Current (Isc) in percentage.
    
    From the graph analysis:
    - Isc shows a slight positive correlation with temperature
    - At -50°C: ~99% normalized
    - At 25°C: 100% normalized (STC reference)
    - At 75°C: ~101% normalized
    
    Linear formula: Isc(T) = 0.02 * T + 99.5
    Where T is cell temperature in Celsius
    
    Args:
        cell_temperature_celsius (float): Cell temperature in degrees Celsius
        
    Returns:
        float: Normalized Isc as percentage (100% = STC value)
    """
    return 0.02 * cell_temperature_celsius + 99.5


def calculate_voc_normalized(cell_temperature_celsius):
    """
    Calculates the normalized Open-Circuit Voltage (Voc) in percentage.
    
    Updated data points:
    - At -45°C: 120% normalized
    - At 25°C: 100% normalized (STC reference)
    - At 75°C: 85% normalized
    
    Linear formula: Voc(T) = -0.286 * T + 107.143
    Where T is cell temperature in Celsius
    
    Args:
        cell_temperature_celsius (float): Cell temperature in degrees Celsius
        
    Returns:
        float: Normalized Voc as percentage (100% = STC value)
    """
    return -0.286 * cell_temperature_celsius + 107.143


def calculate_pmax_normalized(cell_temperature_celsius):
    """
    Calculates the normalized Maximum Power (Pmax) in percentage.
    
    Updated data points:
    - At -50°C: 125% normalized
    - At 25°C: 100% normalized (STC reference)
    - At 75°C: 82% normalized
    
    Linear formula: Pmax(T) = -0.333 * T + 108.333
    Where T is cell temperature in Celsius
    
    Args:
        cell_temperature_celsius (float): Cell temperature in degrees Celsius
        
    Returns:
        float: Normalized Pmax as percentage (100% = STC value)
    """
    return -0.333 * cell_temperature_celsius + 108.333


def calculate_all_parameters(cell_temperature_celsius):
    """
    Calculate all three normalized parameters at a given temperature.
    
    Args:
        cell_temperature_celsius (float): Cell temperature in degrees Celsius
        
    Returns:
        dict: Dictionary containing normalized Isc, Voc, and Pmax values
    """
    return {
        'isc_normalized': calculate_isc_normalized(cell_temperature_celsius),
        'voc_normalized': calculate_voc_normalized(cell_temperature_celsius),
        'pmax_normalized': calculate_pmax_normalized(cell_temperature_celsius)
    }


def temperature_coefficient_analysis():
    """
    Demonstrate the temperature coefficient functions with various temperatures.
    """
    print("Solar Cell Temperature Coefficient Analysis")
    print("=" * 50)
    
    # Test temperatures
    test_temperatures = [-50, -25, 0, 25, 50, 75, 100]
    
    print(f"{'Temp (°C)':<10} {'Isc (%)':<10} {'Voc (%)':<10} {'Pmax (%)':<10}")
    print("-" * 50)
    
    for temp in test_temperatures:
        isc = calculate_isc_normalized(temp)
        voc = calculate_voc_normalized(temp)
        pmax = calculate_pmax_normalized(temp)
        
        print(f"{temp:<10} {isc:<10.2f} {voc:<10.2f} {pmax:<10.2f}")
    
    print("\nKey Observations:")
    print("- Isc increases slightly with temperature (positive coefficient)")
    print("- Voc decreases significantly with temperature (negative coefficient)")
    print("- Pmax decreases significantly with temperature (negative coefficient)")
    print("- All parameters are normalized to 100% at 25°C (STC)")


def calculate_actual_values(stc_isc, stc_voc, stc_pmax, cell_temperature_celsius):
    """
    Calculate actual Isc, Voc, and Pmax values at a given temperature
    based on STC (Standard Test Conditions) values.
    
    Args:
        stc_isc (float): Short-circuit current at STC (25°C)
        stc_voc (float): Open-circuit voltage at STC (25°C)
        stc_pmax (float): Maximum power at STC (25°C)
        cell_temperature_celsius (float): Cell temperature in degrees Celsius
        
    Returns:
        dict: Dictionary containing actual Isc, Voc, and Pmax values
    """
    # Get normalized values
    isc_norm = calculate_isc_normalized(cell_temperature_celsius)
    voc_norm = calculate_voc_normalized(cell_temperature_celsius)
    pmax_norm = calculate_pmax_normalized(cell_temperature_celsius)
    
    # Calculate actual values
    actual_isc = stc_isc * (isc_norm / 100.0)
    actual_voc = stc_voc * (voc_norm / 100.0)
    actual_pmax = stc_pmax * (pmax_norm / 100.0)
    
    return {
        'isc_actual': actual_isc,
        'voc_actual': actual_voc,
        'pmax_actual': actual_pmax,
        'isc_normalized': isc_norm,
        'voc_normalized': voc_norm,
        'pmax_normalized': pmax_norm
    }


if __name__ == "__main__":
    # Run the analysis
    temperature_coefficient_analysis()
    
    print("\n" + "=" * 50)
    print("Example: Calculating actual values from STC values")
    print("=" * 50)
    
    # Example STC values (typical for a solar panel)
    stc_isc = 8.5  # Amperes
    stc_voc = 37.2  # Volts
    stc_pmax = 315  # Watts
    
    print(f"STC Values: Isc={stc_isc}A, Voc={stc_voc}V, Pmax={stc_pmax}W")
    print()
    
    # Test at different temperatures
    test_temps = [0, 25, 50, 75]
    
    for temp in test_temps:
        results = calculate_actual_values(stc_isc, stc_voc, stc_pmax, temp)
        
        print(f"At {temp}°C:")
        print(f"  Isc: {results['isc_actual']:.2f}A ({results['isc_normalized']:.1f}%)")
        print(f"  Voc: {results['voc_actual']:.2f}V ({results['voc_normalized']:.1f}%)")
        print(f"  Pmax: {results['pmax_actual']:.1f}W ({results['pmax_normalized']:.1f}%)")
        print()
