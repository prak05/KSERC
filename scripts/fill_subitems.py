"""
Fill missing approved sub-items by proportional allocation from claimed values.

When the KSERC order only approves a TOTAL (e.g., R&M = 44.53L) without
individual sub-items, this script derives them proportionally:
  approved_item = (claimed_item / claimed_total) × approved_total

Usage:
    python scripts/fill_subitems.py
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from src.tools.db import get_precedent, save_precedent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

FY = "2023-24"
LICENSEES = ["KDHP", "Technopark", "Infopark"]

# Mapping: (approved_line_items_key, claimed_line_items_key, total_key_in_approved_expenses, gross_key)
SUB_ITEM_GROUPS = [
    ("rm_line_items", "rm_claimed_line_items", "repair_maintenance", "gross_rm_expenses"),
    ("ag_line_items", "ag_claimed_line_items", "admin_general", "gross_ag_expenses"),
    ("employee_line_items", "employee_claimed_line_items", "employee_cost", "gross_employee_expenses"),
]


def proportional_allocate(claimed_items: dict, approved_total: float, gross_key: str) -> dict:
    """
    Given claimed sub-items and an approved total, allocate proportionally.
    
    claimed_items: {item_name: claimed_value, ..., gross_key: claimed_total}
    approved_total: Commission-approved total
    
    Returns: {item_name: approved_value, ..., gross_key: approved_total}
    """
    # Get claimed total from gross key
    claimed_total = float(claimed_items.get(gross_key, 0) or 0)
    if claimed_total <= 0:
        # Sum all non-gross items
        claimed_total = sum(
            float(v or 0) for k, v in claimed_items.items() 
            if k != gross_key and float(v or 0) > 0
        )
    
    if claimed_total <= 0 or approved_total <= 0:
        return {}
    
    ratio = approved_total / claimed_total
    result = {}
    
    for k, v in claimed_items.items():
        v = float(v or 0)
        if k == gross_key:
            result[k] = round(approved_total, 2)
        elif v > 0:
            result[k] = round(v * ratio, 2)
        else:
            result[k] = 0.0
    
    return result


def main():
    for licensee in LICENSEES:
        p = get_precedent(licensee, FY)
        if not p:
            logger.warning(f"{licensee}: No data for FY {FY}")
            continue
        
        ae = p.get("approved_expenses", {})
        updated = False
        
        for approved_key, claimed_key, total_key, gross_key in SUB_ITEM_GROUPS:
            approved_items = p.get(approved_key, {})
            claimed_items = p.get(claimed_key, {})
            approved_total = float(ae.get(total_key, 0) or 0)
            
            # Check if approved sub-items have individual values
            non_gross_approved = {
                k: v for k, v in approved_items.items() 
                if k != gross_key and float(v or 0) > 0
            }
            
            # Check if claimed sub-items have individual values
            non_gross_claimed = {
                k: v for k, v in claimed_items.items()
                if k != gross_key and float(v or 0) > 0
            }
            
            if not non_gross_approved and non_gross_claimed and approved_total > 0:
                # Approved sub-items are empty but claimed has breakdowns + we know the total
                allocated = proportional_allocate(claimed_items, approved_total, gross_key)
                if allocated:
                    p[approved_key] = allocated
                    updated = True
                    logger.info(f"{licensee} {total_key}: Allocated {len(allocated)} sub-items from claimed (ratio={approved_total/sum(float(v or 0) for v in claimed_items.values() if float(v or 0) > 0):.4f})")
                    for k, v in sorted(allocated.items()):
                        if v > 0:
                            logger.info(f"    {k}: {v}")
            elif non_gross_approved:
                logger.info(f"{licensee} {total_key}: Already has {len(non_gross_approved)} approved sub-items ✓")
            elif not non_gross_claimed:
                logger.info(f"{licensee} {total_key}: No claimed sub-items available for allocation")
            elif approved_total <= 0:
                # Try to get total from approved_items gross key
                gt = float(approved_items.get(gross_key, 0) or 0)
                if gt > 0 and non_gross_claimed:
                    allocated = proportional_allocate(claimed_items, gt, gross_key)
                    if allocated:
                        p[approved_key] = allocated
                        updated = True
                        logger.info(f"{licensee} {total_key}: Allocated from gross={gt} (approved_expenses.{total_key} was 0)")
                        for k, v in sorted(allocated.items()):
                            if v > 0:
                                logger.info(f"    {k}: {v}")
                else:
                    logger.warning(f"{licensee} {total_key}: No approved total available")
        
        if updated:
            save_precedent(licensee, FY, p)
            logger.info(f"✓ Updated {licensee} FY {FY}\n")
        else:
            logger.info(f"  {licensee}: No changes needed\n")

    # Final verification
    logger.info("=== FINAL VERIFICATION ===")
    for licensee in LICENSEES:
        p = get_precedent(licensee, FY)
        if not p:
            continue
        for key_name, display in [("rm_line_items", "R&M"), ("ag_line_items", "A&G"), ("employee_line_items", "Employee")]:
            items = p.get(key_name, {})
            nz = {k:v for k,v in items.items() if float(v or 0) > 0}
            print(f"{licensee} {display}: {len(nz)} items - {nz}")


if __name__ == "__main__":
    main()
