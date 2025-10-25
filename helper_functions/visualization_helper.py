"""
Solar Panel Stringing Visualization Helper

This module provides functions to visualize solar panel layouts, stringing connections,
and MPPT/inverter assignments on roof planes.

NOTE: This module requires matplotlib and is intended for local visualization only.
For AWS deployment, this module should be excluded to avoid heavy dependencies.
"""

import json
import re
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

# Optional imports for visualization - only import if available
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Polygon, Rectangle
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("Warning: matplotlib not available. Visualization functions will not work.")
    print("Install matplotlib with: pip install matplotlib")


class SolarStringingVisualizer:
    """
    Visualizes solar panel stringing configurations on roof planes
    """
    
    def __init__(self, auto_design_data: Dict[str, Any], stringing_results: Dict[str, Any]):
        """
        Initialize the visualizer with auto-design data and stringing results
        
        Args:
            auto_design_data: Parsed auto-design.json data
            stringing_results: Results from the stringing optimizer
        """
        self.auto_design = auto_design_data
        self.results = stringing_results
        self.roof_planes = auto_design_data.get('roof_planes', {})
        self.solar_panels = auto_design_data.get('solar_panels', [])
        self.stringing_results = stringing_results
        self._parse_stringing_data()
        
        # Color palette for different roof planes and MPPTs
        self.roof_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                           '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        self.mppt_colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', 
                           '#00FFFF', '#FFA500', '#800080', '#008000', '#FFC0CB']

    def _parse_stringing_data(self):
        """Parse the new stringing output format."""
        self.strings = self.stringing_results.get('strings', {})
        self.inverters = self.stringing_results.get('inverter_specs', {})
        self.mppts = self.stringing_results.get('mppt_specs', {})
        self.summary = self.stringing_results.get('summary', {})

        # Create a mapping from panel_id to string_id
        self.panel_to_string_map = {}
        for string_id, string_data in self.strings.items():
            for panel_id in string_data.get('panel_ids', []):
                self.panel_to_string_map[panel_id] = string_id

        
    def parse_polygon_coordinates(self, polygon_wkt: str) -> List[Tuple[float, float]]:
        """
        Parse WKT polygon string to extract coordinate pairs
        
        Args:
            polygon_wkt: WKT polygon string like "POLYGON ((x1 y1, x2 y2, ...))"
            
        Returns:
            List of (x, y) coordinate tuples
        """
        # Extract coordinates from WKT format
        coords_match = re.search(r'POLYGON\s*\(\s*\((.*?)\)\s*\)', polygon_wkt)
        if not coords_match:
            return []
        
        coords_str = coords_match.group(1)
        coord_pairs = coords_str.split(',')
        
        coordinates = []
        for pair in coord_pairs:
            x, y = pair.strip().split()
            coordinates.append((float(x), float(y)))
        
        return coordinates
    
    def get_panel_center_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        Extract center coordinates for all panels
        
        Returns:
            Dictionary mapping panel_id -> (x, y) center coordinates
        """
        panel_centers = {}
        
        for panel in self.solar_panels:
            panel_id = panel.get('panel_id', '')
            pix_coords = panel.get('pix_coords', {})
            c0 = pix_coords.get('c0', [0, 0])
            
            # c0 is the center coordinate
            panel_centers[panel_id] = (float(c0[0]), float(c0[1]))
        
        return panel_centers
    
    def create_stringing_visualization(self, output_path: str = "stringing_visualization.png", 
                                     figsize: Tuple[int, int] = (16, 12)):
        """
        Create a comprehensive visualization of the solar panel stringing layout
        
        Args:
            output_path: Path to save the visualization image
            figsize: Figure size (width, height) in inches
        """
        if not VISUALIZATION_AVAILABLE:
            raise ImportError("matplotlib is required for visualization. Install with: pip install matplotlib")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Set up the coordinate system (1024x1024 grid)
        ax.set_xlim(0, 1024)
        ax.set_ylim(0, 1024)
        ax.set_aspect('equal')
        ax.invert_yaxis()  # Invert Y-axis so (0,0) is top-left
        
        # Add grid
        ax.grid(True, alpha=0.3, linewidth=0.5)
        ax.set_xticks(range(0, 1025, 64))  # Grid every 64 pixels
        ax.set_yticks(range(0, 1025, 64))
        ax.set_xlabel('X Coordinate (pixels)')
        ax.set_ylabel('Y Coordinate (pixels)')
        ax.set_title('Solar Panel Stringing Layout\n(Panels, Strings, MPPTs, and Inverters)', 
                    fontsize=16, fontweight='bold')
        
        # Get panel center coordinates
        panel_centers = self.get_panel_center_coordinates()
        
        # Draw roof planes
        self._draw_roof_planes(ax)
        
        # Draw panels and stringing connections
        self._draw_panels_and_strings(ax, panel_centers)
        
        # Draw MPPT and inverter overlays
        self._draw_mppt_inverter_overlays(ax, panel_centers)
        
        # Add legend
        self._add_legend(ax)
        
        # Save the visualization
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_path}")
        
        return fig, ax
    
    def _draw_roof_planes(self, ax):
        """Draw roof plane boundaries"""
        for i, (roof_id, roof_data) in enumerate(self.roof_planes.items()):
            polygon_wkt = roof_data.get('polygon', '')
            if not polygon_wkt:
                continue
                
            coordinates = self.parse_polygon_coordinates(polygon_wkt)
            if not coordinates:
                continue
            
            # Create polygon patch
            color = self.roof_colors[i % len(self.roof_colors)]
            polygon = Polygon(coordinates, closed=True, 
                            facecolor=color, alpha=0.2, 
                            edgecolor=color, linewidth=2)
            ax.add_patch(polygon)
            
            # Add roof plane label
            if coordinates:
                center_x = sum(coord[0] for coord in coordinates) / len(coordinates)
                center_y = sum(coord[1] for coord in coordinates) / len(coordinates)
                ax.text(center_x, center_y, f'Roof {roof_id}', 
                       ha='center', va='center', fontweight='bold', fontsize=10,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    def _draw_panels_and_strings(self, ax, panel_centers: Dict[str, Tuple[float, float]]):
        """Draw panels and stringing connections"""
        # Group panels by roof plane
        roof_panels = defaultdict(list)
        for panel in self.solar_panels:
            roof_id = panel.get('roof_plane_id', '')
            panel_id = panel.get('panel_id', '')
            if panel_id in panel_centers:
                roof_panels[roof_id].append(panel_id)
        
        # Draw panels and strings for each roof plane
        for roof_id, panel_ids in roof_panels.items():
            roof_color = self.roof_colors[int(roof_id) % len(self.roof_colors)]
            
            # Draw individual panels using actual corner coordinates
            for panel_id in panel_ids:
                panel_data = next((p for p in self.solar_panels if p.get('panel_id') == panel_id), None)
                if panel_data:
                    pix_coords = panel_data.get('pix_coords', {})
                    c1 = pix_coords.get('c1', [0, 0])
                    c2 = pix_coords.get('c2', [0, 0])
                    c3 = pix_coords.get('c3', [0, 0])
                    c4 = pix_coords.get('c4', [0, 0])
                    
                    # Create panel polygon from corner coordinates
                    panel_corners = [
                        (float(c1[0]), float(c1[1])),
                        (float(c2[0]), float(c2[1])),
                        (float(c3[0]), float(c3[1])),
                        (float(c4[0]), float(c4[1]))
                    ]
                    
                    # Use darker blue for panels
                    panel_color = '#2E86AB'  # Darker blue
                    panel_polygon = Polygon(panel_corners, closed=True,
                                          facecolor=panel_color, alpha=0.8,
                                          edgecolor='black', linewidth=0.5)
                    ax.add_patch(panel_polygon)
                    
                    # Add panel ID (abbreviated) at center
                    x, y = panel_centers[panel_id]
                    short_id = panel_id[-4:]  # Last 4 characters
                    ax.text(x, y, short_id, ha='center', va='center', 
                           fontsize=5, fontweight='bold', color='white')
        
        # Draw stringing connections
        self._draw_string_connections(ax, panel_centers)
    
    def _draw_string_connections(self, ax, panel_centers: Dict[str, Tuple[float, float]]):
        """Draw lines connecting panels in the same string"""
        string_count = 0
        
        for string_id, string_data in self.strings.items():
            panel_ids = string_data.get('panel_ids', [])
            if len(panel_ids) > 1:  # Only draw connections for strings with multiple panels
                # Get coordinates for panels in this string
                string_coords = []
                for panel_id in panel_ids:
                    if panel_id in panel_centers:
                        string_coords.append(panel_centers[panel_id])
                
                if len(string_coords) > 1:
                    # Draw connection lines
                    x_coords = [coord[0] for coord in string_coords]
                    y_coords = [coord[1] for coord in string_coords]
                    
                    # Use different colors for different strings
                    color = self.mppt_colors[string_count % len(self.mppt_colors)]
                    
                    # Draw lines connecting panels in sequence
                    for i in range(len(string_coords) - 1):
                        ax.plot([x_coords[i], x_coords[i+1]], 
                               [y_coords[i], y_coords[i+1]], 
                               color=color, linewidth=3, alpha=0.8)
                        
                        # Add directional arrow at the start of each string
                        if i == 0:  # Only for the first connection in each string
                            self._draw_directional_arrow(ax, string_coords[0], string_coords[1], color)
                    
                    # Add string label
                    mid_x = sum(x_coords) / len(x_coords)
                    mid_y = sum(y_coords) / len(y_coords)
                    ax.text(mid_x, mid_y, string_id, 
                           ha='center', va='center', fontsize=8, 
                           fontweight='bold', color='white',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.8))
                    
                    string_count += 1
    
    def _draw_directional_arrow(self, ax, start_coord: Tuple[float, float], end_coord: Tuple[float, float], color: str):
        """Draw a small directional arrow at the start of a string"""
        x1, y1 = start_coord
        x2, y2 = end_coord
        
        # Calculate arrow direction
        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        if length > 0:
            # Normalize direction
            dx_norm = dx / length
            dy_norm = dy / length
            
            # Arrow size (small)
            arrow_size = 8
            
            # Calculate arrow head points
            arrow_x = x1 + dx_norm * arrow_size
            arrow_y = y1 + dy_norm * arrow_size
            
            # Draw small arrow
            ax.annotate('', xy=(arrow_x, arrow_y), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.9))
    
    def _calculate_optimal_inverter_positions(self, panel_centers: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
        """
        Calculate optimal inverter positions based on panel proximity
        """
        inverter_positions = {}
        
        for inverter_id, inverter_data in self.inverters.items():
            # Collect all panels connected to this inverter
            all_panel_coords = []
            for mppt_id in inverter_data.get('mppt_ids', []):
                for string_id, string_data in self.strings.items():
                    if string_data.get('mppt') == mppt_id:
                        for panel_id in string_data.get('panel_ids', []):
                            if panel_id in panel_centers:
                                all_panel_coords.append(panel_centers[panel_id])
            
            if all_panel_coords:
                # Calculate centroid of all connected panels
                inv_x = sum(coord[0] for coord in all_panel_coords) / len(all_panel_coords)
                inv_y = sum(coord[1] for coord in all_panel_coords) / len(all_panel_coords)
                
                # Find the closest panel to the centroid for more precise placement
                min_distance = float('inf')
                optimal_pos = (inv_x, inv_y)
                
                for coord in all_panel_coords:
                    distance = ((coord[0] - inv_x) ** 2 + (coord[1] - inv_y) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        optimal_pos = coord
                
                # Offset inverter position slightly to avoid overlap with panels
                offset_x = 40 if inv_x < 512 else -40  # Offset based on which side of image
                offset_y = 40 if inv_y < 512 else -40
                
                inverter_positions[inverter_id] = (
                    optimal_pos[0] + offset_x,
                    optimal_pos[1] + offset_y
                )
        
        return inverter_positions
    
    def _calculate_clean_inverter_positions(self) -> Dict[str, Tuple[float, float]]:
        """
        Calculate clean inverter positions - three inverters side by side outside the house
        """
        inverter_positions = {}
        
        # Get all unique inverter IDs
        all_inverters = list(self.inverters.keys())
        
        # Position inverters side by side to the right of the house
        # Assuming house is roughly in the center-left area (0-800 pixels)
        # Position inverters at x=900, 950, 1000 (spaced 50 pixels apart)
        base_x = 900
        base_y = 400  # Center vertically
        
        for i, inverter_id in enumerate(all_inverters):
            inv_x = base_x + (i * 50)  # Space inverters 50 pixels apart
            inv_y = base_y
            inverter_positions[inverter_id] = (inv_x, inv_y)
        
        return inverter_positions
    
    def analyze_wiring_efficiency(self, panel_centers: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """
        Analyze wiring efficiency and identify optimization opportunities
        """
        analysis = {
            'inverter_efficiency': {},
            'total_wiring_distance': 0,
            'optimization_suggestions': []
        }
        
        inverter_positions = self._calculate_optimal_inverter_positions(panel_centers)
        
        for inverter_id, inverter_data in self.inverters.items():
            if inverter_id in inverter_positions:
                inv_x, inv_y = inverter_positions[inverter_id]
                
                # Calculate total distance from inverter to all its panels
                total_distance = 0
                panel_count = 0
                max_distance = 0
                min_distance = float('inf')
                
                for mppt_id in inverter_data.get('mppt_ids', []):
                    for string_id, string_data in self.strings.items():
                        if string_data.get('mppt') == mppt_id:
                            for panel_id in string_data.get('panel_ids', []):
                                if panel_id in panel_centers:
                                    panel_x, panel_y = panel_centers[panel_id]
                                    distance = ((panel_x - inv_x) ** 2 + (panel_y - inv_y) ** 2) ** 0.5
                                    total_distance += distance
                                    panel_count += 1
                                    max_distance = max(max_distance, distance)
                                    min_distance = min(min_distance, distance)
                
                avg_distance = total_distance / panel_count if panel_count > 0 else 0
                
                analysis['inverter_efficiency'][inverter_id] = {
                    'panel_count': panel_count,
                    'total_distance': total_distance,
                    'avg_distance': avg_distance,
                    'max_distance': max_distance,
                    'min_distance': min_distance,
                    'efficiency_score': 100 - (avg_distance / 100)  # Simple efficiency metric
                }
                
                analysis['total_wiring_distance'] += total_distance
                
                # Identify inefficient configurations
                if avg_distance > 150:  # Threshold for "too far"
                    analysis['optimization_suggestions'].append({
                        'type': 'inverter_placement',
                        'inverter': inverter_id,
                        'issue': f'Average distance {avg_distance:.1f}px is high',
                        'suggestion': 'Consider relocating inverter closer to panels'
                    })
                
                if max_distance > 300:  # Very far panels
                    analysis['optimization_suggestions'].append({
                        'type': 'string_reorganization',
                        'inverter': inverter_id,
                        'issue': f'Some panels are {max_distance:.1f}px away',
                        'suggestion': 'Consider splitting into multiple inverters or reorganizing strings'
                    })
        
        return analysis
    
    def print_wiring_analysis(self, panel_centers: Dict[str, Tuple[float, float]]):
        """
        Print detailed wiring efficiency analysis
        """
        analysis = self.analyze_wiring_efficiency(panel_centers)
        
        print("\n" + "=" * 60)
        print("WIRING EFFICIENCY ANALYSIS")
        print("=" * 60)
        
        print(f"Total Wiring Distance: {analysis['total_wiring_distance']:.1f} pixels")
        print()
        
        print("Inverter Efficiency Scores:")
        print("-" * 40)
        for inverter_id, data in analysis['inverter_efficiency'].items():
            print(f"{inverter_id}:")
            print(f"  Roof Plane: {data['roof_plane']}")
            print(f"  Panels: {data['panel_count']}")
            print(f"  Avg Distance: {data['avg_distance']:.1f}px")
            print(f"  Max Distance: {data['max_distance']:.1f}px")
            print(f"  Efficiency Score: {data['efficiency_score']:.1f}%")
            print()
        
        if analysis['optimization_suggestions']:
            print("Optimization Suggestions:")
            print("-" * 30)
            for i, suggestion in enumerate(analysis['optimization_suggestions'], 1):
                print(f"{i}. {suggestion['type'].upper()}: {suggestion['inverter']}")
                print(f"   Issue: {suggestion['issue']}")
                print(f"   Suggestion: {suggestion['suggestion']}")
                print()
        else:
            print("✅ No major wiring optimization issues detected!")
    
    def _draw_mppt_inverter_overlays(self, ax, panel_centers: Dict[str, Tuple[float, float]]):
        """Draw MPPT and inverter overlays with clean positioning"""
        # Position inverters side by side outside the house (to the right)
        inverter_positions = self._calculate_clean_inverter_positions()
        
        mppt_count = 0
        
        for inverter_id, inverter_data in self.inverters.items():
            # Get clean inverter position
            if inverter_id in inverter_positions:
                inv_x, inv_y = inverter_positions[inverter_id]
                
                # Draw inverter as a bright blue vertical rectangle
                inverter_rect = Rectangle((inv_x-15, inv_y-30), 30, 60,
                                        facecolor='#00BFFF', alpha=0.9,  # Bright blue
                                        edgecolor='#0066CC', linewidth=2)
                ax.add_patch(inverter_rect)
                
                # Add inverter label
                ax.text(inv_x, inv_y, inverter_id, 
                       ha='center', va='center', fontsize=10, 
                       fontweight='bold', color='white')
                
                # Draw MPPTs without connection lines
                for mppt_id in inverter_data.get('mppt_ids', []):
                    panel_ids = []
                    for string_id, string_data in self.strings.items():
                        if string_data.get('mppt') == mppt_id:
                            panel_ids.extend(string_data.get('panel_ids', []))

                    if panel_ids:
                        # Position MPPT at center of its panels
                        mppt_coords = [panel_centers[pid] for pid in panel_ids if pid in panel_centers]
                        if mppt_coords:
                            mppt_x = sum(coord[0] for coord in mppt_coords) / len(mppt_coords)
                            mppt_y = sum(coord[1] for coord in mppt_coords) / len(mppt_coords)
                            
                            mppt_count += 1
    
    def _add_legend(self, ax):
        """Add legend to the visualization"""
        legend_elements = []
        
        # Add roof plane legend
        for i, (roof_id, _) in enumerate(self.roof_planes.items()):
            color = self.roof_colors[i % len(self.roof_colors)]
            legend_elements.append(patches.Patch(color=color, alpha=0.2, label=f'Roof Plane {roof_id}'))
        
        # Add component legend
        legend_elements.extend([
            patches.Patch(color='#2E86AB', alpha=0.8, label='Solar Panels'),
            patches.Patch(color='#00BFFF', alpha=0.9, label='Inverter (Rectangle)'),
            patches.Patch(color='darkblue', alpha=0.8, label='MPPT (Square)'),
            plt.Line2D([0], [0], color='black', linewidth=3, label='String Connection')
        ])
        
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1))
    
    def create_summary_visualization(self, output_path: str = "stringing_summary.png"):
        """
        Create a simplified summary visualization showing just the key information
        
        Args:
            output_path: Path to save the summary visualization
        """
        if not VISUALIZATION_AVAILABLE:
            raise ImportError("matplotlib is required for visualization. Install with: pip install matplotlib")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Left plot: Panel layout
        self._draw_panel_layout(ax1)
        
        # Right plot: Stringing connections
        self._draw_stringing_diagram(ax2)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Summary visualization saved to: {output_path}")
        
        return fig, (ax1, ax2)
    
    def _draw_panel_layout(self, ax):
        """Draw just the panel layout without connections"""
        ax.set_xlim(0, 1024)
        ax.set_ylim(0, 1024)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.set_title('Panel Layout by Roof Plane', fontsize=14, fontweight='bold')
        
        panel_centers = self.get_panel_center_coordinates()
        roof_panels = defaultdict(list)
        
        for panel in self.solar_panels:
            roof_id = panel.get('roof_plane_id', '')
            panel_id = panel.get('panel_id', '')
            if panel_id in panel_centers:
                roof_panels[roof_id].append(panel_id)
        
        for roof_id, panel_ids in roof_panels.items():
            color = self.roof_colors[int(roof_id) % len(self.roof_colors)]
            for panel_id in panel_ids:
                x, y = panel_centers[panel_id]
                panel_rect = Rectangle((x-8, y-8), 16, 16, 
                                     facecolor=color, alpha=0.7,
                                     edgecolor='black', linewidth=0.5)
                ax.add_patch(panel_rect)
    
    def _draw_stringing_diagram(self, ax):
        """Draw a simplified stringing diagram"""
        ax.set_title('Stringing Configuration', fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Create a simple diagram showing stringing plan
        y_pos = 0.9
        for roof_plane, string_lengths in self.results.get('group_plans', {}).items():
            ax.text(0.1, y_pos, f'Roof Plane {roof_plane}: {string_lengths}', 
                   fontsize=12, transform=ax.transAxes)
            y_pos -= 0.1
        
        # Add summary information
        summary = self.results.get('summary', {})
        ax.text(0.1, y_pos, f"Total MPPTs: {summary.get('total_mppts_used', 'N/A')}", 
               fontsize=12, fontweight='bold', transform=ax.transAxes)
        y_pos -= 0.1
        ax.text(0.1, y_pos, f"Total Inverters: {summary.get('total_inverters', 'N/A')}", 
               fontsize=12, fontweight='bold', transform=ax.transAxes)


def create_visualization_from_files(auto_design_path: str, results_path: str, 
                                  output_path: str = "stringing_visualization.png"):
    """
    Convenience function to create visualization from file paths
    
    Args:
        auto_design_path: Path to auto-design.json file
        results_path: Path to results.json file
        output_path: Path to save the visualization
    """
    # Load data
    with open(auto_design_path, 'r') as f:
        auto_design_data = json.load(f)
    
    with open(results_path, 'r') as f:
        results_data = json.load(f)
    
    # Extract the relevant sections
    auto_design = auto_design_data.get('auto_system_design', auto_design_data)
    
    # Create visualizer
    visualizer = SolarStringingVisualizer(auto_design, results_data)
    
    # Create visualization
    return visualizer.create_stringing_visualization(output_path)


def main():
    """Example usage of the visualization helper"""
    print("Solar Stringing Visualization Helper")
    print("=" * 40)
    
    # Example usage
    try:
        # Create visualization from the test results
        fig, ax = create_visualization_from_files(
            'second-test.json', 
            'results_second_test.json',
            'stringing_visualization.png'
        )
        print("Visualization created successfully!")
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
