#!/usr/bin/env python3
"""
Test script to verify snake pattern organization is working correctly
Creates a simple grid of panels and shows the snake pattern ordering
"""

import json
from solar_stringing_optimizer import SolarStringingOptimizer, PanelSpecs, InverterSpecs, TemperatureData

def create_test_panel_grid():
    """Create a simple 3x3 grid of test panels"""
    panels = []
    
    # Create a 3x3 grid: 3 rows, 3 columns
    for row in range(3):
        for col in range(3):
            panel_id = f"panel_{row}_{col}"
            x_coord = 100 + col * 50  # 100, 150, 200
            y_coord = 200 - row * 50  # 200, 150, 100 (top to bottom)
            
            panel = PanelSpecs(
                panel_id=panel_id,
                voc_stc=40.0,
                isc_stc=10.0,
                vmpp_stc=30.0,
                impp_stc=15.0,
                roof_plane_id="1",
                center_coords=(x_coord, y_coord)
            )
            panels.append(panel)
    
    return panels

def test_snake_pattern_ordering():
    """Test the snake pattern ordering with a simple grid"""
    
    print("=" * 60)
    print("SNAKE PATTERN ORDERING VERIFICATION")
    print("=" * 60)
    
    # Create test panels in a 3x3 grid
    panels = create_test_panel_grid()
    
    print("Original panel positions (3x3 grid):")
    print("Row 0 (top):    panel_0_0  panel_0_1  panel_0_2")
    print("Row 1 (middle): panel_1_0  panel_1_1  panel_1_2") 
    print("Row 2 (bottom): panel_2_0  panel_2_1  panel_2_2")
    print()
    
    # Create optimizer to test snake pattern
    inverter_specs = InverterSpecs(
        inverter_id="test_inverter",
        max_dc_voltage=600.0,
        number_of_mppts=2,
        startup_voltage=100.0,
        max_dc_current_per_mppt=12.5,
        max_dc_current_per_string=12.5,
        mppt_min_voltage=90.0,
        mppt_max_voltage=560.0
    )
    
    temperature_data = TemperatureData(
        min_temp_c=-20.0,
        max_temp_c=40.0,
        avg_high_temp_c=25.0,
        avg_low_temp_c=5.0
    )
    
    # Test snake pattern sorting
    optimizer = SolarStringingOptimizer(
        panels, inverter_specs, temperature_data,
        use_snake_pattern=True
    )
    
    # Get the snake pattern sorted panels
    sorted_panels = optimizer._sort_panels_snake_pattern(panels)
    
    print("Snake pattern ordering (should be):")
    print("Row 0: Left → Right: panel_0_0, panel_0_1, panel_0_2")
    print("Row 1: Right → Left: panel_1_2, panel_1_1, panel_1_0")
    print("Row 2: Left → Right: panel_2_0, panel_2_1, panel_2_2")
    print()
    
    print("Actual snake pattern ordering:")
    for i, panel in enumerate(sorted_panels):
        row, col = panel.panel_id.split('_')[1], panel.panel_id.split('_')[2]
        print(f"  {i+1}. {panel.panel_id} (row {row}, col {col}) at ({panel.center_coords[0]}, {panel.center_coords[1]})")
    
    print()
    
    # Verify the pattern
    expected_order = [
        "panel_0_0", "panel_0_1", "panel_0_2",  # Row 0: Left → Right
        "panel_1_2", "panel_1_1", "panel_1_0",  # Row 1: Right → Left
        "panel_2_0", "panel_2_1", "panel_2_2"   # Row 2: Left → Right
    ]
    
    actual_order = [panel.panel_id for panel in sorted_panels]
    
    print("Verification:")
    if actual_order == expected_order:
        print("✅ Snake pattern is working correctly!")
        print("✅ Row 0: Left → Right")
        print("✅ Row 1: Right → Left (reversed)")
        print("✅ Row 2: Left → Right")
    else:
        print("❌ Snake pattern is NOT working correctly!")
        print(f"Expected: {expected_order}")
        print(f"Actual:   {actual_order}")
    
    return sorted_panels

if __name__ == "__main__":
    test_snake_pattern_ordering()
