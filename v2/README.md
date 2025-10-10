# Solar Stringing Optimizer v2

Simple nearest-neighbor stringing algorithm for solar panel installations.

## Overview

This optimizer creates string configurations for solar panels by connecting them in series to meet inverter voltage and current constraints. The algorithm uses a nearest-neighbor approach per roof plane with optional power validation for optimal DC/AC ratios.

---

## Stringing Algorithm Steps

### 1. Temperature-Adjusted Voltage Calculation

Calculate panel voltages at extreme temperatures:

- **Cold Temperature (Min)**: Calculate open-circuit voltage (Voc)
  - Used to ensure strings don't exceed inverter's max DC voltage
  - Formula: `Voc_cold = Voc_stc * (1 + temp_coeff * (T_min - 25))`

- **Hot Temperature (Max)**: Calculate maximum power point voltage (Vmpp)
  - Used for operating voltage calculations
  - Formula: `Vmpp_hot = Vmpp_stc * (1 + temp_coeff * (T_max - 25))`

### 2. Determine String Length Constraints

Calculate minimum and maximum panels per string:

- **Minimum**: Based on inverter startup voltage
  - `min_panels = ceil(startup_voltage / Vmpp_hot)`
  
- **Maximum**: Based on inverter max DC voltage
  - `max_panels = floor(max_dc_voltage / Voc_cold)`

- **Ideal**: Based on MPPT operating range
  - `ideal_panels = panels that keep Vmpp_hot in middle of MPPT range`
  - Default: ~9 panels for typical inverters

- **Power-Adjusted** (if `validate_power=True`):
  - `ideal_panels = floor(inverter_max_dc_power / power_per_panel)`
  - Ensures strings fit within inverter power capacity

### 3. Group Panels by Roof Plane

Each roof plane is treated independently:

- Extract all panels belonging to each roof plane
- Maintain spatial relationships using panel coordinates

### 4. Create Strings Using Nearest-Neighbor

For each roof plane, build strings iteratively:

**Algorithm**:
1. Start with an unassigned panel
2. Add the closest unassigned panel to the current string
3. Continue until reaching ideal string length
4. If no more panels within reasonable distance, close the string
5. Repeat until all assignable panels are stringed

**Distance Calculation**:
- Euclidean distance between panel center coordinates
- Used to minimize wire runs and maintain logical connections

### 5. Handle Straggler Panels

Panels that cannot form valid strings:

- **Reason**: Insufficient count to meet minimum voltage requirements
- **Detection**: Groups of panels < minimum panels per string
- **Reporting**: Generate warnings with panel IDs and voltage deficit
- **Action**: Left unconnected (cannot meet electrical safety requirements)

### 6. Assign Strings to MPPTs

Group strings into MPPTs based on voltage and current compatibility:

- Check if strings have compatible voltages (within MPPT range)
- Verify total current doesn't exceed MPPT limits
- Allow parallel connections if voltages match

### 7. Assign MPPTs to Inverters

Group MPPTs into inverters based on capacity:

- Each inverter can support a limited number of MPPTs
- Assign MPPTs sequentially until inverter capacity is reached
- Create new inverter instance when needed

**With Power Validation** (`validate_power=True`):
- Track total DC power per inverter
- Create new inverter if adding MPPT exceeds power limit
- Ensures optimal DC/AC ratios (1.1-1.5)

### 8. Calculate Electrical Properties

For each string, MPPT, and inverter, calculate:

**Voltage**:
- Operating voltage: `V_string = Vmpp_hot * num_panels`
- Max voltage: `V_max = Voc_cold * num_panels`

**Current**:
- Operating current: `I_string = Impp_stc`
- Safety current: `I_safety = Isc_stc * 1.25`

**Power**:
- DC power: `P_dc = V_string * I_string`
- DC/AC ratio: `ratio = total_dc_power / inverter_ac_power`

**Validation Flags**:
- `within_range`: Voltage is within MPPT operating range
- `will_clip`: Operating current exceeds inverter's max usable current
- `is_safe`: Safety current is within inverter's short-circuit limit
- `status`: OPTIMAL (1.1-1.3), ACCEPTABLE (1.0-1.5), UNDERSIZED (<1.0), OVERSIZED (>1.5)

### 9. Generate Suggestions

Based on results, provide actionable recommendations:

- **Stragglers + Undersized Inverter**: Suggest larger inverter capacity
- **Stragglers Only**: Suggest more compact panel arrangement
- **String Cropping**: Suggest larger inverter to accommodate longer strings

### 10. Format Output

Two output formats available:

**Technical Format** (`output_frontend=False`):
- Hierarchical: Inverter → Roof → MPPT → Strings
- Good for engineering analysis

**Frontend Format** (`output_frontend=True`):
- Flat structure with references
- Easier for API consumption
- Includes all device specs separately

---

## Deployment Package

### Files Included

**Core Engine**:
- `simple_stringing.py` - Main stringing algorithm
- `data_parsers.py` - Input/output parsing
- `validatePower.py` - Power validation logic
- `lambda_handler.py` - AWS Lambda handler

**Data Files**:
- `panel_specs.csv` - Panel electrical specifications
- `inverter_specs.csv` - Inverter specifications
- `amb_temperature_data.csv` - Temperature data by state

**Package**: `solar-stringing-optimizer-v2-*.zip` (24 KB)

### AWS Lambda Configuration

```
Handler:    lambda_handler.lambda_handler
Runtime:    Python 3.9 or higher
Timeout:    30 seconds
Memory:     512 MB
URL:        https://ywarxlkyexfqbdh5srw6f3vysq0ukojs.lambda-url.us-east-2.on.aws/
```

---

## API Usage

### Required Parameters

```json
{
  "autoDesign": {
    "roof_planes": {
      "1": {"azimuth": 95.15, "orientation": "landscape", "pitch": 17.94}
    },
    "solar_panels": {
      "1": [
        {"panel_id": "p1", "roof_plane_id": "1", "pix_coords": {"c0": [x, y]}}
      ]
    }
  },
  "solarPanelSpecs": {
    "voc": 52.79,
    "isc": 14.19,
    "vmp": 43.88,
    "imp": 13.56
  },
  "inverterSpecs": {
    "maxDCInputVoltage": 600.0,
    "numberOfMPPTs": 2,
    "startUpVoltage": 100.0,
    "maxDCInputCurrentPerMPPT": 12.5,
    "maxDCInputCurrentPerString": 12.5,
    "mpptOperatingVoltageMinRange": 90.0,
    "mpptOperatingVoltageMaxRange": 560.0,
    "maxShortCircuitCurrentPerMPPT": 18.0,
    "ratedACPower": 2000
  }
}
```

### Optional Parameters

```json
{
  "state": "California",
  "validate_power": true,
  "output_frontend": true
}
```

**validate_power** (boolean, default: false):
- `false`: Uses voltage-based ideal string length (typically 9 panels)
- `true`: Adjusts string length to fit inverter power capacity for optimal DC/AC ratios
- Recommended: `true` for production

**output_frontend** (boolean, default: true):
- `false`: Hierarchical structure (Inverter → Roof → MPPT → Strings)
- `true`: Flat structure with references
- Recommended: `true` for API consumption

---

## Example Request

```bash
curl -X POST "https://ywarxlkyexfqbdh5srw6f3vysq0ukojs.lambda-url.us-east-2.on.aws/" \
  -H "Content-Type: application/json" \
  -d '{
    "autoDesign": {...},
    "solarPanelSpecs": {...},
    "inverterSpecs": {...},
    "state": "California",
    "validate_power": true,
    "output_frontend": true
  }'
```

---

## Output Structure

```json
{
  "success": true,
  "data": {
    "strings": {
      "s1": {
        "panel_ids": ["panel_1", "panel_2", "panel_3"],
        "inverter": "Inverter_1",
        "mppt": "MPPT_1",
        "roof_section": "1",
        "properties": {
          "voltage_V": 150.3,
          "current_A": 13.56,
          "power_W": 2038.1
        }
      }
    },
    "inverter_specs": {
      "Inverter_1": {
        "voltage": {...},
        "current": {...},
        "power": {
          "dc_ac_ratio": 1.02,
          "total_dc_power_W": 2038.1,
          "rated_ac_power_W": 2000.0
        },
        "validation": {
          "status": "OPTIMAL"
        }
      }
    },
    "mppt_specs": {...},
    "summary": {
      "total_panels": 3,
      "total_panels_stringed": 3,
      "total_strings": 1,
      "total_inverters_used": 1
    },
    "straggler_warnings": [],
    "suggestions": [],
    "metadata": {
      "optimization_time_seconds": 0.05,
      "state": "California",
      "validate_power": true,
      "output_frontend": true
    }
  }
}
```

---

## Key Features

- Simple nearest-neighbor algorithm (no complex optimization)
- Temperature-adjusted voltage calculations
- Optional power validation for optimal DC/AC ratios
- Roof plane isolation (independent stringing per roof)
- Straggler detection and warnings
- Intelligent sizing suggestions
- Dual output formats (technical and frontend)
- No external dependencies (pure Python + stdlib)
- Lightweight package (24 KB)
- Fast execution (100-300ms for typical systems)

---

## Performance

- **Package Size**: 24 KB (compressed)
- **Cold Start**: 1-2 seconds
- **Warm Execution**: 100-300ms (for 60 panels)
- **Memory Usage**: <100 MB
- **Dependencies**: None (pure Python)

---

## Documentation

- `API_USAGE_GUIDE.md` - Complete API reference with detailed examples
- `CURL_EXAMPLES_V2.sh` - Interactive curl command examples
- `DEPLOYMENT_SUMMARY.txt` - Deployment checklist and configuration
- `create_deployment_package.sh` - Script to rebuild deployment package

---

## Deployment Steps

1. Upload `solar-stringing-optimizer-v2-*.zip` to AWS Lambda
2. Set handler to `lambda_handler.lambda_handler`
3. Set runtime to Python 3.9 or higher
4. Configure timeout (30 seconds) and memory (512 MB)
5. Test with curl examples from `CURL_EXAMPLES_V2.sh`
6. Monitor CloudWatch logs

---

## Support

For detailed API documentation, see `API_USAGE_GUIDE.md`

For curl examples, see `CURL_EXAMPLES_V2.sh`
