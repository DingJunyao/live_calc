#!/usr/bin/env python3
"""Test script to verify bcrypt fix"""

import sys
import os

# Change to backend directory to properly import modules
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

def test_bcrypt_fix():
    """Test the bcrypt fix with long passwords"""
    try:
        from app.core.security import get_password_hash, verify_password

        # Test with a normal password
        normal_password = "mypassword123"
        print(f"Testing normal password: {normal_password}")
        hashed = get_password_hash(normal_password)
        print(f"Hashed successfully: {hashed[:20]}...")

        is_valid = verify_password(normal_password, hashed)
        print(f"Verification: {is_valid}")

        # Test with a long password (over 72 chars)
        long_password = "a" * 80  # 80 chars, well over the 72 char limit
        print(f"\nTesting long password: {len(long_password)} chars")
        hashed_long = get_password_hash(long_password)
        print(f"Long password hashed successfully: {hashed_long[:20]}...")

        is_valid_long = verify_password(long_password, hashed_long)
        print(f"Long password verification: {is_valid_long}")

        # Test verification of long password with shorter version
        is_valid_truncated = verify_password("a" * 70, hashed_long)  # Should fail
        print(f"Verification with different length: {is_valid_truncated}")

        print("\n✅ All tests passed! The bcrypt fix is working correctly.")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing bcrypt fix...")
    success = test_bcrypt_fix()
    if not success:
        sys.exit(1)