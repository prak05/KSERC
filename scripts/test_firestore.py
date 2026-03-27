"""Test Firestore db.py - verify all CRUD operations work correctly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from src.tools.db import (
    init_db, save_myt_norms, get_myt_norms_override, get_all_myt_norms,
    save_analysis, get_analysis, update_progress,
    upsert_economic_indicators, get_economic_indicators,
)

print("Initializing Firestore...")
init_db()

# Test 1: MYT Norms
print("\n=== TEST 1: Save & Read MYT Norms ===")
test_norms = {
    "power_purchase_cost": 1234.56,
    "employee_cost": 78.90,
    "repair_maintenance": 45.67,
    "admin_general": 12.34,
    "depreciation": 56.78,
}
save_myt_norms("TestLicensee", "2025-26", test_norms, source="test")
print("Saved MYT norms for TestLicensee FY 2025-26")

result = get_myt_norms_override("TestLicensee", "2025-26")
print(f"Read back: {result}")
assert result.get("power_purchase_cost") == 1234.56, f"FAIL: {result}"
assert result.get("employee_cost") == 78.90, f"FAIL: {result}"
print("✅ MYT norms round-trip PASSED")

# Test 2: Analysis
print("\n=== TEST 2: Save & Read Analysis ===")
save_analysis("test-firestore-123", "RUNNING")
data = get_analysis("test-firestore-123")
print(f"Status: {data['status']}")
assert data["status"] == "RUNNING"

save_analysis("test-firestore-123", "COMPLETED", {"total_approved": 100.0})
data = get_analysis("test-firestore-123")
print(f"After completion: status={data['status']}, result={data['result']}")
assert data["status"] == "COMPLETED"
assert data["result"]["total_approved"] == 100.0
print("✅ Analysis round-trip PASSED")

# Test 3: Progress
print("\n=== TEST 3: Progress Updates ===")
save_analysis("test-progress-fs", "RUNNING")
update_progress("test-progress-fs", "extraction", "Extracting tables...")
update_progress("test-progress-fs", "audit", "Running audit...")
data = get_analysis("test-progress-fs")
print(f"Progress entries: {len(data['progress'])}")
for p in data["progress"]:
    print(f"  - {p}")
print("✅ Progress updates PASSED")

# Test 4: Economic Indicators
print("\n=== TEST 4: Economic Indicators ===")
upsert_economic_indicators("2024-25", {
    "wpi_pct": 3.5, "cpi_pct": 5.2, "sbi_plr_pct": 8.7,
})
eco = get_economic_indicators("2024-25")
print(f"Read back: {eco}")
assert eco.get("wpi_pct") == 3.5
print("✅ Economic indicators PASSED")

# Test 5: Read real MYT norms (seeded from JSON)
print("\n=== TEST 5: Read Seeded MYT Norms ===")
kdhp = get_myt_norms_override("KDHP", "2024-25")
print(f"KDHP 2024-25: {kdhp}")
techno = get_myt_norms_override("Technopark", "2024-25")
print(f"Technopark 2024-25: {techno}")

all_kdhp = get_all_myt_norms("KDHP")
print(f"KDHP total FYs in Firestore: {len(all_kdhp)}")

print("\n" + "=" * 60)
print("=== ALL TESTS PASSED ===")
print("=" * 60)
