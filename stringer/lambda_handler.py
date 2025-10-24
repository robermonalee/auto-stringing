#!/usr/bin/env python3
"""
AWS Lambda handler for Solar Stringing Optimizer v2
Simple nearest-neighbor stringing with optional power validation

UPDATED: October 10, 2025
- Now uses improved data_parsers with JSON input support
- Cleaner code leveraging data_parsers.create_panel_specs_objects() and create_inverter_specs_object()
"""

import json
import os
import time
from typing import Dict, Any
import traceback

# Import the v2 solar stringing optimizer components
from simple_stringing import SimpleStringingOptimizer
import data_parsers


def lambda_handler(event, context):
    """
    AWS Lambda handler for solar stringing optimization requests
    
    Input Format:
    {
        "autoDesign": {...},            // Auto-design JSON structure
        "solarPanelSpecs": {...},       // Panel specifications (voc, isc, vmp, imp)
        "inverterSpecs": {...},         // Inverter specifications
        "state": "California",          // State name for temperature data
        "validate_power": true,         // Optional: enable power validation (default: false)
        "output_frontend": true         // Optional: frontend format (default: true)
    }
    """
    try:
        # Parse the request
        if 'body' in event:
            # API Gateway request
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            # Direct Lambda invocation
            body = event
        
        # Extract parameters
        auto_design_raw = body.get('autoDesign', {})
        state = body.get('state', 'California')
        solar_panel_specs = body.get('solarPanelSpecs', {})
        inverter_specs_input = body.get('inverterSpecs', {})
        validate_power = body.get('validate_power', False)
        output_frontend = body.get('output_frontend', True)  # Default to frontend format for API
        
        # Validate required parameters
        if not auto_design_raw or not solar_panel_specs or not inverter_specs_input:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required parameters',
                    'required': ['autoDesign', 'solarPanelSpecs', 'inverterSpecs'],
                    'received': list(body.keys())
                })
            }
        
        # Extract auto_system_design structure
        if 'auto_system_design' in auto_design_raw:
            auto_design = auto_design_raw['auto_system_design']
        else:
            auto_design = auto_design_raw
        
        # Prepare auto_design_data for data_parsers
        auto_design_data = {
            'solar_panels': auto_design.get('solar_panels', []),
            'roof_planes': auto_design.get('roof_planes', {})
        }
        
        # Use improved data_parsers to create panel specs
        # Now supports both CSV (list) and JSON (dict) inputs!
        panels = data_parsers.create_panel_specs_objects(auto_design_data, solar_panel_specs)
        
        if not panels:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'No valid panels found in autoDesign'
                })
            }
        
        # Use improved data_parsers to create inverter specs
        # Now supports both CSV (list) and JSON (dict) inputs!
        inverter_spec = data_parsers.create_inverter_specs_object(inverter_specs_input)
        
        # Get temperature data
        temp = _get_temperature_data_from_csv(state)
        
        # Create optimizer
        optimizer = SimpleStringingOptimizer(
            panel_specs=panels,
            inverter_specs=inverter_spec,
            temperature_data=temp,
            output_frontend=output_frontend
        )
        
        # Run optimization
        start_time = time.time()
        result = optimizer.optimize(validate_power=validate_power)
        optimization_time = time.time() - start_time
        
        # Get formatted output
        output = result.formatted_output
        
        # Add metadata
        output['metadata'] = {
            'optimization_time_seconds': round(optimization_time, 4),
            'state': state,
            'validate_power': validate_power,
            'output_frontend': output_frontend,
            'total_panels': len(panels),
            'timestamp': time.time()
        }
        
        # Build response
        response_body = {
            'success': True,
            'data': output
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps(response_body)
        }
        
    except ValueError as e:
        # Validation errors (e.g., missing required fields)
        print(f"Validation error: {str(e)}")
        
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': 'ValidationError'
            })
        }
        
    except Exception as e:
        # Unexpected server errors
        print(f"Error in lambda_handler: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error',
                'message': str(e),
                'error_type': 'ServerError',
                'traceback': traceback.format_exc()
            })
        }


def _get_temperature_data_from_csv(state: str):
    """
    Get temperature data for a state using the CSV parser
    Falls back to hardcoded values if CSV not available
    """
    try:
        # Try to use CSV parser
        return data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', state)
    except Exception as e:
        print(f"Warning: Could not load temperature from CSV: {e}")
        print(f"Using fallback temperature data for {state}")
        
        # Fallback temperature data
        from simple_stringing import TemperatureData
        temp_map = {
            'california': TemperatureData(-42.8, 56.7, 25.0, 5.0),
            'ca': TemperatureData(-42.8, 56.7, 25.0, 5.0),
            'texas': TemperatureData(-23.3, 48.9, 28.0, 8.0),
            'tx': TemperatureData(-23.3, 48.9, 28.0, 8.0),
            'florida': TemperatureData(-18.9, 43.3, 28.0, 15.0),
            'fl': TemperatureData(-18.9, 43.3, 28.0, 15.0),
            'new york': TemperatureData(-37.2, 42.2, 20.0, 0.0),
            'ny': TemperatureData(-37.2, 42.2, 20.0, 0.0),
            'arizona': TemperatureData(-25.6, 53.3, 30.0, 10.0),
            'az': TemperatureData(-25.6, 53.3, 30.0, 10.0),
        }
        
        state_lower = state.lower()
        return temp_map.get(state_lower, temp_map['california'])


def handle_options(event, context):
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': ''
    }
