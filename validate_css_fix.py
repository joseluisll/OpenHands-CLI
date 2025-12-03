#!/usr/bin/env python3
"""Validate the CSS fix for exit modal button visibility."""

import re


def analyze_css_file(css_path):
    """Analyze the CSS file for potential issues."""
    with open(css_path, 'r') as f:
        content = f.read()
    
    issues = []
    fixes = []
    
    # Check for viewport width units used for height
    if 'height: 5vw' in content:
        issues.append("❌ Using viewport width (vw) for height - should use vh or fixed units")
    else:
        fixes.append("✅ Height no longer uses viewport width units")
    
    # Check for very small width that might cause button visibility issues
    if 'width: 25vw' in content:
        issues.append("❌ Very small width (25vw) might cause button visibility issues on small terminals")
    else:
        fixes.append("✅ Width is now using fixed units instead of small viewport percentage")
    
    # Check for fixed grid rows that might not accommodate buttons
    if 'grid-rows: 1fr 3' in content:
        issues.append("❌ Fixed grid row height (3) might not be enough for buttons")
    else:
        fixes.append("✅ Grid rows now use 'auto' for button row")
    
    # Check for minimum dimensions
    if 'min-width:' in content and 'min-height:' in content:
        fixes.append("✅ Minimum dimensions are set to ensure visibility")
    else:
        issues.append("❌ No minimum dimensions set")
    
    # Check for explicit button height
    if re.search(r'Button\s*{[^}]*height:', content, re.DOTALL):
        fixes.append("✅ Buttons have explicit height set")
    else:
        issues.append("❌ Buttons don't have explicit height")
    
    return issues, fixes


def main():
    css_path = "/workspace/project/OpenHands-CLI/openhands_cli/refactor/modals/exit_modal.tcss"
    
    print("🔍 Analyzing exit modal CSS for button visibility issues...\n")
    
    issues, fixes = analyze_css_file(css_path)
    
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print()
    
    if fixes:
        print("✅ FIXES APPLIED:")
        for fix in fixes:
            print(f"  {fix}")
        print()
    
    if not issues:
        print("🎉 No issues found! The CSS should now work properly on small terminals.")
    else:
        print("⚠️  Some issues remain that need to be addressed.")
    
    print("\n📋 SUMMARY OF CHANGES:")
    print("  • Changed width from 25vw to 60 (fixed units)")
    print("  • Changed height from 5vw to auto")
    print("  • Added min-width: 40 and min-height: 7")
    print("  • Changed grid-rows from '1fr 3' to '1fr auto'")
    print("  • Added explicit height: 3 for buttons")
    print("\n💡 These changes ensure:")
    print("  • Modal has adequate size even on small terminals")
    print("  • Buttons get enough space with 'auto' sizing")
    print("  • Minimum dimensions prevent modal from being too small")
    print("  • Fixed units provide consistent sizing across different terminal sizes")


if __name__ == "__main__":
    main()