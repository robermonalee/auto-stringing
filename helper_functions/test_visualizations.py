#!/usr/bin/env python3
"""
Test script for both lightweight and heavy visualization approaches

This script demonstrates the difference between:
1. Lightweight visualization (AWS-compatible, no matplotlib)
2. Heavy visualization (full matplotlib capabilities)
"""

import json
import sys
import os
from typing import Dict, Any


def test_lightweight_visualization():
    """Test the lightweight visualization approach"""
    print("=" * 60)
    print("TESTING LIGHTWEIGHT VISUALIZATION (AWS-Compatible)")
    print("=" * 60)
    
    try:
        from visualization_lite import SolarStringingVisualizerLite, create_lite_visualization_from_files
        
        # Test with the 80-panel system
        print("Creating lightweight visualization...")
        visualizer = create_lite_visualization_from_files(
            'second-test.json', 
            'results_second_test.json',
            '.'
        )
        
        print("✅ Lightweight visualization completed successfully!")
        print("Generated files:")
        print("  - panel_coordinates.json (coordinate data)")
        print("  - stringing_layout.svg (SVG visualization)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_heavy_visualization():
    """Test the heavy visualization approach"""
    print("\n" + "=" * 60)
    print("TESTING HEAVY VISUALIZATION (Full Matplotlib)")
    print("=" * 60)
    
    try:
        from visualization_helper import SolarStringingVisualizer, create_visualization_from_files
        
        # Test with the 80-panel system
        print("Creating heavy visualization...")
        fig, ax = create_visualization_from_files(
            'second-test.json', 
            'results_second_test.json',
            'stringing_visualization_test.png'
        )
        
        print("✅ Heavy visualization completed successfully!")
        print("Generated files:")
        print("  - stringing_visualization_test.png (full matplotlib plot)")
        
        # Test summary visualization
        print("\nCreating summary visualization...")
        fig, (ax1, ax2) = create_visualization_from_files(
            'second-test.json', 
            'results_second_test.json',
            'stringing_summary_test.png'
        )
        
        print("✅ Summary visualization completed successfully!")
        print("Generated files:")
        print("  - stringing_summary_test.png (summary plot)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This is expected if matplotlib is not installed")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def compare_file_sizes():
    """Compare the file sizes of different visualization outputs"""
    print("\n" + "=" * 60)
    print("FILE SIZE COMPARISON")
    print("=" * 60)
    
    files_to_check = [
        'panel_coordinates.json',
        'stringing_layout.svg',
        'stringing_visualization.png',
        'stringing_summary.png'
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            size_kb = size / 1024
            print(f"{filename:30} {size_kb:8.1f} KB")
        else:
            print(f"{filename:30} {'NOT FOUND':>8}")


def test_dependency_separation():
    """Test that the visualization modules can be imported independently"""
    print("\n" + "=" * 60)
    print("DEPENDENCY SEPARATION TEST")
    print("=" * 60)
    
    # Test lightweight visualization (should always work)
    try:
        from visualization_lite import SolarStringingVisualizerLite
        print("✅ visualization_lite imports successfully (no heavy dependencies)")
    except ImportError as e:
        print(f"❌ visualization_lite import failed: {e}")
    
    # Test heavy visualization (may fail if matplotlib not available)
    try:
        from visualization_helper import SolarStringingVisualizer
        print("✅ visualization_helper imports successfully (matplotlib available)")
    except ImportError as e:
        print(f"⚠️  visualization_helper import failed: {e}")
        print("   This is expected in AWS environments without matplotlib")
    
    # Test core optimization (should always work)
    try:
        from solar_stringing_optimizer import SolarStringingOptimizer
        print("✅ Core optimization imports successfully (no visualization dependencies)")
    except ImportError as e:
        print(f"❌ Core optimization import failed: {e}")


def main():
    """Main test function"""
    print("SOLAR STRINGING VISUALIZATION TEST SUITE")
    print("=" * 60)
    print("Testing both lightweight and heavy visualization approaches")
    print("for AWS deployment compatibility")
    
    # Check if required files exist
    required_files = ['second-test.json', 'results_second_test.json']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please run the optimization first to generate results_second_test.json")
        return
    
    # Run tests
    lightweight_success = test_lightweight_visualization()
    heavy_success = test_heavy_visualization()
    
    # Compare file sizes
    compare_file_sizes()
    
    # Test dependency separation
    test_dependency_separation()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Lightweight visualization: {'✅ PASS' if lightweight_success else '❌ FAIL'}")
    print(f"Heavy visualization:       {'✅ PASS' if heavy_success else '❌ FAIL'}")
    
    if lightweight_success and heavy_success:
        print("\n🎉 All visualization tests passed!")
        print("Both AWS-compatible and full visualization approaches are working.")
    elif lightweight_success:
        print("\n✅ Lightweight visualization working (suitable for AWS deployment)")
        print("⚠️  Heavy visualization requires matplotlib installation")
    else:
        print("\n❌ Visualization tests failed")
    
    print("\nFor AWS deployment:")
    print("- Use visualization_lite.py for basic visualization needs")
    print("- Exclude visualization_helper.py from deployment package")
    print("- Install only requirements_aws.txt (no matplotlib)")


if __name__ == "__main__":
    main()
