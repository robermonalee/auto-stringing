"""
Visualize the stringing results for test-3.json
"""

import json
from visualization_helper import SolarStringingVisualizer

def main():
    print("="*80)
    print("Visualizing test-3.json Stringing Results")
    print("="*80)
    
    # Load test-3.json (for auto-design data)
    print("\n📁 Loading test-3.json...")
    with open('test-3.json', 'r') as f:
        test3_data = json.load(f)
    
    auto_design = test3_data.get('autoDesign', {}).get('auto_system_design', {})
    print(f"  ✓ Loaded auto-design data")
    
    # Load stringing results
    print("\n📊 Loading stringing results...")
    with open('test3_stringing_output.json', 'r') as f:
        results = json.load(f)
    print(f"  ✓ Loaded stringing output")
    
    # The visualization helper expects connections in technical format
    # But we have frontend format. Let's convert it back.
    print("\n🔄 Converting frontend format to technical format for visualization...")
    
    # Build technical format connections from frontend format
    technical_connections = {}
    
    for string_id, string_data in results.get('strings', {}).items():
        roof_id = string_data.get('roof_section', 'unknown')
        inverter_id = string_data.get('inverter', 'unknown')
        mppt_id = string_data.get('mppt', 'unknown')
        panel_ids = string_data.get('panel_ids', [])
        
        # Build nested structure: roof -> inverter -> mppt -> panels
        if roof_id not in technical_connections:
            technical_connections[roof_id] = {}
        if inverter_id not in technical_connections[roof_id]:
            technical_connections[roof_id][inverter_id] = {}
        if mppt_id not in technical_connections[roof_id][inverter_id]:
            technical_connections[roof_id][inverter_id][mppt_id] = []
        
        technical_connections[roof_id][inverter_id][mppt_id] = panel_ids
    
    # Create results in technical format
    technical_results = {
        'connections': technical_connections,
        'summary': results.get('summary', {})
    }
    
    print(f"  ✓ Converted to technical format")
    print(f"  ✓ Found {len(technical_connections)} roof planes")
    
    # Create visualizer
    print("\n🎨 Creating visualization...")
    visualizer = SolarStringingVisualizer(auto_design, technical_results)
    
    # Get panel centers for analysis
    panel_centers = visualizer.get_panel_center_coordinates()
    print(f"  ✓ Extracted {len(panel_centers)} panel positions")
    
    # Create the visualization
    output_path = "test3_stringing_visualization.png"
    fig, ax = visualizer.create_stringing_visualization(output_path, figsize=(16, 12))
    
    # Print wiring analysis
    print("\n📈 Performing wiring analysis...")
    visualizer.print_wiring_analysis(panel_centers)
    
    print("\n" + "="*80)
    print("✅ Visualization complete!")
    print(f"📁 Saved to: {output_path}")
    print("="*80)


if __name__ == "__main__":
    main()



