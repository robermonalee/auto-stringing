"""
Guided PCA Panel Sorting Module

Implements an improved panel sorting strategy that uses:
1. PCA to find the actual panel layout axes
2. Roof azimuth to guide which axis to use for stringing
3. Panel corner data to verify orientation

This provides more accurate stringing paths than pure nearest-neighbor,
especially for rectangular panel layouts and diagonal configurations.

Can be easily enabled/disabled for comparison with simple nearest-neighbor.
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class PanelGeometry:
    """Extended panel data including geometry"""
    panel_id: str
    center: Tuple[float, float]
    corners: List[Tuple[float, float]]  # [c1, c2, c3, c4]
    roof_plane_id: str


class GuidedPCASorter:
    """
    Sorts panels using Guided PCA method for optimal stringing paths.
    
    The method combines:
    - PCA (Principal Component Analysis) to find panel layout axes
    - Roof azimuth to select the correct stringing direction
    - Panel corner data for validation
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the sorter.
        
        Args:
            verbose: If True, print debugging information
        """
        self.verbose = verbose
    
    def sort_panels_for_stringing(
        self,
        panels_data: List[Dict[str, Any]],
        roof_azimuth: float,
        method: str = "guided_pca"
    ) -> List[str]:
        """
        Sort panels into optimal stringing order.
        
        Args:
            panels_data: List of panel dictionaries from auto_design
            roof_azimuth: Azimuth angle of the roof (degrees, 0=North, 90=East)
            method: "guided_pca", "forced_axis", or "nearest_neighbor"
        
        Returns:
            List of panel IDs in optimal stringing order
        """
        if not panels_data:
            return []
        
        if len(panels_data) == 1:
            return [panels_data[0]['panel_id']]
        
        # Parse panel geometry
        panels = self._parse_panel_geometry(panels_data)
        
        # Unified strategy: Use panel edges to get two perpendicular directions
        # Apply same snake pattern logic for ALL section sizes
        if method == "guided_pca":
            # Get axes from panel edges
            ref_panel = panels[0]
            edge_axes = self._extract_panel_edge_axes(ref_panel)
            
            if edge_axes is None:
                if self.verbose:
                    print(f"  Corner extraction failed, using nearest-neighbor")
                return self._sort_using_nearest_neighbor(panels)
            
            axis_1, axis_2 = edge_axes
            
            # Try both perpendicular directions with snake pattern
            result_1 = self._sort_panels_by_axes(panels, axis_1['u_axis'], axis_1['v_axis'])
            result_2 = self._sort_panels_by_axes(panels, axis_2['u_axis'], axis_2['v_axis'])
            
            # Count direction changes and pick best
            changes_1 = self._count_direction_changes(panels, result_1)
            changes_2 = self._count_direction_changes(panels, result_2)
            
            if changes_1 <= changes_2:
                selected_order = result_1
                selected_angle = axis_1['angle']
                selected_changes = changes_1
            else:
                selected_order = result_2
                selected_angle = axis_2['angle']
                selected_changes = changes_2
            
            if self.verbose:
                print(f"  Panel edges: {axis_1['angle']:.1f}° and {axis_2['angle']:.1f}°")
                print(f"  Tested both: {changes_1} vs {changes_2} direction changes")
                print(f"  Selected: {selected_angle:.1f}° ({selected_changes} changes)")
            
            return selected_order
        elif method == "forced_axis":
            return self._sort_using_forced_axis(panels, roof_azimuth)
        else:
            # Fallback to simple nearest neighbor
            return self._sort_using_nearest_neighbor(panels)
    
    def _parse_panel_geometry(self, panels_data: List[Dict[str, Any]]) -> List[PanelGeometry]:
        """Extract panel geometry from panel data"""
        panels = []
        
        for panel in panels_data:
            pix_coords = panel.get('pix_coords', {})
            
            # Support both lowercase and uppercase keys
            c0 = pix_coords.get('c0') or pix_coords.get('C0', [0, 0])
            c1 = pix_coords.get('c1') or pix_coords.get('C1', [0, 0])
            c2 = pix_coords.get('c2') or pix_coords.get('C2', [0, 0])
            c3 = pix_coords.get('c3') or pix_coords.get('C3', [0, 0])
            c4 = pix_coords.get('c4') or pix_coords.get('C4', [0, 0])
            
            # c0 is center, c1-c4 are corners
            center = (float(c0[0]), float(c0[1]))
            corners = [
                (float(c1[0]), float(c1[1])),
                (float(c2[0]), float(c2[1])),
                (float(c3[0]), float(c3[1])),
                (float(c4[0]), float(c4[1]))
            ]
            
            panels.append(PanelGeometry(
                panel_id=panel['panel_id'],
                center=center,
                corners=corners,
                roof_plane_id=panel.get('roof_plane_id', '')
            ))
        
        return panels
    
    def _sort_using_guided_pca(
        self,
        panels: List[PanelGeometry],
        roof_azimuth: float
    ) -> List[str]:
        """
        Sort panels using Guided PCA method for large sections.
        
        Steps:
        1. Run PCA on panel centers to find principal axes
        2. Use pc1 (main axis) for stringing direction
        3. Use pc2 for row detection
        4. Sort panels into rows and order within rows with snake pattern
        """
        if len(panels) < 2:
            return [p.panel_id for p in panels]
        
        # Step 1: Run PCA on panel centers
        centers = np.array([p.center for p in panels])
        pc1, pc2 = self._compute_pca(centers)
        
        if self.verbose:
            print(f"  PCA axes: pc1={pc1}, pc2={pc2}")
        
        # Step 2: Use pc1 (main axis) for stringing, pc2 for rows
        # pc1 by definition has the largest variance (longest dimension)
        u_axis = pc1  # Primary stringing direction (along main axis)
        v_axis = pc2  # Secondary (row) direction (across main axis)
        
        if self.verbose:
            print(f"  Using pc1 (main axis) for stringing")
        
        # Step 3: Sort panels using the selected axes
        return self._sort_panels_by_axes(panels, u_axis, v_axis)
    
    def _sort_using_forced_axis(
        self,
        panels: List[PanelGeometry],
        roof_azimuth: float
    ) -> List[str]:
        """
        Sort panels using forced axis from azimuth only.
        
        This method doesn't use PCA - it derives axes directly from azimuth.
        """
        if len(panels) < 2:
            return [p.panel_id for p in panels]
        
        # Get u_axis from azimuth
        u_axis = self._azimuth_to_vector(roof_azimuth)
        
        # Get perpendicular v_axis
        v_axis = np.array([-u_axis[1], u_axis[0]])
        
        if self.verbose:
            print(f"  Forced axes from azimuth {roof_azimuth}°")
            print(f"  u_axis: {u_axis}, v_axis: {v_axis}")
        
        # Sort panels
        return self._sort_panels_by_axes(panels, u_axis, v_axis)
    
    def _sort_using_azimuth_guided(
        self,
        panels: List[PanelGeometry],
        roof_azimuth: float
    ) -> List[str]:
        """
        Sort panels for small roof sections using simplified snake pattern.
        
        Algorithm:
        1. Detect panel orientation from corner distances (landscape/portrait)
        2. Try both horizontal and vertical stringing directions
        3. For each direction: string in one direction, then reverse (snake)
        4. Pick direction with fewer total direction changes
        
        Args:
            panels: List of panel geometries
            roof_azimuth: Azimuth angle of the roof (not used, kept for compatibility)
        
        Returns:
            List of panel IDs in optimal stringing order
        """
        if len(panels) < 2:
            return [p.panel_id for p in panels]
        
        # Extract panel edge orientations from corners
        ref_panel = panels[0]
        edge_axes = self._extract_panel_edge_axes(ref_panel)
        
        if edge_axes is None:
            # Fallback to nearest neighbor if corner extraction fails
            if self.verbose:
                print(f"  Could not extract panel edges, using nearest-neighbor")
            return self._sort_using_nearest_neighbor(panels)
        
        axis_1, axis_2 = edge_axes
        
        # Try both directions with simplified snake pattern
        result_1 = self._snake_stringing_along_axis(panels, axis_1['u_axis'], axis_1['v_axis'])
        result_2 = self._snake_stringing_along_axis(panels, axis_2['u_axis'], axis_2['v_axis'])
        
        # Count direction changes for each
        changes_1 = self._count_direction_changes(panels, result_1)
        changes_2 = self._count_direction_changes(panels, result_2)
        
        # Pick the one with fewer direction changes
        if changes_1 <= changes_2:
            selected_order = result_1
            selected_angle = axis_1['angle']
        else:
            selected_order = result_2
            selected_angle = axis_2['angle']
        
        if self.verbose:
            print(f"  Panel orientation from corners: {selected_angle:.1f}°")
            print(f"  Tested both edges: Edge1 ({changes_1} changes) vs Edge2 ({changes_2} changes)")
            print(f"  Selected edge with fewer direction changes")
        
        return selected_order
    
    def _snake_stringing_along_axis(
        self,
        panels: List[PanelGeometry],
        u_axis: np.ndarray,
        v_axis: np.ndarray
    ) -> List[str]:
        """
        Snake stringing starting from a corner of the panel layout.
        
        Algorithm:
        1. Find corners of the panel grouping (min/max in u and v)
        2. Start from one corner (bottom-left in axis coordinates)
        3. String row by row with snake pattern (alternate directions)
        4. Stay strictly within rows - no jumping between rows
        """
        if not panels:
            return []
        
        # Project all panels onto the axes
        panel_positions = []
        for panel in panels:
            u_coord = np.dot([panel.center[0], panel.center[1]], u_axis)
            v_coord = np.dot([panel.center[0], panel.center[1]], v_axis)
            panel_positions.append((panel, u_coord, v_coord))
        
        # Group panels into rows based on v_coord
        rows = self._group_into_rows_simple(panel_positions)
        
        # Sort rows by v_coord (ascending)
        rows.sort(key=lambda row: np.mean([v for _, _, v in row]))
        
        # Create snake pattern: alternate row direction
        ordered_ids = []
        for row_idx, row in enumerate(rows):
            # Sort panels in row by u_coord
            row.sort(key=lambda x: x[1])  # Sort by u_coord
            
            # Alternate direction for snake pattern
            if row_idx % 2 == 1:
                row.reverse()
            
            # Add panel IDs
            for panel, u, v in row:
                ordered_ids.append(panel.panel_id)
        
        return ordered_ids
    
    def _group_into_rows_simple(
        self,
        panel_positions: List[Tuple[PanelGeometry, float, float]]
    ) -> List[List[Tuple[PanelGeometry, float, float]]]:
        """
        Group panels into rows based on v-coordinate with generous threshold.
        All panels within threshold of each other (not just row start) are in same row.
        """
        if not panel_positions:
            return []
        
        if len(panel_positions) == 1:
            return [[panel_positions[0]]]
        
        # Generous threshold to handle gaps within rows
        # Panels in the same visual row can be spread across ~50-60 pixels
        row_threshold = 55.0
        
        # Sort by v-coordinate
        sorted_panels = sorted(panel_positions, key=lambda x: x[2])
        
        # Build rows by checking if each panel is within threshold of ANY panel in current row
        rows = []
        current_row = [sorted_panels[0]]
        
        for i in range(1, len(sorted_panels)):
            curr_panel = sorted_panels[i]
            curr_v = curr_panel[2]
            
            # Check if this panel is within threshold of ANY panel already in current row
            in_current_row = False
            for row_panel in current_row:
                if abs(curr_v - row_panel[2]) <= row_threshold:
                    in_current_row = True
                    break
            
            if in_current_row:
                current_row.append(curr_panel)
            else:
                # Start new row
                rows.append(current_row)
                current_row = [curr_panel]
        
        # Add last row
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _count_direction_changes(
        self,
        panels: List[PanelGeometry],
        ordered_ids: List[str]
    ) -> int:
        """
        Count actual direction changes in the stringing path.
        """
        if len(ordered_ids) < 2:
            return 0
        
        # Create panel lookup
        panel_lookup = {p.panel_id: p for p in panels}
        
        # Calculate direction vectors between consecutive panels
        changes = 0
        prev_direction = None
        
        for i in range(len(ordered_ids) - 1):
            p1 = panel_lookup[ordered_ids[i]]
            p2 = panel_lookup[ordered_ids[i + 1]]
            
            # Direction vector
            dx = p2.center[0] - p1.center[0]
            dy = p2.center[1] - p1.center[1]
            
            # Normalize
            mag = np.sqrt(dx*dx + dy*dy)
            if mag < 0.1:
                continue
            
            direction = (dx / mag, dy / mag)
            
            if prev_direction is not None:
                # Check if direction changed significantly (> 45 degrees)
                dot_product = prev_direction[0] * direction[0] + prev_direction[1] * direction[1]
                angle_change = np.arccos(np.clip(dot_product, -1.0, 1.0))
                if angle_change > np.pi / 4:  # > 45 degrees
                    changes += 1
            
            prev_direction = direction
        
        return changes
    
    def _extract_panel_edge_axes(
        self,
        panel: PanelGeometry
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Extract the two perpendicular edge axes from a panel's corner coordinates.
        
        Uses center (stored as first tuple in corners from parsing) to corners
        to get proper panel edge directions.
        
        Returns:
            Tuple of two axis dictionaries, each containing 'u_axis', 'v_axis', and 'angle'
            Returns None if corners are invalid
        """
        if len(panel.corners) < 4:
            return None
        
        # panel.center is the actual center, panel.corners are c1-c4
        center = np.array(panel.center)
        c1 = np.array(panel.corners[0])
        c2 = np.array(panel.corners[1])
        
        # Calculate two edges from center to corners (these are perpendicular for a rectangle)
        edge1 = c1 - center
        edge2 = c2 - center
        
        # Normalize to unit vectors
        edge1_len = np.linalg.norm(edge1)
        edge2_len = np.linalg.norm(edge2)
        
        if edge1_len < 0.1 or edge2_len < 0.1:
            return None
        
        edge1_norm = edge1 / edge1_len
        edge2_norm = edge2 / edge2_len
        
        # Calculate angles
        angle1 = np.degrees(np.arctan2(edge1[1], edge1[0]))
        angle2 = np.degrees(np.arctan2(edge2[1], edge2[0]))
        
        # Create two axis pairs (each edge can be the stringing direction)
        axis_pair_1 = {
            'u_axis': edge1_norm,  # Stringing along edge 1
            'v_axis': edge2_norm,  # Perpendicular (edge 2)
            'angle': angle1
        }
        
        axis_pair_2 = {
            'u_axis': edge2_norm,  # Stringing along edge 2
            'v_axis': edge1_norm,  # Perpendicular (edge 1)
            'angle': angle2
        }
        
        return (axis_pair_1, axis_pair_2)
    
    def _evaluate_axis_quality(
        self,
        panels: List[PanelGeometry],
        u_axis: np.ndarray,
        v_axis: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluate how well a given axis pair organizes panels for efficient wiring.
        
        Measures direction changes in the stringing path. Fewer changes = 
        more efficient wiring (less cornering).
        
        Returns a dict with quality metrics including 'direction_changes'.
        """
        # Project panels onto axes
        panel_coords = []
        for panel in panels:
            u_coord = np.dot([panel.center[0], panel.center[1]], u_axis)
            v_coord = np.dot([panel.center[0], panel.center[1]], v_axis)
            panel_coords.append((panel.panel_id, u_coord, v_coord))
        
        # Cluster into rows
        rows = self._cluster_into_rows(panel_coords)
        
        # Count direction changes in snake pattern
        # Each transition between rows is a direction change
        # Snake pattern: row1 (left-to-right), row2 (right-to-left), row3 (left-to-right), etc.
        direction_changes = max(0, len(rows) - 1)
        
        # Also count changes within rows if panels are not well-aligned
        # For each row, count how many times we need to change direction
        total_within_row_changes = 0
        for row in rows:
            if len(row) > 1:
                # Sort by u-coordinate to see the order
                sorted_row = sorted(row, key=lambda x: x[1])
                
                # Count direction reversals in this row
                # If panels are well-aligned, there should be no reversals
                for i in range(len(sorted_row) - 1):
                    # Check if v-coordinates suggest a reversal
                    # (panels not properly aligned in a straight line)
                    v_diff = abs(sorted_row[i+1][2] - sorted_row[i][2])
                    # If v-difference is significant compared to row clustering threshold,
                    # it suggests misalignment
                    if v_diff > 15:  # Half of the default clustering threshold
                        total_within_row_changes += 1
        
        # Total direction changes = between-row changes + within-row changes
        total_changes = direction_changes + total_within_row_changes
        
        return {
            'num_rows': len(rows),
            'direction_changes': total_changes,
            'avg_panels_per_row': len(panels) / len(rows) if rows else 0
        }
    
    def _compute_pca(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute PCA on 2D points.
        
        Returns:
            Tuple of (pc1, pc2) - the two principal component vectors (unit vectors)
        """
        # Center the data
        mean = np.mean(points, axis=0)
        centered = points - mean
        
        # Compute covariance matrix
        cov = np.cov(centered.T)
        
        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        
        # Sort by eigenvalue (largest first)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Extract principal components (already unit vectors)
        pc1 = eigenvectors[:, 0]
        pc2 = eigenvectors[:, 1]
        
        return pc1, pc2
    
    def _azimuth_to_vector(self, azimuth_degrees: float) -> np.ndarray:
        """
        Convert compass azimuth to 2D unit vector in image coordinates.
        
        Azimuth convention: 0°=North, 90°=East, 180°=South, 270°=West
        Image coordinates: +X=right (East), +Y=down (South)
        
        Args:
            azimuth_degrees: Compass azimuth in degrees
        
        Returns:
            Unit vector [x, y] in image coordinates
        """
        # Convert azimuth to image coordinate system angle
        # In image coords: 0° = East (+X), 90° = South (+Y)
        # In compass: 0° = North, 90° = East
        # Conversion: image_angle = 90 - azimuth
        image_angle_deg = 90 - azimuth_degrees
        image_angle_rad = math.radians(image_angle_deg)
        
        # Create unit vector
        vector = np.array([
            math.cos(image_angle_rad),
            math.sin(image_angle_rad)
        ])
        
        return vector
    
    def _sort_panels_by_axes(
        self,
        panels: List[PanelGeometry],
        u_axis: np.ndarray,
        v_axis: np.ndarray
    ) -> List[str]:
        """
        Sort panels using the (u, v) coordinate system.
        
        Process:
        1. Project each panel onto u and v axes
        2. Group panels by v-coordinate (rows)
        3. Sort panels within each row by u-coordinate
        4. Use snake pattern (alternate row directions)
        """
        # Project panels onto (u, v) axes
        panel_coords = []
        for panel in panels:
            center = np.array(panel.center)
            u_coord = np.dot(center, u_axis)
            v_coord = np.dot(center, v_axis)
            panel_coords.append((panel.panel_id, u_coord, v_coord))
        
        # Group panels into rows based on v-coordinate
        # Use clustering to handle slight variations
        rows = self._cluster_into_rows(panel_coords)
        
        if self.verbose:
            print(f"  Identified {len(rows)} rows")
        
        # Sort rows by average v-coordinate
        rows.sort(key=lambda row: np.mean([v for _, _, v in row]))
        
        # Sort panels within each row and apply snake pattern
        sorted_ids = []
        for row_idx, row in enumerate(rows):
            # Sort by u-coordinate
            row.sort(key=lambda item: item[1])  # Sort by u_coord
            
            # Alternate direction for snake pattern
            if row_idx % 2 == 1:
                row.reverse()
            
            # Add panel IDs to result
            sorted_ids.extend([panel_id for panel_id, _, _ in row])
        
        return sorted_ids
    
    def _cluster_into_rows(
        self,
        panel_coords: List[Tuple[str, float, float]],
        threshold: float = None
    ) -> List[List[Tuple[str, float, float]]]:
        """
        Cluster panels into rows based on v-coordinate proximity.
        
        Args:
            panel_coords: List of (panel_id, u_coord, v_coord)
            threshold: Maximum distance to be considered same row (auto if None)
        
        Returns:
            List of rows, where each row is a list of (panel_id, u_coord, v_coord)
        """
        if not panel_coords:
            return []
        
        # Auto-adjust threshold based on panel count
        # More panels = tighter threshold for better row detection
        if threshold is None:
            if len(panel_coords) < 12:
                threshold = 50.0  # Looser for small groups
            elif len(panel_coords) < 24:
                threshold = 35.0  # Medium for medium groups
            else:
                threshold = 25.0  # Tighter for large groups
        
        # Sort by v-coordinate
        sorted_by_v = sorted(panel_coords, key=lambda x: x[2])
        
        # Group into rows
        rows = []
        current_row = [sorted_by_v[0]]
        
        for i in range(1, len(sorted_by_v)):
            prev_v = sorted_by_v[i-1][2]
            curr_v = sorted_by_v[i][2]
            
            if abs(curr_v - prev_v) <= threshold:
                # Same row
                current_row.append(sorted_by_v[i])
            else:
                # New row
                rows.append(current_row)
                current_row = [sorted_by_v[i]]
        
        # Add last row
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _sort_using_nearest_neighbor(self, panels: List[PanelGeometry]) -> List[str]:
        """
        Fallback: Simple nearest-neighbor sorting.
        
        This is the original simple method for comparison.
        """
        if not panels:
            return []
        
        # Start from first panel
        remaining = list(panels)
        sorted_ids = [remaining[0].panel_id]
        current = remaining[0]
        remaining.pop(0)
        
        while remaining:
            # Find closest panel
            distances = [
                (self._distance_2d(current.center, p.center), p)
                for p in remaining
            ]
            distances.sort()
            
            # Add closest
            current = distances[0][1]
            sorted_ids.append(current.panel_id)
            remaining.remove(current)
        
        return sorted_ids
    
    def _distance_2d(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two 2D points"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


# Convenience function for easy integration
def sort_panels_guided_pca(
    panels_data: List[Dict[str, Any]],
    roof_azimuth: float,
    method: str = "guided_pca",
    verbose: bool = False
) -> List[str]:
    """
    Sort panels using guided PCA method.
    
    Args:
        panels_data: List of panel dictionaries from auto_design
        roof_azimuth: Azimuth angle of the roof (degrees)
        method: "guided_pca", "forced_axis", or "nearest_neighbor"
        verbose: Print debugging information
    
    Returns:
        List of panel IDs in optimal stringing order
    """
    sorter = GuidedPCASorter(verbose=verbose)
    return sorter.sort_panels_for_stringing(panels_data, roof_azimuth, method)

