import pytest
from src.agents.auditor import audit_petition

def test_audit_petition_full_integration():
    """
    Test the full auditor agent pipeline with a comprehensive mock state.
    """
    mock_state = {
        "licensee_name": "Technopark",
        "financial_year": "2023-24",
        "claimed_expenses": {
            "power_purchase_cost": 1000.0,
            "employee_cost": 300.0,           # Exceeds MYT norm + CPI/WPI escalation
            "repair_maintenance": 150.0,      # Within norm
            "admin_general": 100.0,
            "depreciation": 200.0,
            "interest_finance": 50.0,
            "return_on_nfa": 80.0,
            "section3_1_duty": 15.0,          # Should be fully disallowed
            "other_expenses": 20.0
        },
        "claimed_revenues": {
            "energy_charges": 1800.0,
            "non_tariff_income": 40.0         # Should be deducted
        },
        "asset_register": [
            {
                "asset_category": "Transformers",
                "gross_value": 1500.0,
                "accumulated_depreciation": 1400.0, # Close to 90% cap (1350)
                "funded_by_grant": False,
                "funded_by_surplus": False,
            }
        ],
        "claimed_distribution_loss_pct": 5.0, # Target is 4.0% for Technopark
        "target_distribution_loss_pct": 4.0,
        "energy_units_purchased_mu": 100.0,
        "power_purchase_cost_rs_per_unit": 5.0, # derived from PPC / MU
        
        "myt_baseline_norms": {
            "employee_cost": 250.0,
            "repair_maintenance": 160.0,
            "admin_general": 110.0
        },
        "prior_approval_status": {
            "New Substation": False
        },
        "precedent_warnings": [
            "Legal fees for non-regulatory matters must be excluded."
        ],
    }
    
    # Run the audit
    result_state = audit_petition(mock_state)
    
    app_exp = result_state["approved_expenses"]
    app_rev = result_state["approved_revenues"]
    disallowances = result_state["disallowance_log"]
    
    # Assertions
    # 1. Section 3(1) Duty should be 0
    assert app_exp.get("section3_1_duty", 0.0) == 0.0
    assert any("Section 3(1)" in d["item"] for d in disallowances)
    
    # 2. O&M Check: Employee Cost should be capped (exact value depends on CPI/WPI, but must be < 300)
    assert app_exp.get("employee_cost", 0.0) < 300.0
    
    # Repair & maintenance should be approved as Claimed since it's within norm
    assert app_exp.get("repair_maintenance", 0.0) == 150.0
    
    # 3. Distribution Loss Penalty (claimed > target)
    assert any("Distribution Loss Penalty" in d["item"] for d in disallowances)
    
    # 4. Depreciation 90% Cap
    # Gross = 1500, Cap = 1350. Acc Dep = 1400. 
    # Current Depl claimed = 200. Allowable = max(0, 1350 - 1400) = 0
    assert any("90% of original capital cost" in d["justification"] for d in disallowances)
    
    # 5. Prior approval check
    assert any("New Substation" in d["justification"] for d in disallowances)
    
    # 6. Precedents check
    assert any("Historical Precedent" in d["item"] for d in disallowances)
    
    # Ensure totals are computed properly
    assert result_state["total_claimed_expenditure"] == sum(mock_state["claimed_expenses"].values())
    assert result_state["total_approved_expenditure"] == sum(app_exp.values())
    assert result_state["total_claimed_revenue"] == sum(mock_state["claimed_revenues"].values())
    assert result_state["total_approved_revenue"] == sum(app_rev.values()) 
