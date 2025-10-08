"""
Solar Panel Stringing Optimizer

This module implements the complete end-to-end process for optimizing solar panel
stringing configurations based on temperature-adjusted voltages and inverter constraints.

The algorithm follows these phases:
1. Pre-Computation: Calculate temperature-adjusted panel voltages
2. String Generation: Generate valid string combinations for each panel group
3. Optimization: Assign strings to MPPTs with parallel connection logic
4. Output: Present the optimal configuration
"""

import json
import math
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from solar_cell_temperature_coefficients import calculate_voc_normalized, calculate_isc_normalized


@dataclass
class PanelSpecs:
    """Solar panel specifications"""
    panel_id: str
    voc_stc: float  # Open-circuit voltage at STC (V)
    isc_stc: float  # Short-circuit current at STC (A)
    vmpp_stc: float  # Maximum power point voltage at STC (V)
    impp_stc: float  # Maximum power point current at STC (A)
    roof_plane_id: str
    center_coords: Tuple[float, float]  # (x, y) pixel coordinates


@dataclass
class InverterSpecs:
    """Inverter specifications"""
    inverter_id: str
    max_dc_voltage: float  # Maximum DC input voltage (V)
    mppt_min_voltage: float  # Minimum MPPT operating voltage (V)
    mppt_max_voltage: float  # Maximum MPPT operating voltage (V)
    max_dc_current_per_mppt: float  # Maximum DC current per MPPT (A)
    max_dc_current_per_string: float  # Maximum DC current per string (A)
    number_of_mppts: int  # Number of MPPTs available
    startup_voltage: float  # Startup voltage (V)


@dataclass
class TemperatureData:
    """Site temperature data"""
    min_temp_c: float  # Record minimum temperature (°C)
    max_temp_c: float  # Record maximum temperature (°C)
    avg_high_temp_c: float  # Average high temperature (°C)
    avg_low_temp_c: float  # Average low temperature (°C)


@dataclass
class StringingPlan:
    """A complete stringing plan for all panel groups"""
    group_plans: Dict[str, List[int]]  # Group name -> list of string lengths
    total_mppts_used: int
    configuration: Dict[str, Any]  # Detailed configuration
    connections: Dict[str, Any]  # Detailed connection plan with panel IDs


class SolarStringingOptimizer:
    """
    Main optimizer class that implements the complete stringing optimization algorithm
    """
    
    def __init__(self, panel_specs: List[PanelSpecs], inverter_specs: InverterSpecs, 
                 temperature_data: TemperatureData, temp_range: str = "extreme", 
                 min_heur_panels: int = 12, use_snake_pattern: bool = False):
        self.panel_specs = panel_specs
        self.inverter_specs = inverter_specs
        self.temperature_data = temperature_data
        self.temp_range = temp_range  # "extreme" or "average"
        self.min_heur_panels = min_heur_panels  # Switch to heuristic when total panels > this
        self.use_snake_pattern = use_snake_pattern  # Enable snake-pattern organization
        self.panel_groups = self._group_panels_by_roof_plane()
        self.use_heuristic = len(panel_specs) > min_heur_panels
        
    def _group_panels_by_roof_plane(self) -> Dict[str, List[PanelSpecs]]:
        """Group panels by their roof plane ID"""
        groups = defaultdict(list)
        for panel in self.panel_specs:
            groups[panel.roof_plane_id].append(panel)
        return dict(groups)
    
    def optimize(self) -> StringingPlan:
        """
        Main optimization method that orchestrates all phases
        """
        start_time = time.time()
        print(f"Starting solar stringing optimization at {time.strftime('%H:%M:%S')}...")
        print(f"System has {len(self.panel_specs)} panels across {len(self.panel_groups)} roof planes")
        
        # Choose optimization strategy based on system size
        if self.use_heuristic:
            print(f"Using HEURISTIC algorithm (system size > {self.min_heur_panels} panels)")
            optimal_plan = self._optimize_heuristic()
        else:
            print(f"Using EXHAUSTIVE algorithm (system size <= {self.min_heur_panels} panels)")
            optimal_plan = self._optimize_exhaustive()
        
        total_time = time.time() - start_time
        print(f"\nOptimization complete! Using {optimal_plan.total_mppts_used} MPPTs total.")
        print(f"Total optimization time: {total_time:.2f} seconds")
        return optimal_plan
    
    def force_heuristic_optimization(self, temperature_strategy: str = "extreme") -> Dict:
        """
        Force heuristic optimization even for small systems (for comparison purposes)
        """
        print("FORCING HEURISTIC algorithm for comparison")
        start_time = time.time()
        
        # Temporarily force heuristic mode
        original_use_heuristic = self.use_heuristic
        self.use_heuristic = True
        
        print(f"System has {len(self.panel_specs)} panels across {len(self.panel_groups)} roof planes")
        print(f"Using HEURISTIC algorithm (FORCED for comparison)")
        
        optimal_plan = self._optimize_heuristic()
        
        # Restore original setting
        self.use_heuristic = original_use_heuristic
        
        total_time = time.time() - start_time
        print(f"\nOptimization complete! Using {optimal_plan.total_mppts_used} MPPTs total.")
        print(f"Total optimization time: {total_time:.2f} seconds")
        return optimal_plan
    
    def roof_section_optimization(self, temperature_strategy: str = "extreme", use_snake_pattern: bool = False, enable_load_balancing: bool = False) -> Dict:
        """
        Roof-section-based optimization that treats each roof section as an independent system
        with smart handling for contiguous sections and size-based algorithm selection
        """
        print("ROOF-SECTION-BASED OPTIMIZATION")
        start_time = time.time()
        
        print(f"System has {len(self.panel_specs)} panels across {len(self.panel_groups)} roof planes")
        
        # Step 1: Analyze roof sections and identify contiguous sections
        roof_analysis = self._analyze_roof_sections()
        
        # Step 2: Group contiguous sections if beneficial
        optimized_groups = self._optimize_roof_grouping(roof_analysis)
        
        # Step 3: Optimize each group independently
        all_results = []
        total_mppts = 0
        
        for group_id, group_info in optimized_groups.items():
            print(f"\n--- Optimizing Group {group_id} ---")
            print(f"Roof sections: {group_info['roof_sections']}")
            print(f"Total panels: {group_info['total_panels']}")
            
            # Choose algorithm based on group size
            if group_info['total_panels'] > 15:
                print(f"Using HEURISTIC algorithm (group size > 15 panels)")
                group_result = self._optimize_group_heuristic(group_info, use_snake_pattern, enable_load_balancing)
            else:
                print(f"Using HEURISTIC algorithm (group size <= 15 panels) - for cleaner stringing")
                group_result = self._optimize_group_heuristic(group_info, use_snake_pattern, enable_load_balancing)
            
            all_results.append(group_result)
            total_mppts += group_result['total_mppts']
        
        # Step 4: Combine all results
        final_result = self._combine_roof_section_results(all_results)
        
        total_time = time.time() - start_time
        print(f"\nRoof-section optimization complete! Using {total_mppts} MPPTs total.")
        print(f"Total optimization time: {total_time:.2f} seconds")
        
        return final_result
    
    def _analyze_roof_sections(self) -> Dict:
        """
        Analyze roof sections and identify contiguous sections
        """
        roof_analysis = {}
        
        for roof_id, panels in self.panel_groups.items():
            roof_analysis[roof_id] = {
                'roof_id': roof_id,
                'panel_count': len(panels),
                'panels': panels,
                'is_contiguous': self._is_contiguous_roof_section(panels),
                'neighbors': self._find_contiguous_neighbors(roof_id)
            }
        
        return roof_analysis
    
    def _is_contiguous_roof_section(self, panels: List[PanelSpecs]) -> bool:
        """
        Determine if a roof section has contiguous panels
        For now, assume all panels in the same roof section are contiguous
        """
        return True  # Simplified for now
    
    def _find_contiguous_neighbors(self, roof_id: str) -> List[str]:
        """
        Find roof sections that are contiguous to the given roof section
        For now, return empty list - this would need spatial analysis
        """
        return []  # Simplified for now
    
    def _optimize_roof_grouping(self, roof_analysis: Dict) -> Dict:
        """
        Group contiguous roof sections if their combined panel count is beneficial
        """
        optimized_groups = {}
        max_panels_per_inverter = 18  # Assume max 18 panels per inverter (2 MPPTs × 9 panels)
        group_id = 1
        
        # Sort roof sections by panel count (smallest first)
        sorted_roofs = sorted(roof_analysis.items(), key=lambda x: x[1]['panel_count'])
        processed_roofs = set()
        
        for roof_id, roof_info in sorted_roofs:
            if roof_id in processed_roofs:
                continue
            
            # Check if this roof section can be combined with neighbors
            combined_roofs = [roof_id]
            total_panels = roof_info['panel_count']
            
            # Try to combine with contiguous neighbors if total would be beneficial
            for neighbor_id in roof_info['neighbors']:
                if (neighbor_id not in processed_roofs and 
                    neighbor_id in roof_analysis and
                    total_panels + roof_analysis[neighbor_id]['panel_count'] <= max_panels_per_inverter):
                    
                    combined_roofs.append(neighbor_id)
                    total_panels += roof_analysis[neighbor_id]['panel_count']
                    processed_roofs.add(neighbor_id)
            
            # Create group
            group_panels = []
            for rid in combined_roofs:
                group_panels.extend(roof_analysis[rid]['panels'])
                processed_roofs.add(rid)
            
            optimized_groups[f"Group_{group_id}"] = {
                'roof_sections': combined_roofs,
                'total_panels': total_panels,
                'panels': group_panels
            }
            group_id += 1
        
        return optimized_groups
    
    def _optimize_group_heuristic(self, group_info: Dict, use_snake_pattern: bool = False, enable_load_balancing: bool = False) -> Dict:
        """
        Optimize a group using heuristic algorithm
        """
        # Create a temporary optimizer for this group
        group_panels = group_info['panels']
        
        # Calculate ideal string length for this group using the same logic as heuristic
        temp_adjusted = self._calculate_temperature_adjusted_voltages()
        group_id = group_panels[0].roof_plane_id
        group_data = temp_adjusted[group_id]
        
        min_voltage = group_data["min_voltage"]
        max_voltage = group_data["max_voltage"]
        
        # Calculate valid string length range
        min_panels = math.ceil(self.inverter_specs.mppt_min_voltage / min_voltage)
        max_panels_safety = math.floor(self.inverter_specs.max_dc_voltage / max_voltage)
        max_panels_operational = math.floor(self.inverter_specs.mppt_max_voltage / min_voltage)
        max_panels = min(max_panels_safety, max_panels_operational)
        
        # Target 85% of max MPPT voltage for efficiency
        target_voltage = self.inverter_specs.mppt_max_voltage * 0.85
        ideal_length = round(target_voltage / min_voltage)
        ideal_length = max(min_panels, min(ideal_length, max_panels))
        
        # Apply stringing (snake pattern or modulus-based)
        if use_snake_pattern:
            strings, stragglers = self._create_snake_pattern_strings(group_panels, ideal_length, {
                'min_panels': min_panels,
                'max_panels': max_panels,
                'panel_count': len(group_panels)
            }, enable_load_balancing)
        else:
            strings, stragglers = self._create_modulus_strings(group_panels, ideal_length, {
                'min_panels': min_panels,
                'max_panels': max_panels,
                'panel_count': len(group_panels)
            })
        
        # Handle stragglers
        if stragglers:
            straggler_strings = self._handle_stragglers(stragglers, strings)
            strings.extend(straggler_strings)
            
            # Apply load balancing after adding stragglers if enabled
            if enable_load_balancing and strings:
                print(f"      Applying load balancing after stragglers to {len(strings)} strings...")
                balanced_strings = self._balance_string_lengths(strings, ideal_length)
                strings = balanced_strings
        
        # Assign to MPPTs
        mppts_used, connections = self._greedy_mppt_assignment(strings)
        
        return {
            'group_id': group_info['roof_sections'],
            'total_mppts': mppts_used,
            'strings': strings,
            'connections': connections
        }
    
    def _optimize_group_exhaustive(self, group_info: Dict) -> Dict:
        """
        Optimize a group using exhaustive algorithm
        """
        # Create a temporary optimizer for this group
        group_panels = group_info['panels']
        
        # Generate all valid string combinations
        valid_combinations = self._generate_valid_string_combinations(group_panels)
        
        # Find optimal MPPT assignment
        best_plan = self._find_optimal_mppt_assignment(valid_combinations)
        
        return {
            'group_id': group_info['roof_sections'],
            'total_mppts': best_plan['total_mppts'],
            'strings': best_plan['strings'],
            'connections': best_plan['connections']
        }
    
    def _generate_valid_string_combinations(self, panels: List[PanelSpecs]) -> List[List[Dict]]:
        """
        Generate all valid string combinations for a group of panels
        """
        # Calculate voltage constraints for this group using existing method
        temp_adjusted = self._calculate_temperature_adjusted_voltages()
        group_id = panels[0].roof_plane_id
        max_voltage_per_panel = temp_adjusted[group_id]['max_voltage']
        min_voltage_per_panel = temp_adjusted[group_id]['min_voltage']
        
        # Calculate valid string length range
        max_string_length = min(9, int(self.inverter_specs.mppt_max_voltage / max_voltage_per_panel))
        min_string_length = max(3, int(self.inverter_specs.mppt_min_voltage / min_voltage_per_panel))
        
        valid_combinations = []
        
        # Generate all possible string combinations using backtracking
        def backtrack(remaining_panels, current_strings, start_idx):
            if not remaining_panels:
                valid_combinations.append(current_strings.copy())
                return
            
            for length in range(min_string_length, min(max_string_length + 1, len(remaining_panels) + 1)):
                if len(remaining_panels) >= length:
                    # Create a string of this length
                    string_panels = remaining_panels[:length]
                    string_data = {
                        'length': length,
                        'panels': [p.panel_id for p in string_panels],
                        'roof_plane': panels[0].roof_plane_id
                    }
                    
                    current_strings.append(string_data)
                    backtrack(remaining_panels[length:], current_strings, start_idx + length)
                    current_strings.pop()
        
        backtrack(panels, [], 0)
        return valid_combinations
    
    def _find_optimal_mppt_assignment(self, valid_combinations: List[List[Dict]]) -> Dict:
        """
        Find the optimal MPPT assignment from valid string combinations
        """
        best_plan = None
        min_mppts = float('inf')
        
        for combination in valid_combinations:
            # Try to assign strings to MPPTs
            mppts_used, connections = self._greedy_mppt_assignment(combination)
            
            if mppts_used < min_mppts:
                min_mppts = mppts_used
                best_plan = {
                    'total_mppts': mppts_used,
                    'strings': combination,
                    'connections': connections
                }
        
        return best_plan if best_plan else {
            'total_mppts': 0,
            'strings': [],
            'connections': {}
        }
    
    def _combine_roof_section_results(self, all_results: List[Dict]) -> Dict:
        """
        Combine results from all roof section groups
        """
        combined_connections = {}
        total_mppts = 0
        all_strings = []
        
        for result in all_results:
            total_mppts += result['total_mppts']
            all_strings.extend(result['strings'])
            
            # Add connections for each roof section in this group
            for roof_section in result['group_id']:
                # The result['connections'] already has the correct structure
                # Copy the connections for this roof section
                if roof_section in result['connections']:
                    combined_connections[roof_section] = result['connections'][roof_section]
        
        # Format the results to match the expected structure for visualization
        formatted_result = self._format_final_configuration_roof_section(combined_connections, total_mppts, all_strings)
        
        return formatted_result
    
    def _format_final_configuration_roof_section(self, connections: Dict, total_mppts: int, all_strings: List[Dict]) -> Dict:
        """
        Format roof-section results to match the expected structure for visualization
        """
        # Create summary information
        total_panels = 0
        for roof_plane, inverters in connections.items():
            for inverter_id, mppts in inverters.items():
                for mppt_id, panel_ids in mppts.items():
                    total_panels += len(panel_ids)
        
        summary = {
            "total_inverters": len(connections),
            "total_mppts_used": total_mppts,
            "total_panels": total_panels,
            "optimization_method": "roof_section_based"
        }
        
        # Create group plans (simplified for roof-section approach)
        group_plans = {}
        for roof_plane, inverters in connections.items():
            roof_strings = []
            for inverter_id, mppts in inverters.items():
                for mppt_id, panel_ids in mppts.items():
                    roof_strings.append(len(panel_ids))
            group_plans[roof_plane] = roof_strings
        
        # Create system details
        system_details = {
            "inverter_specifications": {
                "model": self.inverter_specs.inverter_id,
                "max_dc_voltage": self.inverter_specs.max_dc_voltage,
                "mppt_voltage_range": f"{self.inverter_specs.mppt_min_voltage}V - {self.inverter_specs.mppt_max_voltage}V",
                "max_current_per_mppt": self.inverter_specs.max_dc_current_per_mppt,
                "available_mppts": self.inverter_specs.number_of_mppts
            },
            "temperature_range": f"{self.temperature_data.min_temp_c}°C to {self.temperature_data.max_temp_c}°C",
            "location": "California"  # Default location
        }
        
        return {
            "summary": summary,
            "group_plans": group_plans,
            "connections": connections,
            "configuration": {
                "inverter_model": self.inverter_specs.inverter_id,
                "mppt_voltage_range": f"{self.inverter_specs.mppt_min_voltage}V - {self.inverter_specs.mppt_max_voltage}V",
                "available_mppts": self.inverter_specs.number_of_mppts,
                "temperature_range": f"{self.temperature_data.min_temp_c}°C to {self.temperature_data.max_temp_c}°C",
                "location": "California"
            },
            "system_details": system_details
        }
    
    def _optimize_exhaustive(self) -> StringingPlan:
        """
        Original exhaustive optimization method for small systems
        """
        # Phase 1: Calculate temperature-adjusted voltages
        print("\nPhase 1: Calculating temperature-adjusted panel voltages...")
        phase1_start = time.time()
        temp_adjusted_voltages = self._calculate_temperature_adjusted_voltages()
        phase1_time = time.time() - phase1_start
        print(f"Phase 1 completed in {phase1_time:.2f} seconds")
        
        # Phase 2: Generate valid string combinations for each group
        print("\nPhase 2: Generating valid string combinations...")
        phase2_start = time.time()
        valid_string_plans = self._generate_valid_string_plans(temp_adjusted_voltages)
        phase2_time = time.time() - phase2_start
        print(f"Phase 2 completed in {phase2_time:.2f} seconds")
        
        # Phase 3: Optimize MPPT assignments
        print("\nPhase 3: Optimizing MPPT assignments...")
        phase3_start = time.time()
        optimal_plan = self._optimize_mppt_assignments(valid_string_plans)
        phase3_time = time.time() - phase3_start
        print(f"Phase 3 completed in {phase3_time:.2f} seconds")
        
        # Phase 4: Format output
        print("\nPhase 4: Formatting final configuration...")
        phase4_start = time.time()
        final_config = self._format_final_configuration(optimal_plan)
        phase4_time = time.time() - phase4_start
        print(f"Phase 4 completed in {phase4_time:.2f} seconds")
        
        return optimal_plan
    
    def _optimize_heuristic(self) -> StringingPlan:
        """
        New heuristic/greedy optimization method for large systems
        """
        # Phase 1: Calculate temperature-adjusted voltages
        print("\nPhase 1: Calculating temperature-adjusted panel voltages...")
        phase1_start = time.time()
        temp_adjusted_voltages = self._calculate_temperature_adjusted_voltages()
        phase1_time = time.time() - phase1_start
        print(f"Phase 1 completed in {phase1_time:.2f} seconds")
        
        # Phase 2: Greedy string creation and assignment
        print("\nPhase 2: Greedy string creation and assignment...")
        phase2_start = time.time()
        optimal_plan = self._greedy_string_optimization(temp_adjusted_voltages)
        phase2_time = time.time() - phase2_start
        print(f"Phase 2 completed in {phase2_time:.2f} seconds")
        
        return optimal_plan
    
    def _greedy_string_optimization(self, temp_adjusted: Dict[str, Dict[str, float]]) -> StringingPlan:
        """
        Greedy/heuristic string optimization for large systems
        """
        all_strings = []
        group_plans = {}
        
        # Step 1: Calculate ideal string length for each group
        print("  Calculating ideal string lengths...")
        ideal_lengths = {}
        for group_id, group_data in temp_adjusted.items():
            min_voltage = group_data["min_voltage"]
            max_voltage = group_data["max_voltage"]
            
            # Calculate valid string length range
            min_panels = math.ceil(self.inverter_specs.mppt_min_voltage / min_voltage)
            max_panels_safety = math.floor(self.inverter_specs.max_dc_voltage / max_voltage)
            max_panels_operational = math.floor(self.inverter_specs.mppt_max_voltage / min_voltage)
            max_panels = min(max_panels_safety, max_panels_operational)
            
            # Target 85% of max MPPT voltage for efficiency
            target_voltage = self.inverter_specs.mppt_max_voltage * 0.85
            ideal_length = round(target_voltage / min_voltage)
            ideal_length = max(min_panels, min(ideal_length, max_panels))
            
            ideal_lengths[group_id] = {
                'ideal_length': ideal_length,
                'min_panels': min_panels,
                'max_panels': max_panels,
                'panel_count': group_data["panel_count"]
            }
            
            print(f"    Group {group_id}: {group_data['panel_count']} panels, ideal length: {ideal_length}")
        
        # Step 2: Create strings using modulus-based optimization
        print("  Creating modulus-optimized strings...")
        all_stragglers = []  # Collect stragglers from all groups
        
        for group_id, group_data in temp_adjusted.items():
            panels = self.panel_groups[group_id]
            ideal_info = ideal_lengths[group_id]
            ideal_length = ideal_info['ideal_length']
            panel_count = ideal_info['panel_count']
            
            # Apply stringing strategy (snake pattern or modulus)
            if self.use_snake_pattern:
                group_strings, stragglers = self._create_snake_pattern_strings(panels, ideal_length, ideal_info)
            else:
                group_strings, stragglers = self._create_modulus_strings(panels, ideal_length, ideal_info)
            
            # Add to all strings
            for string_data in group_strings:
                all_strings.append(string_data)
            
            # Collect stragglers for later processing
            all_stragglers.extend(stragglers)
            
            # Store group plan
            group_plans[group_id] = [s['length'] for s in group_strings]
            print(f"    Group {group_id}: Created {len(group_strings)} strings, {len(stragglers)} stragglers")
        
        # Step 2.5: Handle stragglers by connecting to closest available inverters
        if all_stragglers:
            print(f"  Processing {len(all_stragglers)} total stragglers...")
            straggler_strings = self._handle_stragglers(all_stragglers, all_strings)
            all_strings.extend(straggler_strings)
            print(f"  Created {len(straggler_strings)} additional strings from stragglers")
        
        # Step 3: Assign strings to MPPTs using greedy bin-packing
        print("  Assigning strings to MPPTs...")
        mppts_used, connections = self._greedy_mppt_assignment(all_strings)
        
        return StringingPlan(
            group_plans=group_plans,
            total_mppts_used=mppts_used,
            configuration=self._build_detailed_configuration(group_plans),
            connections=connections
        )
    
    def _greedy_mppt_assignment(self, all_strings: List[Dict]) -> Tuple[int, Dict[str, Any]]:
        """
        Greedy MPPT assignment using bin-packing approach
        """
        # Sort strings by length (descending) for better packing
        all_strings.sort(key=lambda x: x['length'], reverse=True)
        
        mppts = []  # List of MPPTs, each containing connection details
        total_inverters_needed = 1
        connections = {}
        
        for string_data in all_strings:
            string_length = string_data['length']
            string_panels = string_data['panels']
            roof_plane = string_data['roof_plane']
            
            # Try to find parallel opportunity first
            parallel_found = False
            for mppt_index, mppt in enumerate(mppts):
                # Check if this MPPT has strings of the same length
                same_length_strings = [s for s in mppt if s['length'] == string_length]
                if same_length_strings:
                    # Check current limit
                    current_strings_of_length = len(same_length_strings)
                    panel_isc = self.panel_specs[0].isc_stc  # Assuming all panels have same Isc
                    if (current_strings_of_length + 1) * panel_isc <= self.inverter_specs.max_dc_current_per_mppt:
                        # Add this string to the existing MPPT
                        mppt.append(string_data)
                        parallel_found = True
                        break
            
            # If no parallel opportunity, need a new MPPT
            if not parallel_found:
                # Check if we have available MPPTs in current inverter
                available_mppts = (total_inverters_needed * self.inverter_specs.number_of_mppts) - len(mppts)
                
                if available_mppts > 0:
                    # Use available MPPT in current inverter
                    mppts.append([string_data])
                else:
                    # Need a new inverter
                    total_inverters_needed += 1
                    mppts.append([string_data])
        
        # Build detailed connections structure
        for mppt_index, mppt in enumerate(mppts):
            inverter_num = (mppt_index // self.inverter_specs.number_of_mppts) + 1
            mppt_num = (mppt_index % self.inverter_specs.number_of_mppts) + 1
            
            global_inverter_id = f"Inverter_{inverter_num}"
            global_mppt_id = f"MPPT_{inverter_num}_{mppt_num}"
            
            # Group strings by roof plane within this MPPT
            roof_plane_strings = {}
            for string_data in mppt:
                roof_plane = string_data['roof_plane']
                if roof_plane not in roof_plane_strings:
                    roof_plane_strings[roof_plane] = []
                roof_plane_strings[roof_plane].extend(string_data['panels'])
            
            # Add to connections structure
            for roof_plane, panel_ids in roof_plane_strings.items():
                if roof_plane not in connections:
                    connections[roof_plane] = {}
                
                if global_inverter_id not in connections[roof_plane]:
                    connections[roof_plane][global_inverter_id] = {}
                
                connections[roof_plane][global_inverter_id][global_mppt_id] = panel_ids
        
        # Store the total inverters needed for reporting
        self._total_inverters_needed = total_inverters_needed
        
        return len(mppts), connections
    
    def _create_contiguous_strings(self, panels: List[PanelSpecs], ideal_length: int, ideal_info: Dict) -> List[Dict]:
        """
        Create contiguous strings using seed-and-grow algorithm for better physical layout
        """
        strings = []
        unassigned_panels = panels.copy()
        
        # Mark panels as unassigned
        for panel in unassigned_panels:
            panel.is_assigned = False
        
        while True:
            # Find the next unassigned panel to be a seed (top-left most)
            seed_panel = self._find_next_seed(unassigned_panels)
            if not seed_panel:
                break
            
            # Check if we have enough panels left for a valid string
            remaining_unassigned = [p for p in unassigned_panels if not getattr(p, 'is_assigned', False)]
            if len(remaining_unassigned) < ideal_info['min_panels']:
                # Try to create a string with remaining panels if possible
                if len(remaining_unassigned) >= ideal_info['min_panels']:
                    current_string = remaining_unassigned[:ideal_info['max_panels']]
                    string_data = {
                        'length': len(current_string),
                        'panels': [p.panel_id for p in current_string],
                        'roof_plane': current_string[0].roof_plane_id,
                        'type': 'contiguous_remaining'
                    }
                    strings.append(string_data)
                    
                    # Mark panels as assigned
                    for panel in current_string:
                        panel.is_assigned = True
                break
            
            # Create a contiguous string starting from the seed
            current_string = self._grow_contiguous_string(seed_panel, unassigned_panels, ideal_length, ideal_info)
            
            if current_string and len(current_string) >= ideal_info['min_panels']:
                string_data = {
                    'length': len(current_string),
                    'panels': [p.panel_id for p in current_string],
                    'roof_plane': current_string[0].roof_plane_id,
                    'type': 'contiguous'
                }
                strings.append(string_data)
                
                # Mark panels as assigned
                for panel in current_string:
                    panel.is_assigned = True
            else:
                # If we can't create a valid string, mark the seed as assigned to avoid infinite loop
                seed_panel.is_assigned = True
        
        return strings
    
    def _create_modulus_strings(self, panels: List[PanelSpecs], ideal_length: int, ideal_info: Dict) -> Tuple[List[Dict], List[PanelSpecs]]:
        """
        Create strings using modulus-based optimization to minimize stragglers
        """
        strings = []
        stragglers = []
        panel_count = len(panels)

        # Calculate how many full ideal strings we can make
        num_full_strings = panel_count // ideal_length
        remainder = panel_count % ideal_length

        print(f"      Modulus analysis: {panel_count} panels = {num_full_strings} × {ideal_length} + {remainder} remainder")

        # Create full ideal strings
        panel_index = 0
        for i in range(num_full_strings):
            string_panels = panels[panel_index:panel_index + ideal_length]
            string_data = {
                'length': ideal_length,
                'panels': [p.panel_id for p in string_panels],
                'roof_plane': panels[0].roof_plane_id,
                'type': 'modulus_ideal'
            }
            strings.append(string_data)
            panel_index += ideal_length

        # Handle remainder using recursive modulus approach
        if remainder > 0:
            remaining_panels = panels[panel_index:]
            remainder_strings, remainder_stragglers = self._handle_remainder_with_modulus(
                remaining_panels, ideal_info
            )
            strings.extend(remainder_strings)
            stragglers.extend(remainder_stragglers)

        return strings, stragglers

    def _create_snake_pattern_strings(self, panels: List[PanelSpecs], ideal_length: int, ideal_info: Dict, enable_load_balancing: bool = False) -> Tuple[List[Dict], List[PanelSpecs]]:
        """
        Create strings using proximity-based organization for irregularly positioned panels
        This is more suitable for real-world data where panels are not in a regular grid
        """
        strings = []
        stragglers = []
        
        if not panels:
            return strings, stragglers
            
        # Check if panels are in a regular grid pattern
        is_regular_grid = self._check_if_regular_grid(panels)
        
        if is_regular_grid:
            print(f"      Regular grid detected - using snake pattern")
            # Use snake pattern for regular grids
            sorted_panels = self._sort_panels_snake_pattern(panels)
        else:
            print(f"      Irregular layout detected - using proximity-based organization")
            # Use proximity-based organization for irregular layouts
            sorted_panels = self._sort_panels_by_proximity(panels)
        
        # Create strings of ideal length
        panel_count = len(sorted_panels)
        num_full_strings = panel_count // ideal_length
        remainder = panel_count % ideal_length
        
        print(f"      Organization: {panel_count} panels = {num_full_strings} × {ideal_length} + {remainder} remainder")
        
        # Create strings
        panel_index = 0
        for i in range(num_full_strings):
            string_panels = sorted_panels[panel_index:panel_index + ideal_length]
            
            # Verify this string has reasonable distances
            self._verify_string_distances(string_panels, i+1)
            
            string_data = {
                'length': ideal_length,
                'panels': [p.panel_id for p in string_panels],
                'roof_plane': panels[0].roof_plane_id,
                'type': 'proximity_organized'
            }
            strings.append(string_data)
            panel_index += ideal_length
        
        # Handle remainder
        if remainder > 0:
            remaining_panels = sorted_panels[panel_index:]
            remainder_strings, remainder_stragglers = self._handle_remainder_with_modulus(
                remaining_panels, ideal_info
            )
            strings.extend(remainder_strings)
            stragglers.extend(remainder_stragglers)
        
        # Apply load balancing to improve string distribution within this roof section
        if strings and enable_load_balancing:
            print(f"      Applying load balancing to {len(strings)} strings...")
            balanced_strings = self._balance_string_lengths(strings, ideal_length)
            strings = balanced_strings
        
        return strings, stragglers

    def _check_if_regular_grid(self, panels: List[PanelSpecs]) -> bool:
        """
        Check if panels are arranged in a regular grid pattern
        """
        if len(panels) < 4:
            return False
            
        # Group panels by Y coordinate
        y_groups = {}
        for panel in panels:
            y_coord = round(panel.center_coords[1], 1)
            if y_coord not in y_groups:
                y_groups[y_coord] = []
            y_groups[y_coord].append(panel)
        
        # Check if we have multiple panels per row (indicating a grid)
        rows_with_multiple_panels = sum(1 for row_panels in y_groups.values() if len(row_panels) > 1)
        total_rows = len(y_groups)
        
        # If more than 50% of rows have multiple panels, it's likely a grid
        return rows_with_multiple_panels > total_rows * 0.5

    def _sort_panels_by_proximity(self, panels: List[PanelSpecs]) -> List[PanelSpecs]:
        """
        Sort panels by proximity to create organized strings
        Uses improved algorithm that avoids diagonal jumps and considers local neighborhoods
        """
        if not panels:
            return panels
            
        # Try different starting points and choose the best one
        best_ordering = None
        best_score = float('inf')
        
        # Test different starting points
        starting_points = [
            ("top-right", lambda p: (p.center_coords[1], p.center_coords[0])),
            ("top-left", lambda p: (p.center_coords[1], -p.center_coords[0])),
            ("bottom-right", lambda p: (-p.center_coords[1], p.center_coords[0])),
            ("bottom-left", lambda p: (-p.center_coords[1], -p.center_coords[0])),
            ("center", lambda p: (0, 0))  # Start from center
        ]
        
        for start_name, key_func in starting_points:
            ordering = self._create_proximity_ordering(panels, key_func)
            score = self._calculate_ordering_score(ordering)
            
            if score < best_score:
                best_score = score
                best_ordering = ordering
        
        return best_ordering
    
    def _create_proximity_ordering(self, panels: List[PanelSpecs], start_key_func) -> List[PanelSpecs]:
        """Create proximity ordering starting from a specific point"""
        sorted_panels = []
        remaining_panels = panels.copy()
        
        # Find the starting panel
        start_panel = max(remaining_panels, key=start_key_func)
        sorted_panels.append(start_panel)
        remaining_panels.remove(start_panel)
        
        # Improved proximity algorithm that avoids diagonal jumps
        while remaining_panels:
            last_panel = sorted_panels[-1]
            
            # Find the best next panel considering both distance and direction
            best_panel = None
            best_score = float('inf')
            
            for panel in remaining_panels:
                # Calculate distance
                x1, y1 = last_panel.center_coords
                x2, y2 = panel.center_coords
                distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                
                # Calculate direction score (prefer horizontal/vertical over diagonal)
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                direction_penalty = 0
                
                # Penalize diagonal moves (when both dx and dy are significant)
                if dx > 20 and dy > 20:
                    direction_penalty = 50  # Heavy penalty for diagonal moves
                elif dx > 10 and dy > 10:
                    direction_penalty = 20  # Medium penalty for moderate diagonals
                
                # Prefer panels that are closer horizontally or vertically
                if dx < 30 and dy < 30:  # Local neighborhood
                    direction_penalty -= 10  # Bonus for local moves
                
                # Combined score
                score = distance + direction_penalty
                
                if score < best_score:
                    best_score = score
                    best_panel = panel
            
            if best_panel:
                sorted_panels.append(best_panel)
                remaining_panels.remove(best_panel)
            else:
                # Fallback to simple closest if no good option
                closest_panel = min(remaining_panels, 
                                  key=lambda p: ((p.center_coords[0] - last_panel.center_coords[0])**2 + 
                                               (p.center_coords[1] - last_panel.center_coords[1])**2)**0.5)
                sorted_panels.append(closest_panel)
                remaining_panels.remove(closest_panel)
        
        return sorted_panels
    
    def _calculate_ordering_score(self, ordering: List[PanelSpecs]) -> float:
        """Calculate a score for the ordering (lower is better)"""
        if len(ordering) < 2:
            return 0.0
        
        total_score = 0.0
        max_distance = 0.0
        
        for i in range(len(ordering) - 1):
            p1 = ordering[i]
            p2 = ordering[i + 1]
            x1, y1 = p1.center_coords
            x2, y2 = p2.center_coords
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            
            # Calculate direction penalty
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            direction_penalty = 0
            
            if dx > 20 and dy > 20:
                direction_penalty = 50
            elif dx > 10 and dy > 10:
                direction_penalty = 20
            
            if dx < 30 and dy < 30:
                direction_penalty -= 10
            
            step_score = distance + direction_penalty
            total_score += step_score
            max_distance = max(max_distance, distance)
        
        # Penalize orderings with very large jumps
        return total_score + (max_distance * 2)

    def _verify_string_distances(self, string_panels: List[PanelSpecs], string_number: int):
        """
        Verify that a string has reasonable distances between consecutive panels
        """
        if len(string_panels) < 2:
            return
            
        max_jump_distance = 0
        total_distance = 0
        
        for i in range(len(string_panels) - 1):
            panel1 = string_panels[i]
            panel2 = string_panels[i + 1]
            
            # Calculate distance between consecutive panels
            x1, y1 = panel1.center_coords
            x2, y2 = panel2.center_coords
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            
            if distance > max_jump_distance:
                max_jump_distance = distance
            total_distance += distance
        
        avg_distance = total_distance / (len(string_panels) - 1) if len(string_panels) > 1 else 0
        
        print(f"      ✅ String {string_number}: max jump {max_jump_distance:.1f}, avg {avg_distance:.1f}")

    def _organize_string_snake_pattern(self, string_panels: List[PanelSpecs]) -> List[PanelSpecs]:
        """
        Organize panels within a string to follow snake pattern locally
        This ensures no big jumps within the string
        """
        if len(string_panels) <= 1:
            return string_panels
            
        # Group panels by Y coordinate (rows) within this string
        rows = {}
        for panel in string_panels:
            y_coord = panel.center_coords[1]
            if y_coord not in rows:
                rows[y_coord] = []
            rows[y_coord].append(panel)
        
        # Sort rows by Y coordinate (top to bottom)
        sorted_rows = sorted(rows.items(), key=lambda x: x[0], reverse=True)
        
        # Apply snake pattern within this string
        organized_panels = []
        for i, (y_coord, row_panels) in enumerate(sorted_rows):
            # Sort panels in row by X coordinate
            row_panels.sort(key=lambda p: p.center_coords[0])
            
            # Apply snake pattern: alternate direction for each row
            if i % 2 == 0:
                # Even rows: Left → Right
                organized_panels.extend(row_panels)
            else:
                # Odd rows: Right → Left
                organized_panels.extend(reversed(row_panels))
        
        return organized_panels

    def _verify_snake_pattern_string(self, string_panels: List[PanelSpecs], string_number: int):
        """
        Verify that a string follows snake pattern (no big jumps between consecutive panels)
        """
        if len(string_panels) < 2:
            return
            
        max_jump_distance = 0
        problematic_jumps = []
        
        for i in range(len(string_panels) - 1):
            panel1 = string_panels[i]
            panel2 = string_panels[i + 1]
            
            # Calculate distance between consecutive panels
            x1, y1 = panel1.center_coords
            x2, y2 = panel2.center_coords
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            
            if distance > max_jump_distance:
                max_jump_distance = distance
                
            # Check for problematic jumps (distance > 2x panel spacing)
            if distance > 100:  # Assuming panel spacing is ~50 units
                problematic_jumps.append({
                    'from': panel1.panel_id,
                    'to': panel2.panel_id,
                    'distance': distance,
                    'positions': [(x1, y1), (x2, y2)]
                })
        
        if problematic_jumps:
            print(f"      ⚠️  String {string_number} has {len(problematic_jumps)} big jumps:")
            for jump in problematic_jumps:
                print(f"        {jump['from']} → {jump['to']}: {jump['distance']:.1f} units")
        else:
            print(f"      ✅ String {string_number} follows snake pattern (max jump: {max_jump_distance:.1f})")

    def _sort_panels_snake_pattern(self, panels: List[PanelSpecs]) -> List[PanelSpecs]:
        """
        Sort panels in true snake pattern: 
        - Row 1: Left → Right (ends at right edge)
        - Row 2: Right → Left (starts at right edge, ends at left edge)
        - Row 3: Left → Right (starts at left edge, ends at right edge)
        - And so on...
        """
        if not panels:
            return panels
            
        # Group panels by Y coordinate (rows)
        rows = {}
        for panel in panels:
            y_coord = panel.center_coords[1]
            if y_coord not in rows:
                rows[y_coord] = []
            rows[y_coord].append(panel)
        
        # Sort rows by Y coordinate (top to bottom)
        sorted_rows = sorted(rows.items(), key=lambda x: x[0], reverse=True)  # Reverse for top to bottom
        
        # Sort panels within each row and apply true snake pattern
        sorted_panels = []
        for i, (y_coord, row_panels) in enumerate(sorted_rows):
            # Sort panels in row by X coordinate (left to right)
            row_panels.sort(key=lambda p: p.center_coords[0])
            
            # Apply true snake pattern: alternate direction for each row
            if i % 2 == 0:
                # Even rows (0, 2, 4...): Left → Right
                sorted_panels.extend(row_panels)
            else:
                # Odd rows (1, 3, 5...): Right → Left (reverse the sorted order)
                sorted_panels.extend(reversed(row_panels))
        
        return sorted_panels
    
    def _handle_remainder_with_modulus(self, panels: List[PanelSpecs], ideal_info: Dict) -> Tuple[List[Dict], List[PanelSpecs]]:
        """
        Recursively handle remainder panels using modulus approach
        """
        strings = []
        stragglers = []
        panel_count = len(panels)
        
        if panel_count == 0:
            return strings, stragglers
        
        min_panels = ideal_info['min_panels']
        max_panels = ideal_info['max_panels']
        
        # Try to create strings of decreasing size
        for string_length in range(max_panels, min_panels - 1, -1):
            if panel_count >= string_length:
                num_strings = panel_count // string_length
                remainder = panel_count % string_length
                
                if num_strings > 0:
                    print(f"        Creating {num_strings} strings of length {string_length}, remainder: {remainder}")
                    
                    # Create strings of this length
                    panel_index = 0
                    for i in range(num_strings):
                        string_panels = panels[panel_index:panel_index + string_length]
                        string_data = {
                            'length': string_length,
                            'panels': [p.panel_id for p in string_panels],
                            'roof_plane': panels[0].roof_plane_id,
                            'type': f'modulus_{string_length}'
                        }
                        strings.append(string_data)
                        panel_index += string_length
                    
                    # Handle remaining panels recursively
                    if remainder > 0:
                        remaining_panels = panels[panel_index:]
                        if remainder >= min_panels:
                            # Can create one more string
                            string_data = {
                                'length': remainder,
                                'panels': [p.panel_id for p in remaining_panels],
                                'roof_plane': panels[0].roof_plane_id,
                                'type': f'modulus_remainder_{remainder}'
                            }
                            strings.append(string_data)
                        else:
                            # Not enough for a valid string - these are stragglers
                            stragglers.extend(remaining_panels)
                            print(f"        {remainder} panels become stragglers")
                    
                    break  # We've handled all panels
        
        # If we couldn't create any valid strings, all panels are stragglers
        if not strings and panel_count > 0:
            stragglers.extend(panels)
            print(f"        All {panel_count} panels become stragglers")
        
        return strings, stragglers
    
    def _balance_string_lengths(self, strings: List[Dict], ideal_length: int) -> List[Dict]:
        """
        Balance string lengths within a roof section by partitioning long strings
        to help short strings (stragglers), using percentage-based approach
        """
        if not strings:
            return strings
        
        # Identify short strings (less than 50% of ideal) and long strings
        short_strings = []
        long_strings = []
        balanced_strings = []
        
        for string_data in strings:
            length = string_data['length']
            if length < ideal_length * 0.5:  # Less than 50% of ideal
                short_strings.append(string_data)
            elif length >= ideal_length:  # Long strings (ideal length or more)
                long_strings.append(string_data)
            else:
                balanced_strings.append(string_data)
        
        if not short_strings or not long_strings:
            return strings  # No balancing needed
        
        print(f"      Load balancing: {len(short_strings)} short strings, {len(long_strings)} long strings")
        
        # Try to help short strings by partitioning CONTIGUOUS long strings
        for short_string in short_strings:
            if not long_strings:
                break
                
            short_length = short_string['length']
            
            # Calculate target lengths using percentages
            # Target: split long string into two parts, one to combine with short string
            # Aim for 50% of ideal length for each part
            target_length = int(ideal_length * 0.5)  # 50% of ideal (e.g., 4-5 for ideal 9)
            
            # Find the best CONTIGUOUS long string to partition
            best_long_string = None
            best_partition_point = None
            best_balance_score = float('inf')
            
            # Get short string panel positions for proximity calculation
            short_panel_positions = []
            for panel_id in short_string['panels']:
                panel_data = next((p for p in self.panel_specs if p.panel_id == panel_id), None)
                if panel_data:
                    short_panel_positions.append(panel_data.center_coords)
            
            for long_string in long_strings:
                long_length = long_string['length']
                if long_length >= target_length + 3:  # Ensure we can partition meaningfully
                    
                    # Calculate proximity score between short string and long string
                    proximity_score = self._calculate_proximity_score(short_panel_positions, long_string['panels'])
                    
                    # Try different partition points to get target length
                    for partition_point in range(3, long_length - 3):
                        first_part_length = partition_point
                        second_part_length = long_length - partition_point
                        
                        # Calculate balance score (lower is better)
                        score = 0
                        
                        # Penalize very short strings
                        if first_part_length < 3:
                            score += 100
                        if second_part_length < 3:
                            score += 100
                        
                        # Bonus for getting close to target length (50% of ideal)
                        score += abs(first_part_length - target_length) + abs(second_part_length - target_length)
                        
                        # Bonus for balanced lengths (both parts similar)
                        length_diff = abs(first_part_length - second_part_length)
                        score += length_diff * 0.5
                        
                        # HEAVILY prioritize contiguous strings (lower proximity score = better)
                        score += proximity_score * 10  # High weight for proximity
                        
                        if score < best_balance_score:
                            best_balance_score = score
                            best_long_string = long_string
                            best_partition_point = partition_point
            
            if best_long_string and best_partition_point:
                # Partition the long string
                long_panels = best_long_string['panels']
                first_part_panels = long_panels[:best_partition_point]
                second_part_panels = long_panels[best_partition_point:]
                
                # Combine short string with first part
                combined_panels = short_string['panels'] + first_part_panels
                combined_string = {
                    'length': len(combined_panels),
                    'panels': combined_panels,
                    'roof_plane': short_string['roof_plane'],
                    'type': 'balanced_combined'
                }
                
                # Create second string from remaining part
                second_string = {
                    'length': len(second_part_panels),
                    'panels': second_part_panels,
                    'roof_plane': best_long_string['roof_plane'],
                    'type': 'balanced_partition'
                }
                
                balanced_strings.extend([combined_string, second_string])
                long_strings.remove(best_long_string)
                
                print(f"        Combined {short_string['length']}-panel string with {len(first_part_panels)} panels from {best_long_string['length']}-panel string")
                print(f"        Result: {len(combined_panels)} + {len(second_part_panels)} panels")
            else:
                # Keep the short string as is if no good combination found
                balanced_strings.append(short_string)
        
        # Add remaining long strings
        balanced_strings.extend(long_strings)
        
        return balanced_strings

    def _calculate_proximity_score(self, short_panel_positions: List[Tuple[float, float]], long_string_panel_ids: List[str]) -> float:
        """
        Calculate proximity score between short string panels and long string panels
        Lower score = closer proximity (better for contiguous strings)
        """
        if not short_panel_positions or not long_string_panel_ids:
            return float('inf')
        
        # Get positions of long string panels
        long_panel_positions = []
        for panel_id in long_string_panel_ids:
            panel_data = next((p for p in self.panel_specs if p.panel_id == panel_id), None)
            if panel_data:
                long_panel_positions.append(panel_data.center_coords)
        
        if not long_panel_positions:
            return float('inf')
        
        # Calculate minimum distance between any panel in short string and any panel in long string
        min_distance = float('inf')
        for short_pos in short_panel_positions:
            for long_pos in long_panel_positions:
                distance = ((short_pos[0] - long_pos[0])**2 + (short_pos[1] - long_pos[1])**2)**0.5
                min_distance = min(min_distance, distance)
        
        return min_distance

    def _apply_final_load_balancing(self, connections: Dict) -> Dict:
        """
        Apply load balancing across all strings from all roof sections
        """
        # Extract all strings from connections
        all_strings = []
        string_to_location = {}  # Track which roof/inverter/mppt each string belongs to
        
        for roof_plane, inverters in connections.items():
            for inverter_id, mppts in inverters.items():
                for mppt_id, panel_ids in mppts.items():
                    if len(panel_ids) > 0:
                        string_data = {
                            'length': len(panel_ids),
                            'panels': panel_ids,
                            'roof_plane': roof_plane,
                            'type': 'existing'
                        }
                        all_strings.append(string_data)
                        string_to_location[len(all_strings) - 1] = (roof_plane, inverter_id, mppt_id)
        
        if len(all_strings) < 2:
            return connections  # No balancing needed
        
        # Apply load balancing
        ideal_length = 9  # Based on the optimization
        balanced_strings = self._balance_string_lengths(all_strings, ideal_length)
        
        if len(balanced_strings) != len(all_strings):
            print(f"      Load balancing: {len(all_strings)} → {len(balanced_strings)} strings")
            
            # Rebuild connections with balanced strings
            new_connections = {}
            string_index = 0
            
            for roof_plane, inverters in connections.items():
                new_connections[roof_plane] = {}
                for inverter_id, mppts in inverters.items():
                    new_connections[roof_plane][inverter_id] = {}
                    for mppt_id, panel_ids in mppts.items():
                        if len(panel_ids) > 0:
                            if string_index < len(balanced_strings):
                                new_connections[roof_plane][inverter_id][mppt_id] = balanced_strings[string_index]['panels']
                                string_index += 1
                            else:
                                new_connections[roof_plane][inverter_id][mppt_id] = panel_ids
            
            return new_connections
        
        return connections

    def _handle_stragglers(self, stragglers: List[PanelSpecs], existing_strings: List[Dict]) -> List[Dict]:
        """
        Handle stragglers by connecting them to closest available inverters
        """
        if not stragglers:
            return []
        
        straggler_strings = []
        
        # Group stragglers by roof plane
        stragglers_by_roof = {}
        for panel in stragglers:
            roof_id = panel.roof_plane_id
            if roof_id not in stragglers_by_roof:
                stragglers_by_roof[roof_id] = []
            stragglers_by_roof[roof_id].append(panel)
        
        # Process each roof plane's stragglers
        for roof_id, roof_stragglers in stragglers_by_roof.items():
            print(f"      Processing {len(roof_stragglers)} stragglers from roof {roof_id}")
            
            # Try to create valid strings from stragglers within the same roof
            min_panels = 3  # Minimum for a valid string
            max_panels = 9  # Maximum for a string
            
            # Sort stragglers by position for better organization
            roof_stragglers.sort(key=lambda p: (p.center_coords[1], p.center_coords[0]))
            
            # Create strings from stragglers
            panel_index = 0
            while panel_index < len(roof_stragglers):
                remaining_count = len(roof_stragglers) - panel_index
                
                if remaining_count >= min_panels:
                    # Create a string with available panels
                    string_length = min(remaining_count, max_panels)
                    string_panels = roof_stragglers[panel_index:panel_index + string_length]
                    
                    string_data = {
                        'length': string_length,
                        'panels': [p.panel_id for p in string_panels],
                        'roof_plane': roof_id,
                        'type': 'straggler_string'
                    }
                    straggler_strings.append(string_data)
                    panel_index += string_length
                else:
                    # Not enough for a valid string - try to create 2-panel strings
                    individual_stragglers = roof_stragglers[panel_index:]
                    
                    # Try to pair up individual stragglers
                    for i in range(0, len(individual_stragglers), 2):
                        if i + 1 < len(individual_stragglers):
                            # Create a 2-panel string
                            string_data = {
                                'length': 2,
                                'panels': [individual_stragglers[i].panel_id, individual_stragglers[i+1].panel_id],
                                'roof_plane': roof_id,
                                'type': 'straggler_pair'
                            }
                            straggler_strings.append(string_data)
                        else:
                            # Single remaining panel - try to connect to closest panel in same roof
                            single_panel = individual_stragglers[i]
                            all_roof_panels = [p for p in self.panel_specs if p.roof_plane_id == roof_id and p.panel_id != single_panel.panel_id]
                            
                            if all_roof_panels:
                                # Find closest panel
                                closest_panel = min(all_roof_panels, 
                                                  key=lambda p: ((p.center_coords[0] - single_panel.center_coords[0])**2 + 
                                                               (p.center_coords[1] - single_panel.center_coords[1])**2)**0.5)
                                
                                # Create a 2-panel string
                                string_data = {
                                    'length': 2,
                                    'panels': [single_panel.panel_id, closest_panel.panel_id],
                                    'roof_plane': roof_id,
                                    'type': 'straggler_connected'
                                }
                                straggler_strings.append(string_data)
                            else:
                                # Fallback to single panel
                                string_data = {
                                    'length': 1,
                                    'panels': [single_panel.panel_id],
                                    'roof_plane': roof_id,
                                    'type': 'single_panel'
                                }
                                straggler_strings.append(string_data)
                    break
        
        return straggler_strings
    
    def _create_simple_strings(self, panels: List[PanelSpecs], ideal_length: int, ideal_info: Dict) -> List[Dict]:
        """
        Create strings using simple sequential approach for smaller groups
        """
        strings = []
        panel_count = len(panels)
        
        # Create as many ideal strings as possible
        num_ideal_strings = panel_count // ideal_length
        leftover_panels = panel_count % ideal_length
        
        panel_index = 0
        
        # Create ideal strings
        for i in range(num_ideal_strings):
            string_panels = panels[panel_index:panel_index + ideal_length]
            string_data = {
                'length': ideal_length,
                'panels': [p.panel_id for p in string_panels],
                'roof_plane': panels[0].roof_plane_id,
                'type': 'simple_ideal'
            }
            strings.append(string_data)
            panel_index += ideal_length
        
        # Handle leftover panels
        if leftover_panels >= ideal_info['min_panels']:
            # Can form a valid string with leftovers
            string_panels = panels[panel_index:panel_index + leftover_panels]
            string_data = {
                'length': leftover_panels,
                'panels': [p.panel_id for p in string_panels],
                'roof_plane': panels[0].roof_plane_id,
                'type': 'simple_leftover'
            }
            strings.append(string_data)
        elif leftover_panels > 0:
            # Not enough for a valid string - add to unassigned
            print(f"    Warning: {leftover_panels} panels cannot form valid string")
            # For now, we'll create a string anyway (this could be improved)
            string_panels = panels[panel_index:panel_index + leftover_panels]
            string_data = {
                'length': leftover_panels,
                'panels': [p.panel_id for p in string_panels],
                'roof_plane': panels[0].roof_plane_id,
                'type': 'simple_invalid'
            }
            strings.append(string_data)
        
        return strings
    
    def _find_next_seed(self, panels: List[PanelSpecs]) -> Optional[PanelSpecs]:
        """
        Find the next unassigned panel to use as a seed (top-left most)
        """
        unassigned = [p for p in panels if not getattr(p, 'is_assigned', False)]
        if not unassigned:
            return None
        
        # Sort by y-coordinate first (top to bottom), then by x-coordinate (left to right)
        unassigned.sort(key=lambda p: (p.center_coords[1], p.center_coords[0]))
        return unassigned[0]
    
    def _grow_contiguous_string(self, seed_panel: PanelSpecs, all_panels: List[PanelSpecs], 
                               ideal_length: int, ideal_info: Dict) -> List[PanelSpecs]:
        """
        Grow a contiguous string from a seed panel using nearest neighbor approach
        """
        current_string = [seed_panel]
        last_panel = seed_panel
        
        # Grow the string to ideal length, but be more conservative
        target_length = min(ideal_length, ideal_info['max_panels'])
        
        for _ in range(target_length - 1):
            # Find the closest unassigned neighbor
            closest_panel = self._find_closest_unassigned_neighbor(last_panel, all_panels)
            if not closest_panel:
                break
            
            # Check if adding this panel would exceed max length
            if len(current_string) >= ideal_info['max_panels']:
                break
                
            current_string.append(closest_panel)
            last_panel = closest_panel
        
        return current_string
    
    def _find_closest_unassigned_neighbor(self, reference_panel: PanelSpecs, 
                                        all_panels: List[PanelSpecs]) -> Optional[PanelSpecs]:
        """
        Find the closest unassigned panel to the reference panel
        """
        unassigned = [p for p in all_panels if not getattr(p, 'is_assigned', False)]
        if not unassigned:
            return None
        
        min_distance = float('inf')
        closest_panel = None
        
        ref_x, ref_y = reference_panel.center_coords
        
        for panel in unassigned:
            panel_x, panel_y = panel.center_coords
            distance = ((panel_x - ref_x) ** 2 + (panel_y - ref_y) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_panel = panel
        
        return closest_panel
    
    def _calculate_temperature_adjusted_voltages(self) -> Dict[str, Dict[str, float]]:
        """
        Phase 1: Calculate temperature-adjusted panel voltages for each group
        Uses the linear functions from solar_cell_temperature_coefficients.py
        
        Returns:
            Dict mapping group_id -> {"max_voltage": float, "min_voltage": float}
        """
        temp_adjusted = {}
        
        # Choose temperature range based on temp_range parameter
        if self.temp_range == "extreme":
            cold_temp = self.temperature_data.min_temp_c
            hot_temp = self.temperature_data.max_temp_c + 20  # Add 20°C for cell heating above ambient
            temp_source = "extreme recorded temperatures"
        else:  # "average"
            cold_temp = self.temperature_data.avg_low_temp_c
            hot_temp = self.temperature_data.avg_high_temp_c + 20  # Add 20°C for cell heating
            temp_source = "average temperatures"
        
        print(f"  Using {temp_source} for calculations")
        print(f"    Cold temperature: {cold_temp}°C")
        print(f"    Hot temperature: {hot_temp}°C")
        
        for group_id, panels in self.panel_groups.items():
            # Use the first panel in the group as representative (assuming all panels in group are same type)
            representative_panel = panels[0]
            
            # Calculate max voltage (coldest day - safety calculation)
            # Use the linear function: Voc(T) = -0.286 * T + 107.143
            voc_normalized_cold = calculate_voc_normalized(cold_temp)
            max_voltage_per_panel = representative_panel.voc_stc * (voc_normalized_cold / 100.0)
            
            # Calculate min operating voltage (hottest day - performance calculation)
            # For Vmpp, we'll use a similar approach but with a different coefficient
            # Since Pmax = Vmpp × Impp, and we have Pmax function, we can estimate Vmpp
            # For simplicity, we'll use the same Voc function but with a slightly different slope
            # This is an approximation - in reality, Vmpp has its own temperature coefficient
            vmpp_normalized_hot = calculate_voc_normalized(hot_temp) * 0.95  # Approximate Vmpp as 95% of Voc
            min_voltage_per_panel = representative_panel.vmpp_stc * (vmpp_normalized_hot / 100.0)
            
            temp_adjusted[group_id] = {
                "max_voltage": max_voltage_per_panel,
                "min_voltage": min_voltage_per_panel,
                "panel_count": len(panels),
                "panel_specs": representative_panel,
                "cold_temp": cold_temp,
                "hot_temp": hot_temp
            }
            
            print(f"  Group {group_id}: {len(panels)} panels")
            print(f"    Max voltage per panel: {max_voltage_per_panel:.2f}V (coldest day: {cold_temp}°C)")
            print(f"    Min voltage per panel: {min_voltage_per_panel:.2f}V (hottest day: {hot_temp}°C)")
            print(f"    Voc normalized at cold: {voc_normalized_cold:.1f}%")
            print(f"    Vmpp normalized at hot: {vmpp_normalized_hot:.1f}%")
        
        return temp_adjusted
    
    def _generate_valid_string_plans(self, temp_adjusted: Dict[str, Dict[str, float]]) -> Dict[str, List[List[int]]]:
        """
        Phase 2: Generate all valid string combinations for each panel group
        
        Returns:
            Dict mapping group_id -> list of valid string length combinations
        """
        valid_plans = {}
        
        for group_id, group_data in temp_adjusted.items():
            group_start_time = time.time()
            panel_count = group_data["panel_count"]
            max_voltage = group_data["max_voltage"]
            min_voltage = group_data["min_voltage"]
            panel_specs = group_data["panel_specs"]
            
            print(f"  Processing Group {group_id}: {panel_count} panels")
            print(f"    Max voltage per panel: {max_voltage:.2f}V")
            print(f"    Min voltage per panel: {min_voltage:.2f}V")
            
            # Calculate valid string length range
            min_panels_per_string = math.ceil(self.inverter_specs.mppt_min_voltage / min_voltage)
            
            # Safety limit
            max_panels_safety = math.floor(self.inverter_specs.max_dc_voltage / max_voltage)
            # Operational limit  
            max_panels_operational = math.floor(self.inverter_specs.mppt_max_voltage / min_voltage)
            
            max_panels_per_string = min(max_panels_safety, max_panels_operational)
            
            print(f"  Group {group_id}: {panel_count} panels")
            print(f"    Valid string length range: [{min_panels_per_string}, {max_panels_per_string}]")
            
            # Generate all valid combinations
            print(f"    Generating string combinations for {panel_count} panels...")
            combination_start = time.time()
            valid_combinations = self._find_string_combinations(
                panel_count, min_panels_per_string, max_panels_per_string
            )
            combination_time = time.time() - combination_start
            print(f"    Found {len(valid_combinations)} valid string combinations in {combination_time:.2f} seconds")
            
            valid_plans[group_id] = valid_combinations
            group_time = time.time() - group_start_time
            print(f"  Group {group_id} completed in {group_time:.2f} seconds")
        
        return valid_plans
    
    def _find_string_combinations(self, total_panels: int, min_per_string: int, max_per_string: int) -> List[List[int]]:
        """
        Find all valid ways to combine string lengths to use exactly total_panels
        """
        combinations = []
        call_count = 0
        
        def backtrack(remaining_panels: int, current_combination: List[int]):
            nonlocal call_count
            call_count += 1
            
            # Log progress every 1000 calls for large systems
            if call_count % 1000 == 0:
                print(f"      Backtracking: {call_count} calls, {len(combinations)} combinations found so far...")
            
            if remaining_panels == 0:
                combinations.append(current_combination.copy())
                return
            
            for string_length in range(min_per_string, min(max_per_string + 1, remaining_panels + 1)):
                if remaining_panels >= string_length:
                    current_combination.append(string_length)
                    backtrack(remaining_panels - string_length, current_combination)
                    current_combination.pop()
        
        print(f"    Starting backtracking algorithm for {total_panels} panels...")
        backtrack(total_panels, [])
        print(f"    Backtracking completed: {call_count} total calls, {len(combinations)} combinations found")
        return combinations
    
    def _optimize_mppt_assignments(self, valid_string_plans: Dict[str, List[List[int]]]) -> StringingPlan:
        """
        Phase 3: Find the optimal MPPT assignment across all possible stringing plans
        """
        best_plan = None
        min_mppts_used = float('inf')
        
        # Generate all possible complete plans (one stringing option per group)
        print(f"  Generating complete stringing plans...")
        plan_generation_start = time.time()
        complete_plans = self._generate_complete_plans(valid_string_plans)
        plan_generation_time = time.time() - plan_generation_start
        print(f"  Generated {len(complete_plans)} complete stringing plans in {plan_generation_time:.2f} seconds")
        
        print(f"  Evaluating {len(complete_plans)} complete stringing plans...")
        evaluation_start = time.time()
        
        best_connections = None
        for i, plan in enumerate(complete_plans):
            if i % 100 == 0 and i > 0:
                print(f"    Evaluated {i}/{len(complete_plans)} plans...")
            
            mppts_used, connections = self._calculate_mppts_for_plan(plan)
            
            if mppts_used < min_mppts_used:
                min_mppts_used = mppts_used
                best_plan = plan
                best_connections = connections
        
        evaluation_time = time.time() - evaluation_start
        print(f"  Plan evaluation completed in {evaluation_time:.2f} seconds")
        
        return StringingPlan(
            group_plans=best_plan,
            total_mppts_used=min_mppts_used,
            configuration=self._build_detailed_configuration(best_plan),
            connections=best_connections
        )
    
    def _generate_complete_plans(self, valid_string_plans: Dict[str, List[List[int]]]) -> List[Dict[str, List[int]]]:
        """Generate all possible complete stringing plans"""
        group_names = list(valid_string_plans.keys())
        complete_plans = []
        
        def generate_combinations(group_index: int, current_plan: Dict[str, List[int]]):
            if group_index == len(group_names):
                complete_plans.append(current_plan.copy())
                return
            
            group_name = group_names[group_index]
            for string_combination in valid_string_plans[group_name]:
                current_plan[group_name] = string_combination
                generate_combinations(group_index + 1, current_plan)
        
        generate_combinations(0, {})
        return complete_plans
    
    def _calculate_mppts_for_plan(self, plan: Dict[str, List[int]]) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate how many MPPTs are needed for a given stringing plan and return detailed connections
        """
        # Create master list of all strings with panel assignments
        all_strings_with_panels = []
        for group_name, string_lengths in plan.items():
            group_panels = self.panel_groups[group_name]
            panel_index = 0
            
            for string_length in string_lengths:
                # Get the actual panel IDs for this string
                string_panels = [group_panels[i].panel_id for i in range(panel_index, panel_index + string_length)]
                all_strings_with_panels.append({
                    'length': string_length,
                    'panels': string_panels,
                    'roof_plane': group_name
                })
                panel_index += string_length
        
        # Sort strings by length (for better parallel matching)
        all_strings_with_panels.sort(key=lambda x: x['length'], reverse=True)
        
        # Simulate MPPT assignment with detailed tracking
        mppts = []  # List of MPPTs, each containing connection details
        total_inverters_needed = 1  # Start with one inverter
        connections = {}  # Detailed connection plan
        
        for string_data in all_strings_with_panels:
            string_length = string_data['length']
            string_panels = string_data['panels']
            roof_plane = string_data['roof_plane']
            
            # First, look for parallel opportunity in existing MPPTs
            parallel_found = False
            for mppt_index, mppt in enumerate(mppts):
                # Check if this MPPT has strings of the same length
                same_length_strings = [s for s in mppt if s['length'] == string_length]
                if same_length_strings:
                    # Check if we can add another string of same length
                    current_strings_of_length = len(same_length_strings)
                    max_current = self.inverter_specs.max_dc_current_per_mppt
                    
                    # Estimate current (simplified - using Isc)
                    panel_isc = self.panel_specs[0].isc_stc  # Assuming all panels have same Isc
                    if (current_strings_of_length + 1) * panel_isc <= max_current:
                        # Add this string to the existing MPPT
                        mppt.append(string_data)
                        parallel_found = True
                        break
            
            # If no parallel opportunity, need a new MPPT
            if not parallel_found:
                # Check if we have available MPPTs in current inverter
                available_mppts = (total_inverters_needed * self.inverter_specs.number_of_mppts) - len(mppts)
                
                if available_mppts > 0:
                    # Use available MPPT in current inverter
                    mppts.append([string_data])
                else:
                    # Need a new inverter
                    total_inverters_needed += 1
                    mppts.append([string_data])
        
        # Build detailed connections structure with unique global identifiers
        for mppt_index, mppt in enumerate(mppts):
            inverter_num = (mppt_index // self.inverter_specs.number_of_mppts) + 1
            mppt_num = (mppt_index % self.inverter_specs.number_of_mppts) + 1
            
            # Create unique global identifiers
            global_inverter_id = f"Inverter_{inverter_num}"
            global_mppt_id = f"MPPT_{inverter_num}_{mppt_num}"
            
            # Group strings by roof plane within this MPPT
            roof_plane_strings = {}
            for string_data in mppt:
                roof_plane = string_data['roof_plane']
                if roof_plane not in roof_plane_strings:
                    roof_plane_strings[roof_plane] = []
                roof_plane_strings[roof_plane].extend(string_data['panels'])
            
            # Add to connections structure
            for roof_plane, panel_ids in roof_plane_strings.items():
                if roof_plane not in connections:
                    connections[roof_plane] = {}
                
                if global_inverter_id not in connections[roof_plane]:
                    connections[roof_plane][global_inverter_id] = {}
                
                connections[roof_plane][global_inverter_id][global_mppt_id] = panel_ids
        
        # Store the total inverters needed for reporting
        self._total_inverters_needed = total_inverters_needed
        
        return len(mppts), connections
    
    def _build_detailed_configuration(self, plan: Dict[str, List[int]]) -> Dict[str, Any]:
        """Build detailed configuration for the optimal plan"""
        # This would contain the full MPPT assignment details
        # For now, return a simplified structure
        return {
            "plan": plan,
            "mppt_assignments": "Detailed assignments would go here"
        }
    
    def _format_final_configuration(self, optimal_plan: StringingPlan) -> Dict[str, Any]:
        """
        Phase 4: Format the final configuration output
        """
        total_inverters = getattr(self, '_total_inverters_needed', 1)
        
        return {
            "summary": {
                "total_inverters": total_inverters,
                "total_mppts_used": optimal_plan.total_mppts_used,
                "total_panels": sum(len(panels) for panels in self.panel_groups.values()),
                "inverters_needed": "Multiple inverters required" if total_inverters > 1 else "Single inverter sufficient"
            },
            "group_plans": optimal_plan.group_plans,
            "connections": optimal_plan.connections,
            "configuration": optimal_plan.configuration
        }


def main():
    """Example usage of the SolarStringingOptimizer"""
    print("Solar Stringing Optimizer - Example Usage")
    print("=" * 50)
    
    # This would be populated from actual data files
    # For now, showing the structure
    print("To use this optimizer:")
    print("1. Load panel specs from auto-design.json and panel_specs.csv")
    print("2. Load inverter specs from inverter_specs.csv") 
    print("3. Load temperature data from consolidated_temperature_data.csv")
    print("4. Create optimizer instance and call optimize()")
    print("5. Get the optimal stringing configuration")


if __name__ == "__main__":
    main()
