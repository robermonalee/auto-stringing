# Solar Panel Stringing Optimizer

A comprehensive Python-based system for optimizing solar panel stringing configurations based on temperature-adjusted voltages and inverter constraints. This implementation follows a complete end-to-end process from initial calculations to final output, with clear decision points for parallel connections.

## 🚀 Features

- **Temperature-Adjusted Calculations**: Uses linear functions from `solar_cell_temperature_coefficients.py` to calculate panel voltages at extreme temperatures
- **Multi-Phase Optimization**: Implements the complete 4-phase optimization process
- **Parallel Connection Logic**: Automatically determines optimal series and parallel connections
- **Real Data Integration**: Works with actual solar design data from `auto-design.json`
- **Comprehensive Output**: Generates detailed JSON configuration with system specifications
- **Heuristic Algorithm**: Fast greedy optimization for large systems (>12 panels)
- **Visualization Support**: Panel layout and stringing connection visualization
- **AWS Deployment Ready**: Minimal dependencies for cloud deployment

## 📁 Project Structure

```
auto-stringing/
├── main_optimizer.py                    # Main entry point and orchestrator
├── solar_stringing_optimizer.py         # Core optimization algorithm
├── data_parsers.py                      # Data loading and parsing utilities
├── solar_cell_temperature_coefficients.py # Linear temperature functions
├── auto_design_reference.txt            # Reference guide for auto-design.json
├── auto-design.json                     # Solar system design data
├── panel_specs.csv                      # Panel specifications
├── inverter_specs.csv                   # Inverter specifications
├── amb_temperature_data.csv             # Temperature data by state
└── results.json                         # Output configuration
```

## 🔧 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/robermonalee/auto-stringing.git
   cd auto-stringing
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install pandas
   ```

## 🎯 Usage

### Command Line Interface

```bash
python main_optimizer.py <auto_design.json> <panel_specs.csv> <inverter_specs.csv> <temperature_data.csv> <state_name> [output.json]
```

### Example

```bash
python main_optimizer.py auto-design.json panel_specs.csv inverter_specs.csv amb_temperature_data.csv California results.json
```

### Programmatic Usage

```python
from main_optimizer import run_optimization

# Run optimization
config = run_optimization(
    auto_design_path="auto-design.json",
    panel_specs_path="panel_specs.csv", 
    inverter_specs_path="inverter_specs.csv",
    temperature_data_path="amb_temperature_data.csv",
    state_name="California",
    output_path="results.json"
)

# Print summary
from main_optimizer import print_results_summary
print_results_summary(config)
```

## 🔬 Algorithm Overview

The optimizer implements a 4-phase process:

### Phase 1: Pre-Computation and Temperature Adjustment
- Calculates maximum panel voltage (coldest day) using linear function: `Voc(T) = -0.286 * T + 107.143`
- Calculates minimum operating voltage (hottest day) for performance
- Uses site-specific temperature extremes from state data

### Phase 2: String Generation
- Determines valid string length ranges based on inverter constraints
- Generates all possible string combinations for each roof plane group
- Ensures safety limits and operational requirements are met

### Phase 3: MPPT Optimization
- Evaluates all possible stringing plans
- Assigns strings to MPPTs with parallel connection logic
- Optimizes for minimum MPPT usage

### Phase 4: Output Generation
- Formats optimal configuration into structured JSON
- Includes system specifications and temperature conditions
- Provides detailed stringing plan by roof plane

## 📊 Input Data Requirements

### auto-design.json
Contains solar system design information:
- `solar_panels`: Array of panel objects with pixel coordinates and roof plane assignments
- `roof_planes`: Roof plane definitions with polygon boundaries
- Panel center coordinates (`c0`) used for stringing analysis

### panel_specs.csv
Panel specifications including:
- `voc (V)`: Open-circuit voltage at STC
- `isc (A)`: Short-circuit current at STC  
- `vmp (V)`: Maximum power point voltage at STC
- `imp (A)`: Maximum power point current at STC

### inverter_specs.csv
Inverter specifications including:
- `maxDCInputVoltage (V)`: Maximum DC input voltage
- `numberOfMPPTs`: Number of available MPPTs
- `mpptOperatingVoltageMinRange (V)`: Minimum MPPT voltage
- `mpptOperatingVoltageMaxRange (V)`: Maximum MPPT voltage
- `maxDCInputCurrentPerMPPT (A)`: Maximum current per MPPT

### amb_temperature_data.csv
Temperature data by state:
- `Min_Recorded_Temperature_Celsius`: Record low temperature
- `Max_Recorded_Temperature_Celsius`: Record high temperature

## 📈 Output Format

The optimizer generates a comprehensive JSON output:

```json
{
  "summary": {
    "total_inverters": 1,
    "total_mppts_used": 2,
    "total_panels": 11
  },
  "group_plans": {
    "1": [3, 8]
  },
  "system_details": {
    "inverter_specifications": {
      "model": "Huawei SUN2000-2KTL-L1",
      "max_dc_voltage": 600.0,
      "mppt_voltage_range": "90.0V - 560.0V",
      "number_of_mppts": 2
    },
    "temperature_conditions": {
      "min_recorded_temp": "-42.8°C",
      "max_recorded_temp": "56.7°C",
      "state": "California"
    },
    "panel_specifications": {
      "total_panels": 11,
      "voc_stc": "52.79V",
      "isc_stc": "14.19A",
      "temperature_functions": "Using linear functions from solar_cell_temperature_coefficients.py"
    }
  }
}
```

## 🌡️ Temperature Functions

The system uses linear functions from `solar_cell_temperature_coefficients.py`:

- **Voc**: `Voc(T) = -0.286 * T + 107.143` (coefficient = -0.286%/°C)
- **Isc**: `Isc(T) = 0.02 * T + 99.5` (coefficient = 0.02%/°C)  
- **Pmax**: `Pmax(T) = -0.333 * T + 108.333` (coefficient = -0.333%/°C)

These functions are based on actual solar cell temperature dependence data and provide more accurate modeling than traditional temperature coefficients.

## 🔍 Key Features

### Parallel Connection Logic
The optimizer automatically determines when to use parallel connections:
- First looks for existing MPPTs with strings of the same length
- Checks current limits before adding parallel strings
- Falls back to empty MPPTs or new inverters as needed

### Safety Calculations
- Uses record low temperatures for maximum voltage calculations (safety)
- Uses realistic high operating temperatures for minimum voltage calculations (performance)
- Ensures all configurations stay within inverter safety limits

### Optimization Strategy
- Minimizes total MPPT usage for cost efficiency
- Considers all possible stringing combinations
- Balances series and parallel connections optimally

## 🧪 Testing

The system has been tested with real data:
- 11 panels on a single roof plane
- California temperature extremes (-42.8°C to 56.7°C)
- Huawei SUN2000-2KTL-L1 inverter with 2 MPPTs
- Optimal result: 2 strings of 3 and 8 panels using 2 MPPTs

## 📚 References

- `auto_design_reference.txt`: Detailed guide to auto-design.json structure
- `solar_cell_temperature_coefficients.py`: Temperature function documentation
- Jinko Solar panel specifications and temperature coefficients

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with real data
5. Submit a pull request

## 📄 License

This project is part of the auto-stringing optimization system for solar panel installations.

---

**Note**: This implementation follows the complete end-to-end process for backend optimization logic, detailing every step from initial calculations to final output, with clear explanation of when parallel configuration decisions are made.