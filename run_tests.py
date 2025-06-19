#!/usr/bin/env python3
"""
Comprehensive test runner for Novatel ProPak6 Navigation Data Toolkit
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'-' * 20} {title} {'-' * 20}")

def run_pytest(test_path, description):
    """Run pytest on a specific test file or directory"""
    print(f"\nRunning {description}...")
    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True, result.stdout.count("PASSED"), 0
        else:
            print(f"❌ {description} - FAILED")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            
            # Count passed and failed tests
            passed = result.stdout.count("PASSED")
            failed = result.stdout.count("FAILED")
            return False, passed, failed
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False, 0, 1
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False, 0, 1

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Dependency Check")
    
    required_packages = ['pytest', 'pynmea2', 'pyModeS']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - Available")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def run_individual_tests():
    """Run individual test files"""
    print_section("Individual Module Tests")
    
    test_files = [
        ("tests/test_config.py", "Configuration Tests"),
        ("tests/test_gdl90_deframer.py", "GDL-90 Deframer Tests"),
        ("tests/test_adsb_parser.py", "ADS-B Parser Tests"),
        ("tests/test_nmea_parser.py", "NMEA Parser Tests"),
        ("tests/test_udp_listener.py", "UDP Listener Tests"),
        ("tests/test_navigation_display.py", "Navigation Display Tests"),
        ("tests/test_main.py", "Main Application Tests"),
    ]
    
    results = []
    total_passed = 0
    total_failed = 0
    
    for test_file, description in test_files:
        if os.path.exists(test_file):
            success, passed, failed = run_pytest(test_file, description)
            results.append((description, success, passed, failed))
            total_passed += passed
            total_failed += failed
        else:
            print(f"⚠️  {test_file} not found")
            results.append((description, False, 0, 1))
            total_failed += 1
    
    return results, total_passed, total_failed

def run_integration_tests():
    """Run integration tests"""
    print_section("Integration Tests")
    
    if os.path.exists("tests/test_integration.py"):
        success, passed, failed = run_pytest("tests/test_integration.py", "Integration Tests")
        return [(("Integration Tests", success, passed, failed))], passed, failed
    else:
        print("⚠️  Integration tests not found")
        return [("Integration Tests", False, 0, 1)], 0, 1

def run_legacy_tests():
    """Run legacy test files if they exist"""
    print_section("Legacy Tests")
    
    legacy_files = [
        ("tests/test_gdl90_fix_demo.py", "Legacy GDL-90 Fix Demo"),
        ("tests/test_adsb_integration.py", "Legacy ADS-B Integration"),
        ("tests/test_adsb_message_parsing.py", "Legacy ADS-B Message Parsing"),
        ("tests/test_nmea_sample.py", "Legacy NMEA Sample"),
        ("tests/test_udp_sender.py", "Legacy UDP Sender"),
        ("tests/test_adsb_sender.py", "Legacy ADS-B Sender"),
    ]
    
    results = []
    total_passed = 0
    total_failed = 0
    
    for test_file, description in legacy_files:
        if os.path.exists(test_file):
            print(f"\nRunning {description}...")
            try:
                # Try to run as Python script
                cmd = [sys.executable, test_file]
                
                # Add test mode flag for scripts that support it
                if test_file in ["tests/test_nmea_sample.py", "tests/test_udp_sender.py", "tests/test_adsb_sender.py"]:
                    cmd.append("--test")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"✅ {description} - PASSED")
                    results.append((description, True, 1, 0))
                    total_passed += 1
                else:
                    print(f"❌ {description} - FAILED")
                    if result.stdout:
                        print("STDOUT:", result.stdout[-200:])  # Last 200 chars
                    if result.stderr:
                        print("STDERR:", result.stderr[-200:])
                    results.append((description, False, 0, 1))
                    total_failed += 1
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ {description} - TIMEOUT")
                results.append((description, False, 0, 1))
                total_failed += 1
            except Exception as e:
                print(f"💥 {description} - ERROR: {e}")
                results.append((description, False, 0, 1))
                total_failed += 1
        else:
            print(f"ℹ️  {test_file} not found (optional)")
    
    return results, total_passed, total_failed

def print_summary(all_results, total_passed, total_failed):
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    print(f"Total Tests Run: {total_passed + total_failed}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        success_rate = 100.0
    else:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for description, success, passed, failed in all_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {description} ({passed} passed, {failed} failed)")
    
    return total_failed == 0

def main():
    """Main test runner"""
    start_time = time.time()
    
    print_header("Novatel ProPak6 Navigation Data Toolkit - Test Suite")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot run tests due to missing dependencies")
        return 1
    
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    all_results = []
    total_passed = 0
    total_failed = 0
    
    # Run individual module tests
    individual_results, ind_passed, ind_failed = run_individual_tests()
    all_results.extend(individual_results)
    total_passed += ind_passed
    total_failed += ind_failed
    
    # Run integration tests
    integration_results, int_passed, int_failed = run_integration_tests()
    all_results.extend(integration_results)
    total_passed += int_passed
    total_failed += int_failed
    
    # Run legacy tests
    legacy_results, leg_passed, leg_failed = run_legacy_tests()
    all_results.extend(legacy_results)
    total_passed += leg_passed
    total_failed += leg_failed
    
    # Print summary
    success = print_summary(all_results, total_passed, total_failed)
    
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)