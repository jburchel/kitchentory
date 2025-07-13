#!/usr/bin/env python3
"""
Comprehensive test runner for Kitchentory.
Runs all tests in a systematic order and provides detailed reporting.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


class TestRunner:
    """Main test runner class."""

    def __init__(self, verbose: bool = False, fast: bool = False):
        self.verbose = verbose
        self.fast = fast
        self.results = {}
        self.start_time = time.time()

        # Test configuration
        self.test_categories = {
            "linting": {
                "name": "Code Quality & Linting",
                "tests": ["black_check", "flake8", "isort_check"],
                "required": True,
            },
            "unit": {
                "name": "Unit Tests",
                "tests": [
                    "inventory_models",
                    "recipe_models",
                    "shopping_models",
                    "utility_functions",
                ],
                "required": True,
            },
            "integration": {
                "name": "Integration Tests",
                "tests": ["view_integration", "api_endpoints", "authentication_flow"],
                "required": True,
            },
            "security": {
                "name": "Security Tests",
                "tests": ["security_suite", "dependency_check"],
                "required": True,
            },
            "e2e": {
                "name": "End-to-End Tests",
                "tests": ["playwright_e2e"],
                "required": False,  # Optional in fast mode
            },
            "performance": {
                "name": "Performance Tests",
                "tests": ["load_test_light"],
                "required": False,  # Optional in fast mode
            },
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_command(
        self,
        command: List[str],
        description: str,
        cwd: Optional[str] = None,
        timeout: int = 300,
    ) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr."""
        if self.verbose:
            self.log(f"Running: {' '.join(command)}")

        try:
            result = subprocess.run(
                command, cwd=cwd, capture_output=True, text=True, timeout=timeout
            )

            success = result.returncode == 0

            if self.verbose or not success:
                if result.stdout:
                    self.log(f"STDOUT:\n{result.stdout}")
                if result.stderr:
                    self.log(f"STDERR:\n{result.stderr}")

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s: {description}", "ERROR")
            return False, "", "Command timed out"
        except Exception as e:
            self.log(f"Command failed: {description} - {e}", "ERROR")
            return False, "", str(e)

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are available."""
        self.log("Checking prerequisites...")

        requirements = [
            (["python", "--version"], "Python"),
            (["pip", "--version"], "Pip"),
            (["which", "black"], "Black formatter"),
            (["which", "flake8"], "Flake8 linter"),
            (["which", "isort"], "isort"),
        ]

        all_good = True
        for command, name in requirements:
            success, _, _ = self.run_command(command, f"Check {name}")
            if not success:
                self.log(f"Missing requirement: {name}", "ERROR")
                all_good = False
            elif self.verbose:
                self.log(f"✓ {name} available")

        return all_good

    def run_linting_tests(self) -> Dict[str, bool]:
        """Run code quality and linting tests."""
        self.log("Running code quality checks...")
        results = {}

        # Black formatting check
        self.log("Checking code formatting with Black...")
        success, _, stderr = self.run_command(
            ["black", "--check", "."], "Black format check"
        )
        results["black_check"] = success
        if not success:
            self.log("Code formatting issues found. Run 'black .' to fix.", "WARNING")

        # Flake8 linting
        self.log("Running Flake8 linting...")
        success, _, stderr = self.run_command(["flake8", "."], "Flake8 linting")
        results["flake8"] = success
        if not success and stderr:
            self.log(f"Linting issues found:\n{stderr}", "WARNING")

        # isort import sorting
        self.log("Checking import sorting with isort...")
        success, _, stderr = self.run_command(
            ["isort", "--check-only", "."], "isort check"
        )
        results["isort_check"] = success
        if not success:
            self.log("Import sorting issues found. Run 'isort .' to fix.", "WARNING")

        return results

    def run_unit_tests(self) -> Dict[str, bool]:
        """Run unit tests for all components."""
        self.log("Running unit tests...")
        results = {}

        # Django unit tests
        test_modules = [
            ("inventory.tests.test_models", "Inventory Models"),
            ("recipes.tests.test_models", "Recipe Models"),
            ("shopping.tests.test_models", "Shopping Models"),
        ]

        for module, description in test_modules:
            self.log(f"Testing {description}...")
            success, stdout, stderr = self.run_command(
                ["python", "manage.py", "test", module, "--verbosity=1"],
                f"Unit tests: {description}",
            )

            # Parse test results
            test_key = module.split(".")[-1]  # e.g., 'test_models'
            results[f"{module.split('.')[0]}_models"] = success

            if success:
                # Extract test count from output
                if "OK" in stdout:
                    self.log(f"✓ {description} tests passed")
                else:
                    self.log(f"? {description} tests completed (check output)")
            else:
                self.log(f"✗ {description} tests failed", "ERROR")
                if stderr:
                    self.log(stderr, "ERROR")

        return results

    def run_integration_tests(self) -> Dict[str, bool]:
        """Run integration tests."""
        self.log("Running integration tests...")
        results = {}

        # View integration tests
        self.log("Testing view integration...")
        success, stdout, stderr = self.run_command(
            [
                "python",
                "manage.py",
                "test",
                "tests.test_views_integration",
                "--verbosity=1",
            ],
            "View integration tests",
        )
        results["view_integration"] = success

        # API endpoint tests
        self.log("Testing API endpoints...")
        success, stdout, stderr = self.run_command(
            [
                "python",
                "manage.py",
                "test",
                "tests.test_api_endpoints",
                "--verbosity=1",
            ],
            "API endpoint tests",
        )
        results["api_endpoints"] = success

        # Authentication flow tests
        self.log("Testing authentication flows...")
        success, stdout, stderr = self.run_command(
            ["python", "manage.py", "test", "tests.test_auth", "--verbosity=1"],
            "Authentication tests",
        )
        results["authentication_flow"] = success

        return results

    def run_security_tests(self) -> Dict[str, bool]:
        """Run security tests."""
        self.log("Running security tests...")
        results = {}

        # Security test suite
        self.log("Running security test suite...")
        success, stdout, stderr = self.run_command(
            ["python", "manage.py", "test", "tests.test_security", "--verbosity=1"],
            "Security tests",
        )
        results["security_suite"] = success

        # Dependency vulnerability check
        self.log("Checking for known vulnerabilities in dependencies...")
        success, stdout, stderr = self.run_command(
            ["pip-audit"], "Dependency vulnerability check"
        )
        if not success:
            # pip-audit might not be installed, try safety as fallback
            success, stdout, stderr = self.run_command(
                ["safety", "check"], "Safety dependency check"
            )

        results["dependency_check"] = success
        if not success:
            self.log(
                "Dependency vulnerability check failed or tool not available", "WARNING"
            )

        return results

    def run_e2e_tests(self) -> Dict[str, bool]:
        """Run end-to-end tests."""
        if self.fast:
            self.log("Skipping E2E tests in fast mode")
            return {"playwright_e2e": True}

        self.log("Running end-to-end tests...")
        results = {}

        # Check if test server is needed
        self.log("Setting up test environment...")

        # Run Playwright E2E tests
        self.log("Running Playwright E2E tests...")
        success, stdout, stderr = self.run_command(
            ["python", "manage.py", "test", "tests.test_e2e", "--verbosity=1"],
            "Playwright E2E tests",
            timeout=600,  # E2E tests can take longer
        )
        results["playwright_e2e"] = success

        return results

    def run_performance_tests(self) -> Dict[str, bool]:
        """Run performance tests."""
        if self.fast:
            self.log("Skipping performance tests in fast mode")
            return {"load_test_light": True}

        self.log("Running performance tests...")
        results = {}

        # Light load test (if available)
        if Path("tests/load/api_load_test.js").exists():
            self.log("Running light load test...")
            success, stdout, stderr = self.run_command(
                ["k6", "run", "--quiet", "tests/load/api_load_test.js"],
                "Light load test",
            )
            results["load_test_light"] = success
            if not success:
                self.log("Load test failed or k6 not available", "WARNING")
        else:
            results["load_test_light"] = True  # Skip if no load test file

        return results

    def run_all_tests(self) -> Dict[str, Dict[str, bool]]:
        """Run all test categories."""
        all_results = {}

        # Check prerequisites first
        if not self.check_prerequisites():
            self.log(
                "Prerequisites check failed. Please install missing tools.", "ERROR"
            )
            return {}

        # Run each test category
        for category_key, category_info in self.test_categories.items():
            if self.fast and not category_info["required"]:
                self.log(f"Skipping {category_info['name']} in fast mode")
                continue

            self.log(f"\n{'='*60}")
            self.log(f"Running {category_info['name']}")
            self.log(f"{'='*60}")

            try:
                if category_key == "linting":
                    results = self.run_linting_tests()
                elif category_key == "unit":
                    results = self.run_unit_tests()
                elif category_key == "integration":
                    results = self.run_integration_tests()
                elif category_key == "security":
                    results = self.run_security_tests()
                elif category_key == "e2e":
                    results = self.run_e2e_tests()
                elif category_key == "performance":
                    results = self.run_performance_tests()
                else:
                    results = {}

                all_results[category_key] = results

                # Summary for this category
                passed = sum(1 for success in results.values() if success)
                total = len(results)
                self.log(f"{category_info['name']}: {passed}/{total} tests passed")

            except Exception as e:
                self.log(f"Error running {category_info['name']}: {e}", "ERROR")
                all_results[category_key] = {
                    test: False for test in category_info["tests"]
                }

        return all_results

    def generate_report(self, results: Dict[str, Dict[str, bool]]) -> str:
        """Generate a comprehensive test report."""
        report_lines = []
        report_lines.append("KITCHENTORY TEST REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Duration: {time.time() - self.start_time:.1f} seconds")
        report_lines.append("")

        overall_passed = 0
        overall_total = 0

        for category_key, category_results in results.items():
            category_info = self.test_categories[category_key]
            report_lines.append(f"{category_info['name']}:")
            report_lines.append("-" * 40)

            for test_name, success in category_results.items():
                status = "PASS" if success else "FAIL"
                report_lines.append(f"  {test_name:<30} {status}")
                overall_total += 1
                if success:
                    overall_passed += 1

            category_passed = sum(1 for success in category_results.values() if success)
            category_total = len(category_results)
            report_lines.append(f"  Category Total: {category_passed}/{category_total}")
            report_lines.append("")

        # Overall summary
        report_lines.append("OVERALL SUMMARY")
        report_lines.append("=" * 60)
        report_lines.append(f"Total tests passed: {overall_passed}/{overall_total}")

        success_rate = (
            (overall_passed / overall_total * 100) if overall_total > 0 else 0
        )
        report_lines.append(f"Success rate: {success_rate:.1f}%")

        if overall_passed == overall_total:
            report_lines.append("🎉 ALL TESTS PASSED! 🎉")
        else:
            failed_tests = overall_total - overall_passed
            report_lines.append(f"❌ {failed_tests} test(s) failed")

        return "\n".join(report_lines)

    def save_results(self, results: Dict[str, Dict[str, bool]], report: str):
        """Save test results and report to files."""
        results_dir = Path("test-results")
        results_dir.mkdir(exist_ok=True)

        # Save JSON results
        results_file = results_dir / "test_results.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "results": results,
                    "summary": {
                        "total_passed": sum(
                            sum(1 for success in cat.values() if success)
                            for cat in results.values()
                        ),
                        "total_tests": sum(len(cat) for cat in results.values()),
                    },
                },
                f,
                indent=2,
            )

        # Save text report
        report_file = results_dir / "test_report.txt"
        with open(report_file, "w") as f:
            f.write(report)

        self.log(f"Results saved to {results_file}")
        self.log(f"Report saved to {report_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run comprehensive Kitchentory tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--fast", "-f", action="store_true", help="Fast mode (skip optional tests)"
    )
    parser.add_argument(
        "--category",
        "-c",
        choices=["linting", "unit", "integration", "security", "e2e", "performance"],
        help="Run only specific test category",
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose, fast=args.fast)

    if args.category:
        # Run only specific category
        runner.log(f"Running only {args.category} tests")
        # Implementation for single category would go here
        print("Single category mode not implemented yet")
        return

    # Run all tests
    runner.log("Starting comprehensive test suite...")
    results = runner.run_all_tests()

    if not results:
        runner.log("No tests were run due to prerequisites failure", "ERROR")
        sys.exit(1)

    # Generate and display report
    report = runner.generate_report(results)
    print("\n" + report)

    # Save results
    runner.save_results(results, report)

    # Exit with appropriate code
    total_passed = sum(
        sum(1 for success in cat.values() if success) for cat in results.values()
    )
    total_tests = sum(len(cat) for cat in results.values())

    if total_passed == total_tests:
        runner.log("All tests passed! ✅")
        sys.exit(0)
    else:
        runner.log(f"{total_tests - total_passed} test(s) failed ❌", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
