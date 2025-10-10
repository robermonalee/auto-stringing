#!/bin/bash

# Files to move (documentation, test files, old outputs, plot images)
mv CURRENT_VALIDATION_CORRECTION.md v2_backup_simple/
mv DUAL_OUTPUT_FORMAT.md v2_backup_simple/
mv FINAL_HIERARCHY_IMPLEMENTATION.md v2_backup_simple/
mv OUTPUT_FORMAT.md v2_backup_simple/
mv POWER_VALIDATION_DESIGN.md v2_backup_simple/
mv POWER_VALIDATION_SUCCESS.md v2_backup_simple/
mv README.md v2_backup_simple/
mv V2_FINAL_SUMMARY.md v2_backup_simple/

# Test files
mv test_all_formatted.py v2_backup_simple/
mv test_power_validation.py v2_backup_simple/

# Old output files
mv exampleCA_formatted_output.json v2_backup_simple/
mv oct9design_formatted_output.json v2_backup_simple/
mv oct9design_frontend.json v2_backup_simple/
mv oct9design_no_validation.json v2_backup_simple/
mv oct9design_power_validated_15strings.json v2_backup_simple/
mv oct9design_power_validated_output.json v2_backup_simple/
mv oct9design_string_validation.json v2_backup_simple/
mv oct9design_technical.json v2_backup_simple/
mv oct9design_with_validation.json v2_backup_simple/
mv second-test_formatted_output.json v2_backup_simple/

# Plot images
mv oct9design_15strings_FINAL.png v2_backup_simple/
mv oct9design_power_validated.png v2_backup_simple/
mv oct9design_power_validated_fixed.png v2_backup_simple/

# Old script
mv move_to_backup.sh v2_backup_simple/

# output_formatter.py is not needed (integrated into simple_stringing.py)
mv output_formatter.py v2_backup_simple/

echo "✅ Moved unused files to v2_backup_simple/"
