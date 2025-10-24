"""
Flask API Server for Solar Stringing Optimizer
Provides REST API endpoints for stringing optimization
"""

from flask import Flask, request, jsonify
from simple_stringing import SimpleStringingOptimizer
import data_parsers
import json
import traceback

app = Flask(__name__)

# Load static data files once at startup
try:
    PANEL_SPECS_CSV = data_parsers.parse_panel_specs_csv('panel_specs.csv')
    INVERTER_SPECS_CSV = data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    TEMP_DATA_CSV = 'amb_temperature_data.csv'
    print("✅ Static data files loaded successfully")
except Exception as e:
    print(f"❌ Error loading data files: {e}")
    raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Solar Stringing Optimizer API",
        "version": "v2.0"
    }), 200


@app.route('/api/optimize', methods=['POST'])
def optimize_stringing():
    """
    Main optimization endpoint
    
    Request Body:
    {
        "autoDesign": {...},                  // Auto-design JSON structure (or "design")
        "solarPanelSpecs": {...},             // Optional: panel specs from input (voc, isc, vmp, imp)
        "inverterSpecs": {...},               // Optional: inverter specs from input
        "state": "California",                // State name for temperature data
        "validate_power": true,               // Optional: enable power validation (default: false)
        "output_frontend": true               // Optional: frontend format (default: false)
    }
    
    Note: If solarPanelSpecs/inverterSpecs are not provided, uses default CSV files
    
    Returns:
    {
        "success": true,
        "data": {...},                // Stringing output
        "metadata": {
            "panels_stringed": 58,
            "total_panels": 63,
            "strings_created": 15,
            "inverters_used": 15
        }
    }
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract parameters - support both 'design' and 'autoDesign' keys
        design = data.get('design') or data.get('autoDesign')
        state = data.get('state', 'California')
        validate_power = data.get('validate_power', False)
        output_frontend = data.get('output_frontend', False)
        
        # NEW: Guided PCA parameters
        use_guided_pca = data.get('use_guided_pca', False)
        pca_method = data.get('pca_method', 'guided_pca')  # "guided_pca", "forced_axis", or "nearest_neighbor"
        
        # Get inverters quantity
        inverters_quantity = data.get('invertersQuantity')

        # Support solarPanelSpecs and inverterSpecs from input package
        panel_specs_input = data.get('solarPanelSpecs')
        inverter_specs_input = data.get('inverterSpecs')
        
        if not design:
            return jsonify({
                "success": False,
                "error": "Missing 'design' or 'autoDesign' field in request"
            }), 400
        
        # Create panel specs from design
        # Use panel specs from request if provided, otherwise use CSV
        panel_specs_data = panel_specs_input if panel_specs_input else PANEL_SPECS_CSV
        panels = data_parsers.create_panel_specs_objects(design, panel_specs_data)
        
        # Create inverter specs
        # Use inverter specs from request if provided, otherwise use CSV
        inverter_specs_data = inverter_specs_input if inverter_specs_input else INVERTER_SPECS_CSV
        inverter = data_parsers.create_inverter_specs_object(inverter_specs_data)
        
        # Parse temperature data for the state
        temp = data_parsers.parse_temperature_data_csv(TEMP_DATA_CSV, state)
        
        # Run optimization
        optimizer = SimpleStringingOptimizer(
            panels, 
            inverter, 
            temp,
            output_frontend=output_frontend,
            use_guided_pca=use_guided_pca,
            pca_method=pca_method,
            inverters_quantity=inverters_quantity
        )
        
        # NEW: Set auto_design data for Guided PCA
        if use_guided_pca and design:
            # Extract auto_system_design if nested
            if 'auto_system_design' in design:
                optimizer.auto_design_data = design['auto_system_design']
            else:
                optimizer.auto_design_data = design
            
            # Extract roof planes
            if optimizer.auto_design_data and 'roof_planes' in optimizer.auto_design_data:
                optimizer.roof_planes = optimizer.auto_design_data['roof_planes']
        
        result = optimizer.optimize(validate_power=validate_power)
        
        # Build response
        output = result.formatted_output
        
        response = {
            "success": True,
            "data": output,
            "metadata": {
                "panels_stringed": output['summary']['total_panels_stringed'],
                "total_panels": output['summary']['total_panels'],
                "strings_created": output['summary']['total_strings'],
                "inverters_used": output['summary']['total_inverters_used'],
                "state": state,
                "validate_power": validate_power,
                "output_frontend": output_frontend,
                "use_guided_pca": use_guided_pca,
                "pca_method": pca_method
            }
        }
        
        # Add suggestions if present
        if 'suggestions' in output and output['suggestions']:
            response["metadata"]["suggestions"] = output['suggestions']
        
        return jsonify(response), 200
        
    except ValueError as e:
        # Validation errors (e.g., missing required fields)
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    except Exception as e:
        # Unexpected server errors
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ServerError",
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/validate', methods=['POST'])
def validate_design():
    """
    Validation endpoint - checks design without full optimization
    
    Request Body:
    {
        "design": {...},
        "state": "California"
    }
    
    Returns:
    {
        "success": true,
        "validation": {
            "total_panels": 63,
            "roof_planes": 6,
            "estimated_strings": 9,
            "estimated_inverters": 5,
            "preliminary_dc_ac_ratio": 21.39
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('design'):
            return jsonify({
                "success": False,
                "error": "Missing 'design' field"
            }), 400
        
        design = data['design']
        state = data.get('state', 'California')
        
        # Create specs
        panels = data_parsers.create_panel_specs_objects(design, PANEL_SPECS_CSV)
        inverter = data_parsers.create_inverter_specs_object(INVERTER_SPECS_CSV)
        temp = data_parsers.parse_temperature_data_csv(TEMP_DATA_CSV, state)
        
        # Get roof plane count
        roof_planes = set()
        for panel in panels:
            roof_planes.add(panel.roof_plane_id)
        
        # Quick estimation
        total_panels = len(panels)
        estimated_strings = total_panels // 7  # Rough estimate
        estimated_inverters = max(1, estimated_strings // 2)
        
        # Calculate preliminary DC/AC
        panel_sample = panels[0]
        temp_coeff_vmpp = 0.00446
        temp_diff_hot = temp.max_temp_c - 25.0
        vmpp_hot = panel_sample.vmpp_stc * (1 + temp_coeff_vmpp * temp_diff_hot)
        power_per_panel = vmpp_hot * panel_sample.impp_stc
        total_dc_power = total_panels * power_per_panel
        preliminary_dc_ac = total_dc_power / inverter.rated_ac_power_w if inverter.rated_ac_power_w else 0
        
        return jsonify({
            "success": True,
            "validation": {
                "total_panels": total_panels,
                "roof_planes": len(roof_planes),
                "estimated_strings": estimated_strings,
                "estimated_inverters": estimated_inverters,
                "preliminary_dc_ac_ratio": round(preliminary_dc_ac, 2),
                "inverter_model": inverter.model,
                "inverter_ac_capacity_w": inverter.rated_ac_power_w
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("="*80)
    print("🚀 Starting Solar Stringing Optimizer API Server")
    print("="*80)
    print("\nEndpoints:")
    print("  GET  /health             - Health check")
    print("  POST /api/optimize       - Run stringing optimization")
    print("  POST /api/validate       - Validate design (quick check)")
    print("\nServer will run on: http://localhost:5000")
    print("="*80)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

