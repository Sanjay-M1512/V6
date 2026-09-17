"""
Seed script: Creates the 3 demo user accounts used by the quick-fill chips
in the index.html Auth Modal, if they don't already exist.
"""
import sys
import os
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\V 6')

from Module2.services.user_service import register_user

DEMO_ACCOUNTS = [
    {"email": "officer@ssb.gov.in",                "role": "SSB",          "password": "SSBSecurePassword!123"},
    {"email": "investigator@trustid.gov.in",        "role": "Investigator", "password": "InvestigatorPass!123"},
    {"email": "admin@trustid.gov.in",               "role": "Admin",        "password": "AdminSecurePassword!123"},
]

print("=" * 60)
print("TRUST-ID — Demo Account Seeder")
print("=" * 60)

for acc in DEMO_ACCOUNTS:
    result, code = register_user(acc["email"], acc["role"], acc["password"])
    if code == 201:
        print(f"[CREATED]  {acc['email']}  ({acc['role']})")
    elif code == 409:
        print(f"[EXISTS]   {acc['email']}  ({acc['role']}) — already in Firestore")
    else:
        print(f"[ERROR]    {acc['email']}  → {result.get('message')}  (code {code})")

print("=" * 60)
print("Done. All demo accounts are ready.")

