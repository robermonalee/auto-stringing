#!/usr/bin/env python3
"""
Test script for enhanced visualization with wiring analysis

This script demonstrates the improved visualization features:
1. Individual panels drawn using c1-c4 coordinates
2. Darker blue panels
3. Dark squares for MPPTs
4. Circles for inverters
5. Smart inverter placement
6. Wiring efficiency analysis
"""

import json
import os
from visualization_helper import SolarStringingVisualizer, create_visualization_from_files


def test_enhanced_visualization():
    """Test the enhanced visualization with wiring analysis"""
    print("=" * 70)
    print("ENHANCED SOLAR STRINGING VISUALIZATION TEST")
    print("=" * 70)
    
    # Load data
    with open('second-test.json', 'r') as f:
        auto_design_data = json.load(f)
    
    with open('results_second_test.json', 'r') as f:
        results_data = json.load(f)
    
    # Extract the relevant sections
    auto_design = auto_design_data.get('auto_system_design', auto_design_data)
    
    # Create visualizer
    visualizer = SolarStringingVisualizer(auto_design, results_data)
    
    # Get panel centers for analysis
    panel_centers = visualizer.get_panel_center_coordinates()
    
    print("Creating enhanced visualization...")
    print("Features:")
    print("  ✓ Individual panels using c1-c4 coordinates")
    print("  ✓ Darker blue panel shading")
    print("  ✓ Dark squares for MPPTs")
    print("  ✓ Circles for inverters")
    print("  ✓ Smart inverter placement")
    print("  ✓ Inverter-MPPT connection lines")
    
    # Create the enhanced visualization
    fig, ax = visualizer.create_stringing_visualization("enhanced_visualization_detailed.png")
    
    print("\n✅ Enhanced visualization created: enhanced_visualization_detailed.png")
    
    # Perform wiring analysis
    print("\nPerforming wiring efficiency analysis...")
    visualizer.print_wiring_analysis(panel_centers)
    
    # Create a comparison visualization showing the problem
    print("\nCreating comparison visualization...")
    create_comparison_visualization(visualizer, panel_centers)
    
    return visualizer, panel_centers


def create_comparison_visualization(visualizer, panel_centers):
    """Create a comparison showing before/after inverter placement"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Polygon, Rectangle, Circle
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 10))
    
    # Left plot: Original placement (centered)
    ax1.set_xlim(0, 1024)
    ax1.set_ylim(0, 1024)
    ax1.set_aspect('equal')
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Original Inverter Placement\n(Centered on Panels)', fontsize=14, fontweight='bold')
    
    # Right plot: Optimized placement
    ax2.set_xlim(0, 1024)
    ax2.set_ylim(0, 1024)
    ax2.set_aspect('equal')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Optimized Inverter Placement\n(Closest to Panels)', fontsize=14, fontweight='bold')
    
    # Draw panels on both plots
    for panel in visualizer.solar_panels:
        panel_id = panel.get('panel_id', '')
        if panel_id in panel_centers:
            pix_coords = panel.get('pix_coords', {})
            c1 = pix_coords.get('c1', [0, 0])
            c2 = pix_coords.get('c2', [0, 0])
            c3 = pix_coords.get('c3', [0, 0])
            c4 = pix_coords.get('c4', [0, 0])
            
            panel_corners = [
                (float(c1[0]), float(c1[1])),
                (float(c2[0]), float(c2[1])),
                (float(c3[0]), float(c3[1])),
                (float(c4[0]), float(c4[1]))
            ]
            
            panel_polygon = Polygon(panel_corners, closed=True,
                                  facecolor='#2E86AB', alpha=0.8,
                                  edgecolor='black', linewidth=0.5)
            ax1.add_patch(panel_polygon)
            ax2.add_patch(panel_polygon)
    
    # Draw original placement (centered)
    for roof_plane, inverters in visualizer.connections.items():
        for inverter_id, mppts in inverters.items():
            # Calculate center of all panels
            all_panel_coords = []
            for mppt_id, panel_ids in mppts.items():
                for panel_id in panel_ids:
                    if panel_id in panel_centers:
                        all_panel_coords.append(panel_centers[panel_id])
            
            if all_panel_coords:
                # Original: center of all panels
                orig_x = sum(coord[0] for coord in all_panel_coords) / len(all_panel_coords)
                orig_y = sum(coord[1] for coord in all_panel_coords) / len(all_panel_coords)
                
                # Draw original inverter
                orig_circle = Circle((orig_x, orig_y), 25, 
                                   facecolor='red', alpha=0.7,
                                   edgecolor='darkred', linewidth=2)
                ax1.add_patch(orig_circle)
                ax1.text(orig_x, orig_y, inverter_id.split('_')[-1], 
                        ha='center', va='center', fontsize=10, 
                        fontweight='bold', color='white')
                
                # Draw connections
                for mppt_id, panel_ids in mppts.items():
                    mppt_coords = [panel_centers[pid] for pid in panel_ids if pid in panel_centers]
                    if mppt_coords:
                        mppt_x = sum(coord[0] for coord in mppt_coords) / len(mppt_coords)
                        mppt_y = sum(coord[1] for coord in mppt_coords) / len(mppt_coords)
                        
                        ax1.plot([orig_x, mppt_x], [orig_y, mppt_y], 
                               color='red', linewidth=2, alpha=0.6, linestyle='--')
    
    # Draw optimized placement
    inverter_positions = visualizer._calculate_optimal_inverter_positions(panel_centers)
    
    for roof_plane, inverters in visualizer.connections.items():
        for inverter_id, mppts in inverters.items():
            if inverter_id in inverter_positions:
                opt_x, opt_y = inverter_positions[inverter_id]
                
                # Draw optimized inverter
                opt_circle = Circle((opt_x, opt_y), 25, 
                                  facecolor='green', alpha=0.7,
                                  edgecolor='darkgreen', linewidth=2)
                ax2.add_patch(opt_circle)
                ax2.text(opt_x, opt_y, inverter_id.split('_')[-1], 
                        ha='center', va='center', fontsize=10, 
                        fontweight='bold', color='white')
                
                # Draw connections
                for mppt_id, panel_ids in mppts.items():
                    mppt_coords = [panel_centers[pid] for pid in panel_ids if pid in panel_centers]
                    if mppt_coords:
                        mppt_x = sum(coord[0] for coord in mppt_coords) / len(mppt_coords)
                        mppt_y = sum(coord[1] for coord in mppt_coords) / len(mppt_coords)
                        
                        ax2.plot([opt_x, mppt_x], [opt_y, mppt_y], 
                               color='green', linewidth=2, alpha=0.6, linestyle='--')
    
    plt.tight_layout()
    plt.savefig('inverter_placement_comparison.png', dpi=300, bbox_inches='tight')
    print("✅ Comparison visualization created: inverter_placement_comparison.png")


def main():
    """Main test function"""
    print("Testing Enhanced Solar Stringing Visualization")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ['second-test.json', 'results_second_test.json']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please run the optimization first to generate results_second_test.json")
        return
    
    try:
        # Test enhanced visualization
        visualizer, panel_centers = test_enhanced_visualization()
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print("✅ Enhanced visualization created successfully!")
        print("✅ Wiring efficiency analysis completed!")
        print("✅ Comparison visualization generated!")
        
        print("\nGenerated files:")
        print("  - enhanced_visualization_detailed.png (full enhanced visualization)")
        print("  - inverter_placement_comparison.png (before/after comparison)")
        
        print("\nKey improvements:")
        print("  - Individual panels drawn using actual corner coordinates")
        print("  - Darker blue shading for better visibility")
        print("  - Smart inverter placement based on panel proximity")
        print("  - Wiring efficiency analysis and optimization suggestions")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
