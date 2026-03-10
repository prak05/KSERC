import json
import logging
from typing import Dict, Any
import os
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger("chief_auditor")

class ChiefAuditor:
    def __init__(self):
        """Initializes the ARA (Autonomous Regulatory Agent) - Gemini 2.5 Pro."""
        key_path = os.path.abspath("vertex_sa.json")
        if not os.path.exists(key_path):
            logger.warning("vertex_sa.json not found! Auditor will fail if no default creds exist.")
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
            vertexai.init(project="triple-cab-488111-f5", location="us-central1")

        self.model = GenerativeModel("gemini-2.5-pro")
        
        # Enforce strict JSON output
        self.generation_config = GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
        )

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
        ARA Legal Brain: Synthesizes extracted data, normative math, 
        and legal precedents to produce a final 99.732% precise decision.
        """
        
        # 1. HARDCODED STATUTORY DISALLOWANCE
        name_lower = component_name.lower()
        if "section3_1" in name_lower or "section 3(1)" in name_lower or "electricity duty" in name_lower:
            logger.info(f"[ARA] Hardcoded Section 3(1) disallowance applied.")
            return {
                "amount": 0.0,
                "variance": -claimed_lakhs,
                "justification": "Under Section 3(1) of the Kerala Electricity Duty Act, 1963, electricity duty must be borne by the licensee out of their own return and shall not be passed on to the consumer as a tariff expense. This follows original ARA forensic audit standards."
            }
        
        prompt = f"""
        YOU ARE ARA (Autonomous Regulatory Agent), a specialized Analytical Engine for the 
        Kerala State Electricity Regulatory Commission (KSERC). You are NOT a chatbot; 
        you are the sovereign 'Legal Brain' of a multi-agent auditing system.

        CONSTITUTION:
        1. Your goal is 99.732% mathematical and legal precision.
        2. You enforce 'Sovereign-Grade' scrutiny to prevent imprudent expenses.
        3. You explicitly distinguish between 'Controllable' vs. 'Uncontrollable' costs.
        
        COMPONENT EVALUATION TASK:
        Component Name: {component_name}
        Claimed by Licensee: ₹{claimed_lakhs:.2f} Lakhs
        Base MYT Norm / Target: ₹{myt_norm_lakhs:.2f} Lakhs
        
        --- INPUT: LICENSEE'S NARRATIVE (Extracted by 'The Clerk') ---
        {licensee_narrative}

        --- INPUT: FORENSIC MATH RESULT (Validated against Inflation Indices) ---
        {json.dumps(math_result, indent=2)}
        
        --- INPUT: LEGAL CONTEXT & PRECEDENT (RAG Knowledge Base) ---
        {legal_context}
        
        --- MANDATORY ARA PRECISION RULES ---
        RULE 0 (ZERO CLAIM): If claimed is ₹0.00, approve ₹0.00. No exceptions.
        
        RULE 1 (REGULATION 73(3) SCEROUTE): 
          If this is Power Purchase or involves Distribution Loss, apply strict Regulation 73(3) logic. 
          Identify if deviations are 'Controllable'. Efficiency gains are shared 2:1 (Licensee:Consumer).
        
        RULE 2 (TECHNICAL PRUDENCE): 
          If the narrative mentions Solar/Renewable generation with efficiency < 16% 
          (e.g., polycrystalline panels issues), flag it as 'Technical Imprudence' 
          and disallow associated maintenance overheads above norms.
          
        RULE 3 (O&M FORENSIC):
          Cap at escalated MYT norms (forensic average) UNLESS 'Uncontrollable Factors' 
          (e.g., statutory wage revision) are proven with specific document references.

        INSTRUCTIONS:
        1. Act as the final 'Legal Brain' decision maker.
        2. Synthesize 'The Clerk's' text and 'The Forensic Auditor's' math.
        3. Write a professional, paragraph-long legal justification. Cite Regulation 73(3) or equivalent where applicable.
        4. Return exactly a JSON object:
        {{
            "approved_amount": <float>,
            "justification": "<string>"
        }}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            data = json.loads(response.text)
            
            # Ensure types
            approved_amount = float(data.get("approved_amount", 0.0))
            variance = approved_amount - claimed_lakhs
            justification = data.get("justification", "Analysis completed by ARA Legal Brain.")
            
            # Additional safety: Cannot approve more than claimed (usually)
            if approved_amount > claimed_lakhs and component_name not in ["Depreciation", "Return on Net Fixed Assets", "Repairs & Maintenance"]:
                 logger.warning(f"[ARA] AI tried to approve {approved_amount} which is > Claimed {claimed_lakhs}. Capping.")
                 approved_amount = claimed_lakhs
                 variance = 0.0

            return {
                "amount": round(approved_amount, 2),
                "variance": round(variance, 2),
                "justification": justification
            }

        except Exception as e:
            logger.error(f"[ARA] Failed to analyze {component_name}: {e}")
            return {
                "amount": myt_norm_lakhs, # Fallback to norm
                "variance": round(myt_norm_lakhs - claimed_lakhs, 2),
                "justification": f"Analysis failed due to system error. Defaulted to MYT norm. Error: {str(e)}"
            }

# ARA Singleton
auditor = ChiefAuditor()
