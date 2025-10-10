#!/bin/bash

# ============================================================================
# Solar Stringing Optimizer API - cURL Examples
# ============================================================================

BASE_URL="http://localhost:5000"

echo "============================================================================"
echo "                  SOLAR STRINGING OPTIMIZER API"
echo "                         cURL Examples"
echo "============================================================================"
echo ""

# ============================================================================
# Example 1: Health Check
# ============================================================================
echo "1️⃣  HEALTH CHECK"
echo "----------------------------------------------------------------------------"
echo "Command:"
echo "curl -X GET ${BASE_URL}/health"
echo ""
echo "Response:"
curl -s -X GET ${BASE_URL}/health | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Example 2: Quick Validation (No optimization)
# ============================================================================
echo "2️⃣  QUICK VALIDATION"
echo "----------------------------------------------------------------------------"
echo "Command:"
echo "curl -X POST ${BASE_URL}/api/validate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d @- << 'EOF'"
echo "{\"design\": <design_json>, \"state\": \"California\"}"
echo "EOF"
echo ""
echo "Response:"
curl -s -X POST ${BASE_URL}/api/validate \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\"
  }" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Example 3: Basic Optimization (No optional parameters)
# ============================================================================
echo "3️⃣  BASIC OPTIMIZATION (Default Parameters)"
echo "----------------------------------------------------------------------------"
echo "Parameters:"
echo "  - validate_power: false (default)"
echo "  - output_frontend: false (default)"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/api/optimize \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"design\": <design_json>, \"state\": \"California\"}'"
echo ""
echo "Response (summary only):"
curl -s -X POST ${BASE_URL}/api/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\"
  }" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps({'success': data['success'], 'metadata': data['metadata']}, indent=2))"
echo ""
echo ""

# ============================================================================
# Example 4: With validate_power=true
# ============================================================================
echo "4️⃣  WITH POWER VALIDATION"
echo "----------------------------------------------------------------------------"
echo "Parameters:"
echo "  - validate_power: true  ✅"
echo "  - output_frontend: false (default)"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/api/optimize \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"design\": <design_json>, \"validate_power\": true}'"
echo ""
echo "Response (summary only):"
curl -s -X POST ${BASE_URL}/api/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\",
    \"validate_power\": true
  }" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps({'success': data['success'], 'metadata': data['metadata']}, indent=2))"
echo ""
echo ""

# ============================================================================
# Example 5: With output_frontend=true
# ============================================================================
echo "5️⃣  WITH FRONTEND OUTPUT FORMAT"
echo "----------------------------------------------------------------------------"
echo "Parameters:"
echo "  - validate_power: false (default)"
echo "  - output_frontend: true  ✅"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/api/optimize \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"design\": <design_json>, \"output_frontend\": true}'"
echo ""
echo "Response (first string only):"
curl -s -X POST ${BASE_URL}/api/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\",
    \"output_frontend\": true
  }" | python3 -c "import sys, json; data=json.load(sys.stdin); first_string=list(data['data']['strings'].keys())[0]; print(json.dumps({first_string: data['data']['strings'][first_string]}, indent=2))"
echo ""
echo ""

# ============================================================================
# Example 6: FULL CONFIGURATION (Both parameters enabled)
# ============================================================================
echo "6️⃣  FULL CONFIGURATION (validate_power=true + output_frontend=true)"
echo "============================================================================"
echo "Parameters:"
echo "  - validate_power: true   ✅"
echo "  - output_frontend: true  ✅"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/api/optimize \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"design\": <design_json>, \"validate_power\": true, \"output_frontend\": true}'"
echo ""
echo "Full command with file:"
cat << 'COMMAND_EOF'
curl -X POST http://localhost:5000/api/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\",
    \"validate_power\": true,
    \"output_frontend\": true
  }"
COMMAND_EOF
echo ""
echo "Executing..."
curl -s -X POST ${BASE_URL}/api/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"design\": $(cat oct9design.json),
    \"state\": \"California\",
    \"validate_power\": true,
    \"output_frontend\": true
  }" > /tmp/stringing_output.json

echo ""
echo "✅ Full output saved to: /tmp/stringing_output.json"
echo ""
echo "Response Summary:"
cat /tmp/stringing_output.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps({'success': data['success'], 'metadata': data['metadata']}, indent=2))"
echo ""
echo "Output Structure:"
cat /tmp/stringing_output.json | python3 -c "import sys, json; data=json.load(sys.stdin); print('  Top-level keys:', list(data.keys())); print('  Data keys:', list(data['data'].keys())); print('  Strings count:', len(data['data']['strings'])); print('  Inverters count:', len(data['data']['inverter_specs']))"
echo ""
echo ""

# ============================================================================
# Example 7: Error Handling (Bad Request)
# ============================================================================
echo "7️⃣  ERROR HANDLING"
echo "----------------------------------------------------------------------------"
echo "Command (missing 'design' field):"
echo "curl -X POST ${BASE_URL}/api/optimize \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"state\": \"California\"}'"
echo ""
echo "Response:"
curl -s -X POST ${BASE_URL}/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"state": "California"}' | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "============================================================================"
echo "                            QUICK REFERENCE"
echo "============================================================================"
echo ""
echo "Required Parameters:"
echo "  - design: JSON object (auto-design structure)"
echo ""
echo "Optional Parameters:"
echo "  - state: string (default: 'California')"
echo "  - validate_power: boolean (default: false)"
echo "    └─ Enables power validation and adjusts string length for optimal DC/AC"
echo "  - output_frontend: boolean (default: false)"
echo "    └─ Returns flat structure with references instead of hierarchical"
echo ""
echo "Recommended Production Configuration:"
echo "  {\"validate_power\": true, \"output_frontend\": true}"
echo ""
echo "============================================================================"

