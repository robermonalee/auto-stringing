#!/bin/bash

# ============================================================================
# Solar Stringing Optimizer - AWS Lambda Deployment Package Creator
# ============================================================================

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PACKAGE_NAME="stringer-${TIMESTAMP}.zip"
TEMP_DIR="deployment_temp"
DIST_DIR="$(dirname "$0")/dist"

echo "============================================================================"
echo "        Solar Stringing Optimizer - Deployment Package Creator"
echo "============================================================================"
echo ""

# Clean up any existing temp directory
if [ -d "$TEMP_DIR" ]; then
    echo "🧹 Cleaning up existing temp directory..."
    rm -rf "$TEMP_DIR"
fi

# Create temp directory
echo "📁 Creating temp directory..."
mkdir -p "$TEMP_DIR"

# Copy essential Python files from stringer directory
echo "📄 Copying Python modules..."
cp "$(dirname "$0")/../stringer/simple_stringing.py" "$TEMP_DIR/"
cp "$(dirname "$0")/../stringer/data_parsers.py" "$TEMP_DIR/"
cp "$(dirname "$0")/../stringer/specs.py" "$TEMP_DIR/"
cp "$(dirname "$0")/../stringer/validatePower.py" "$TEMP_DIR/"
cp "$(dirname "$0")/lambda_handler.py" "$TEMP_DIR/"

# Convert relative imports to absolute
echo "🔧 Converting relative imports to absolute..."
sed -i '' 's/from \.specs/from specs/g' "$TEMP_DIR/data_parsers.py"
sed -i '' 's/from \.specs/from specs/g' "$TEMP_DIR/simple_stringing.py"
sed -i '' 's/from \.validatePower/from validatePower/g' "$TEMP_DIR/simple_stringing.py"

# Copy CSV data files from stringer directory
echo "📊 Copying data files..."
cp "$(dirname "$0")/../stringer/panel_specs.csv" "$TEMP_DIR/"
cp "$(dirname "$0")/../stringer/inverter_specs.csv" "$TEMP_DIR/"
cp "$(dirname "$0")/../stringer/amb_temperature_data.csv" "$TEMP_DIR/"

# List files in package
echo ""
echo "📦 Package contents:"
ls -lh "$TEMP_DIR"

# Get total size
TOTAL_SIZE=$(du -sh "$TEMP_DIR" | cut -f1)
echo ""
echo "📏 Total package size: $TOTAL_SIZE"

# Create ZIP file
echo ""
echo "🗜️  Creating ZIP file: $PACKAGE_NAME"
zip -j "$DIST_DIR/$PACKAGE_NAME" "$TEMP_DIR"/*

# Clean up temp directory
echo "🧹 Cleaning up temp directory..."
rm -rf "$TEMP_DIR"

# Get final ZIP size
ZIP_SIZE=$(du -h "$DIST_DIR/$PACKAGE_NAME" | cut -f1)

echo ""
echo "============================================================================"
echo "✅ Deployment package created successfully!"
echo "============================================================================"
echo ""
echo "Package: $DIST_DIR/$PACKAGE_NAME"
echo "Size: $ZIP_SIZE"
echo ""
echo "Files included:"
echo "  ✓ simple_stringing.py       - Core stringing engine"
echo "  ✓ data_parsers.py           - Input/output parsing"
echo "  ✓ specs.py                  - Data classes for panel and inverter specs"
echo "  ✓ lambda_handler.py         - AWS Lambda handler"
echo "  ✓ panel_specs.csv           - Panel specifications"
echo "  ✓ inverter_specs.csv        - Inverter specifications"
echo "  ✓ amb_temperature_data.csv  - Temperature data"
echo ""
echo "============================================================================"
