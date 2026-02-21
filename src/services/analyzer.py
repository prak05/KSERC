# [Purpose] Analyzer service for compliance checks and gap analysis
# [Source] Logic derived from 'ARA_Autonomous_Regulatory_Compliance.pdf' (Phase 2: Analysis)
# [Why] Performs mathematical precision checks and regulatory compliance analysis

# [Library] typing - Type hints for better code clarity
# [Why] Enables IDE support and type checking
from typing import List, Dict, Any, Tuple, TYPE_CHECKING

# [Optional] pandas - Only needed for response_to_dataframe
# [Why] Avoids hard dependency during runtime unless export is requested
if TYPE_CHECKING:
    import pandas as pd

# [User Defined] Import data models
# [Source] src/models/schemas.py
# [Why] Type-safe data structures
from src.models.schemas import FinancialRow, TruingUpResponse

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Tracking analysis steps
from src.utils.logger import get_logger

# [User Defined] Get logger instance for this module
logger = get_logger(__name__)


# [User Defined] Function to calculate percentage deviation
# [Source] Standard financial analysis formula
# [Why] Shows relative deviation as percentage for better understanding
def calculate_percentage_deviation(arr_value: float, actual_value: float) -> float:
    """
    [Purpose] Calculates percentage deviation from ARR
    [Source] User defined using standard financial formula
    [Why] Percentage gives context - is deviation significant?
    
    [Parameters]
    - arr_value: Approved ARR amount
    - actual_value: Actual trued up amount
    
    [Returns]
    - float: Percentage deviation (positive = overspend, negative = underspend)
    
    [Formula] ((Actual - ARR) / ARR) * 100
    """
    # [Comment] Handle division by zero case
    if arr_value == 0:
        logger.warning("ARR value is zero, cannot calculate percentage")
        return 0.0
    
    # [Comment] Calculate percentage using standard formula
    # [Why] Shows proportion of deviation relative to budget
    percentage = ((actual_value - arr_value) / arr_value) * 100
    
    return round(percentage, 2)  # [Comment] Round to 2 decimal places for readability


# [User Defined] Function to identify significant deviations
# [Source] Regulatory threshold analysis
# [Why] Flags items requiring closer scrutiny
def identify_significant_deviations(
    financial_rows: List[FinancialRow],
    threshold_percentage: float = 10.0
) -> List[Dict[str, Any]]:
    """
    [Purpose] Identifies financial items with significant deviations
    [Source] User defined based on regulatory scrutiny practices
    [Why] Regulators focus on items with large deviations
    
    [Parameters]
    - financial_rows: List of financial line items
    - threshold_percentage: Deviation % threshold (default 10%)
    
    [Returns]
    - List[Dict]: Items exceeding threshold with details
    
    [Regulatory Context]
    Deviations above threshold may require explanation from licensee
    """
    logger.info(f"Analyzing deviations with threshold: {threshold_percentage}%")
    
    # [Comment] Initialize list for significant items
    significant_items = []
    
    # [Comment] Analyze each financial row
    for row in financial_rows:
        # [Comment] Calculate percentage deviation
        percentage_dev = calculate_percentage_deviation(
            row.arr_approved,
            row.trued_up_value
        )
        
        # [Comment] Check if deviation exceeds threshold
        # [Library] abs() - Absolute value (considers both over and under spending)
        # [Why] Both overspending and underspending need scrutiny
        if abs(percentage_dev) > threshold_percentage:
            logger.warning(
                f"Significant deviation found: {row.particulars} "
                f"({percentage_dev}% deviation)"
            )
            
            # [Comment] Add to significant items list with details
            significant_items.append({
                'particulars': row.particulars,
                'arr_approved': row.arr_approved,
                'trued_up_value': row.trued_up_value,
                'deviation': row.deviation,
                'percentage_deviation': percentage_dev,
                'severity': 'HIGH' if abs(percentage_dev) > 20 else 'MEDIUM'
            })
    
    logger.info(f"Found {len(significant_items)} significant deviations")
    return significant_items


# [User Defined] Function to perform compliance checks
# [Source] KSERC regulatory requirements
# [Why] Automated validation against regulatory norms
def perform_compliance_checks(
    response: TruingUpResponse
) -> Dict[str, Any]:
    """
    [Purpose] Performs regulatory compliance checks on analysis
    [Source] User defined based on KSERC regulations
    [Why] Automates compliance verification per regulatory standards
    
    [Parameters]
    - response: Complete truing up response object
    
    [Returns]
    - Dict: Compliance check results with pass/fail status
    
    [Checks Performed]
    1. Mathematical accuracy (totals match)
    2. Significant deviation analysis
    3. Overall surplus/deficit assessment
    """
    logger.info("Starting compliance checks")
    
    # [Comment] Initialize compliance report
    compliance_report = {
        'checks_performed': [],
        'passed_checks': 0,
        'failed_checks': 0,
        'warnings': [],
        'overall_status': 'COMPLIANT'
    }
    
    # [Comment] Check 1: Mathematical Accuracy
    # [Why] Zero-Error Math is key value proposition
    logger.debug("Check 1: Mathematical accuracy")
    
    # [Comment] Verify totals match sum of individual rows
    calculated_arr_total = sum(
        row.arr_approved for row in response.financial_summary
    )
    calculated_actual_total = sum(
        row.trued_up_value for row in response.financial_summary
    )
    
    # [Comment] Allow small floating-point tolerance
    math_check_passed = (
        abs(calculated_arr_total - (response.total_arr_approved or 0)) < 0.01 and
        abs(calculated_actual_total - (response.total_trued_up or 0)) < 0.01
    )
    
    compliance_report['checks_performed'].append({
        'check_name': 'Mathematical Accuracy',
        'status': 'PASS' if math_check_passed else 'FAIL',
        'details': 'All totals verified' if math_check_passed else 'Total mismatch detected'
    })
    
    if math_check_passed:
        compliance_report['passed_checks'] += 1
        logger.info("✓ Mathematical accuracy check: PASSED")
    else:
        compliance_report['failed_checks'] += 1
        compliance_report['overall_status'] = 'NON_COMPLIANT'
        logger.error("✗ Mathematical accuracy check: FAILED")
    
    # [Comment] Check 2: Significant Deviations Analysis
    # [Why] Identifies items requiring regulatory attention
    logger.debug("Check 2: Significant deviations")
    
    significant_deviations = identify_significant_deviations(
        response.financial_summary,
        threshold_percentage=10.0
    )
    
    compliance_report['checks_performed'].append({
        'check_name': 'Significant Deviations',
        'status': 'WARNING' if significant_deviations else 'PASS',
        'details': f'Found {len(significant_deviations)} item(s) with >10% deviation',
        'items': significant_deviations
    })
    
    if significant_deviations:
        compliance_report['warnings'].append(
            f"{len(significant_deviations)} items have significant deviations"
        )
        logger.warning(f"⚠ Found {len(significant_deviations)} significant deviations")
    else:
        compliance_report['passed_checks'] += 1
        logger.info("✓ No significant deviations found")
    
    # [Comment] Check 3: Overall Surplus/Deficit Assessment
    # [Why] Determines if licensee is within acceptable range
    logger.debug("Check 3: Surplus/Deficit assessment")
    
    # [Comment] Analyze net surplus/deficit magnitude
    net_amount = response.net_surplus_deficit
    
    # [Comment] Calculate as percentage of total ARR
    total_arr = response.total_arr_approved or 1.0  # [Comment] Avoid division by zero
    surplus_deficit_percentage = (abs(net_amount) / total_arr) * 100
    
    # [Comment] Define acceptable range (e.g., within ±5% is normal)
    acceptable_range = 5.0
    
    assessment_status = 'PASS'
    assessment_details = f"Net surplus/deficit: ₹{net_amount:.2f} Lakhs ({surplus_deficit_percentage:.2f}% of ARR)"
    
    if surplus_deficit_percentage > acceptable_range:
        assessment_status = 'WARNING'
        compliance_report['warnings'].append(
            f"Net surplus/deficit exceeds {acceptable_range}% of ARR"
        )
        logger.warning(f"⚠ Surplus/deficit {surplus_deficit_percentage:.2f}% exceeds threshold")
    else:
        compliance_report['passed_checks'] += 1
        logger.info("✓ Surplus/deficit within acceptable range")
    
    compliance_report['checks_performed'].append({
        'check_name': 'Surplus/Deficit Assessment',
        'status': assessment_status,
        'details': assessment_details,
        'percentage_of_arr': round(surplus_deficit_percentage, 2)
    })
    
    # [Comment] Generate overall assessment
    logger.info(
        f"Compliance checks complete - "
        f"Passed: {compliance_report['passed_checks']}, "
        f"Failed: {compliance_report['failed_checks']}, "
        f"Warnings: {len(compliance_report['warnings'])}"
    )
    
    return compliance_report


# [User Defined] Function to generate analysis summary
# [Source] Dashboard visualization requirements
# [Why] Provides executive summary for decision makers
def generate_analysis_summary(
    response: TruingUpResponse,
    compliance_report: Dict[str, Any]
) -> Dict[str, Any]:
    """
    [Purpose] Generates executive summary of analysis
    [Source] User defined for dashboard integration
    [Why] Provides quick overview for stakeholders
    
    [Parameters]
    - response: Complete truing up response
    - compliance_report: Results from compliance checks
    
    [Returns]
    - Dict: Executive summary with key insights
    """
    logger.info("Generating analysis summary")
    
    # [Comment] Calculate key statistics
    total_items = len(response.financial_summary)
    
    # [Comment] Count items by deviation direction
    overspent_items = sum(
        1 for row in response.financial_summary if row.deviation > 0
    )
    underspent_items = sum(
        1 for row in response.financial_summary if row.deviation < 0
    )
    
    # [Comment] Calculate largest deviation
    largest_deviation_row = max(
        response.financial_summary,
        key=lambda row: abs(row.deviation),
        default=None
    )
    
    # [Comment] Build summary dictionary
    summary = {
        'licensee_name': response.licensee_name,
        'financial_year': response.financial_year,
        'analysis_date': response.analysis_timestamp.isoformat() if response.analysis_timestamp else None,
        
        'financial_overview': {
            'total_arr_approved': response.total_arr_approved,
            'total_trued_up': response.total_trued_up,
            'net_surplus_deficit': response.net_surplus_deficit,
            'total_line_items': total_items
        },
        
        'deviation_breakdown': {
            'overspent_items': overspent_items,
            'underspent_items': underspent_items,
            'on_budget_items': total_items - overspent_items - underspent_items
        },
        
        'key_insights': {
            'largest_deviation': {
                'particulars': largest_deviation_row.particulars if largest_deviation_row else None,
                'amount': largest_deviation_row.deviation if largest_deviation_row else None
            },
            'compliance_status': compliance_report['overall_status'],
            'warnings_count': len(compliance_report['warnings'])
        },
        
        'compliance_summary': {
            'total_checks': len(compliance_report['checks_performed']),
            'passed': compliance_report['passed_checks'],
            'failed': compliance_report['failed_checks'],
            'warnings': compliance_report['warnings']
        }
    }
    
    logger.info("Analysis summary generated successfully")
    return summary


# [User Defined] Function to convert response to pandas DataFrame
# [Source] Data analysis best practice
# [Why] Enables advanced analysis and export capabilities
def response_to_dataframe(response: TruingUpResponse) -> "pd.DataFrame":
    """
    [Purpose] Converts TruingUpResponse to pandas DataFrame
    [Source] User defined using pandas library
    [Why] DataFrame format enables further analysis and export (Excel, CSV)
    
    [Parameters]
    - response: TruingUpResponse object
    
    [Returns]
    - pd.DataFrame: Financial data in tabular format
    
    [Use Cases]
    - Export to Excel for manual review
    - Further statistical analysis
    - Visualization with matplotlib/seaborn
    """
    logger.debug("Converting response to DataFrame")
    
    # [Comment] Extract data from FinancialRow objects
    data = []
    for row in response.financial_summary:
        # [Comment] Convert each FinancialRow to dictionary
        # [Library] Pydantic model_dump() - Converts model to dict
        # [Why] pandas works with dictionaries
        data.append({
            'Particulars': row.particulars,
            'ARR Approved (Lakhs)': row.arr_approved,
            'Trued Up Value (Lakhs)': row.trued_up_value,
            'Deviation (Lakhs)': row.deviation,
            'Percentage Deviation': calculate_percentage_deviation(
                row.arr_approved,
                row.trued_up_value
            )
        })
    
    # [Library] pandas is imported lazily
    # [Why] Keeps core API usable without pandas installed
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pandas is not installed. Install it with: pip install pandas==2.2.0"
        ) from e

    # [Library] pd.DataFrame() - Create DataFrame from list of dicts
    # [Source] pandas library
    # [Why] Standard way to create pandas DataFrame
    df = pd.DataFrame(data)
    
    logger.info(f"Created DataFrame with {len(df)} rows")
    return df
