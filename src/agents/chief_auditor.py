import json
import logging
from typing import Dict, Any

from src.gemini_client import generate

logger = logging.getLogger("chief_auditor")

class ChiefAuditor:
    def __init__(self):
        """Initializes the Gemini 2.5 Pro Chief Auditor."""
        # Client is initialized lazily via gemini_client on first generate() call
        pass

    def analyze_component(
        self, 
        component_name: str, 
        claimed_lakhs: float, 
        myt_norm_lakhs: float, 
        math_result: Dict[str, Any], 
        legal_context: str,
        licensee_narrative: str = "No narrative provided."
    ) -> Dict[str, Any]:
        """
        Synthesizes the Claimed amount, MYT Norm, deterministic Math Result, 
        and RAG Legal Context to produce the final approved value and justification.
        """
        
        # 1. HARDCODED STATUTORY DISALLOWANCE
        name_lower = component_name.lower()
        if "section3_1" in name_lower or "section 3(1)" in name_lower or "electricity duty" in name_lower:
            logger.info(f"[{component_name}] Hardcoded Section 3(1) disallowance applied.")
            return {
                "amount": 0.0,
                "variance": -claimed_lakhs,
                "justification": "Under Section 3(1) of the Kerala Electricity Duty Act, 1963, electricity duty must be borne by the licensee out of their own return and shall not be passed on to the consumer as a tariff expense. Therefore, this amount is entirely disallowed."
            }
        
        prompt = f"""
        You are the Chief Auditor for the Kerala State Electricity Regulatory Commission (KSERC).
        You are evaluating a single financial component from a True-Up petition.

        Component Name: {component_name}
        Claimed by Licensee: ₹{claimed_lakhs:.2f} Lakhs
        Base MYT Norm / Target: ₹{myt_norm_lakhs:.2f} Lakhs
        
        --- LICENSEE'S NARRATIVE JUSTIFICATION ---
        This is the Licensee's exact textual justification for why they are claiming this amount:
        {licensee_narrative}

        --- DETERMINISTIC MATH CALCULATOR RESULT ---
        This is the mathematically correct baseline limit derived by the Python engine
        (includes MYT norm, CPI/WPI escalation at actual blended rate, and penalty adjustments):
        {json.dumps(math_result, indent=2)}
        
        --- LEGAL RESEARCHER (RAG) CONTEXT & PRECEDENT ---
        These are exact regulations and past KSERC rulings governing this component:
        {legal_context}
        
        --- COMPONENT-SPECIFIC RULES (MANDATORY — Apply these first) ---
        
        RULE 0 — ZERO CLAIM: If the claimed amount is ₹0.00, the Licensee has made NO claim.
          You MUST approve ₹0.00. Do NOT substitute the MYT norm value. Explain this as "No claim made by the Licensee."
        
        RULE 1 — EMPLOYEE COST:
          The MYT Norm is the base cap (escalated at actual CPI/WPI blended rate).
          HOWEVER, if the Licensee explicitly mentions any of the following, grant a partial override above the norm:
          - State Government Pay Revision / DA revision order
          - Wage Board revision
          - Court-ordered salary reinstatement
          - New medical scheme (GPAIS, KSFE)
          - Increased workload due to new area/phase addition (with specific headcount data)
          The override must be proportional to the specific cited impact. Do NOT grant a full override for generic claims.
        
        RULE 2 — DEPRECIATION:
          Depreciation is calculated on actual Gross Fixed Assets (GFA) based on audited accounts.
          If claimed < MYT norm, approve claimed (actual is correct). If claimed > MYT norm, verify if new assets
          were commissioned; if so, approve the higher amount. Do NOT cap depreciation arbitrarily.
        
        RULE 3 — RETURN ON NET FIXED ASSETS (RoNFA):
          RoNFA = 5.5% × Opening NFA. The MYT order fixes the approved NFA trajectory.
          If the Licensee's claimed NFA significantly differs from the MYT-approved NFA trajectory without
          evidence of new capital investment, restrict to the MYT-approved RoNFA.
        
        RULE 4 — INTEREST ON CONSUMER SECURITY DEPOSITS:
          This is directly linked to the bank rate on April 1st of the FY. If the actual bank rate
          changed significantly from the MYT assumption, the Commission may admit the full claimed amount, up to the prudent SBI benchmark.
        
        RULE 5 — REPAIRS & MAINTENANCE (ONE-TIME EXCEPTION):
          The strict escalated MYT norm applies to the existing network. HOWEVER, if the Licensee's 
          narrative explicitly justifies excess R&M costs due to newly commissioned infrastructure 
          (e.g., "Phase-IV", "new campus") or a major unforeseen "one-time breakdown", the Commission allows exceptions. 
          You MUST isolate those specific extraordinary costs and add them ON TOP of the escalated MYT norm.
          
        INSTRUCTIONS:
        1. Apply the COMPONENT-SPECIFIC RULES above first.
        2. Then use the Deterministic Math Result as the baseline.
           HOWEVER, you have DISCRETIONARY AUTHORITY to OVERRIDE the math cap if the Licensee's Narrative
           provides a highly compelling, reasonable, or extraordinary operational justification.
           *CRITICAL PRUDENCE CHECK*: If an excuse is compelling, DO NOT blindly approve the entire claimed amount.
           Estimate the specific financial impact of the valid excuse only. Base + Justified Variance = Approved.
           Any unexplained remainder is disallowed. If the excuse is weak or generic, enforce the math limit exactly.
        3. Write a professional, paragraph-long legal justification. Cite the specific regulation clause.
           If you override the math limit, explicitly state why and how you determined the proportion.
        4. Explain any disallowances (Claimed - Approved).

        Return exactly a JSON object:
        {{
            "approved_amount": <float>,
            "justification": "<string>"
        }}
        """

        try:
            from src.models.schemas import AuditorDecision
            raw = generate(
                prompt,
                model="gemini-2.5-pro",  # Fast structured JSON — no AFC loops needed
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=AuditorDecision,
            )
            data = json.loads(raw)
            
            # Ensure types
            approved_amount = float(data.get("approved_amount", 0.0))
            variance = approved_amount - claimed_lakhs
            justification = data.get("justification", "Analysis completed.")
            
            # Additional safety: Cannot approve more than claimed (usually)
            if approved_amount > claimed_lakhs and component_name not in ["Depreciation", "Return on Net Fixed Assets", "Repairs & Maintenance"]:
                 logger.warning(f"[{component_name}] AI tried to approve {approved_amount} which is > Claimed {claimed_lakhs}. Capping.")
                 approved_amount = claimed_lakhs
                 variance = 0.0

            return {
                "amount": round(approved_amount, 2),
                "variance": round(variance, 2),
                "justification": justification
            }

        except Exception as e:
            logger.error(f"[ChiefAuditor] Failed to analyze {component_name}: {e}")
            raise  # Let the caller (pipeline) handle it — no silent fallbacks

# Singleton instance
auditor = ChiefAuditor()
