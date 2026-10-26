# Truing-Up Calculations & Analysis

## Key Metrics and Formulas

- **Revenue Gap/Surplus:** Calculate as **(Approved ARR – Actual Revenue)**【2†L13-L16】. For example, if approved ARR is ₹100 Cr and actual revenue is ₹90 Cr, the gap is ₹10 Cr. A positive result is a *gap*; a negative result is a *surplus*.  
- **Power Purchase Validation:** Compare **actual power purchase cost** and per-unit rates against the approved/estimated values. Use ratios and differences to spot anomalies (e.g. cost/unit significantly above norm). Flag large spikes for review.  
- **AT&C Loss:** Compute as  
  \[
  AT\&C\ Loss = \frac{\text{Energy Input} - \text{Energy Realized}}{\text{Energy Input}}.
  \]  
  Track year-on-year changes. Anomalies (e.g. sudden jump) may indicate metering or reporting issues.  
- **Anomaly Detection:** Use statistical methods (e.g. Z-scores, regression) on cost/revenue series. For instance, if *employee cost* jumps 40% but connected consumers grew 5%, this deviation would be flagged. These methods automate “prudence checks” for each cost element.

Each metric should be calculated for the truing-up year and compared with historical trends and approved norms. The AI tool would ingest data (audited accounts, ARR orders, past truing-up) and apply these formulas to generate reports.

## Historical Extremes (KSERC Truing-Up Cases)

Looking at past KSERC orders, we see extreme outcomes:

- **Largest Approved Surpluses:**  
  - *Technopark (FY2020-21):* Commission approved a huge surplus of **₹280.42 lakh**【77†L1839-L1842】.  
  - *CSEZA (FY2022-23):* Approved surplus of **₹135.14 lakh**【68†L1124-L1131】.  
  - *Kanan Devan (FY2022-23):* Approved surplus **₹116.91 lakh**【45†L1491-L1494】.  
- **Largest Approved Deficits (Gaps):**  
  - *Infopark (FY2020-21):* Commission approved a gap of **₹60.80 lakh**【14†L1111-L1118】 (licensee had asked for ₹76.53 lakh).  
- **Significant Rejections (Disallowances):** In many cases the Commission reduced the claimed gap. E.g. Infopark asked for ₹76.53 lakh but was granted only ₹60.80 lakh【14†L1111-L1118】; similarly, Infopark asked ₹79.76 lakh (FY2024-25) and was granted ₹64.72 lakh【7†L1343-L1350】.  
- **“Overshoot” Decisions:** Sometimes the Commission granted more than asked. Notably, *CSEZA (FY2023-24)*: licensee claimed a **small deficit** (–₹3.42 lakh) but KSERC approved a **large surplus** of **₹87.85 lakh**【26†L1090-L1094】. Likewise, *Kanan Devan (FY2021-22)* asked for a surplus of ₹13.61 lakh and got **₹58.72 lakh**【41†L1396-L1402】. These reversals illustrate how the AI must consider both licensee claims and regulatory judgment.

In summary, the tool’s calculations should be checked against such benchmarks: e.g. no historical surplus exceeded ₹280 lakh, and the largest gaps were on the order of ₹60 lakh. The AI should also learn patterns (e.g. caps on allowed cost items) from past decisions.

## AI Architecture (“Brain”) Recommendation

For an **intelligent truing-up tool**, use a hybrid LLM+retrieval system. In practice, this means a **Retrieval-Augmented Generation (RAG)** architecture【79†L247-L254】【81†L158-L166】.  Steps include: 

- **Knowledge Base:** Index all KSERC regulations, tariff orders, past truing-up orders, etc. into a vector database. This anchors reasoning in authoritative text.  
- **Retrieval:** For each claim (e.g. a cost item in uploaded accounts), retrieve relevant regulations or past findings. RAG methods ensure outputs are grounded in source documents【79†L247-L254】.  
- **Reasoning Module:** Use a large language model (LLM) or chain-of-thought prompts (e.g. via LangChain) to apply business rules to the data. For example, the LLM can “reason” that a 50% jump in power purchase cost vs only 10% load growth is suspicious, referencing related clauses.  
- **Traceability:** Follow an industrial RAG pattern: each answer cites specific clauses/order excerpts【79†L247-L254】【81†L158-L166】. This mirrors a regulator’s analysis and allows auditing.  

Studies confirm RAG is the state-of-art for regulatory compliance tasks: it “grounds model outputs in authoritative sources” and mitigates hallucinations【81†L158-L166】. A lightweight open LLM (like LLaMA2, Mistral, or an openGPT) can be used with vector retrieval. Optionally, an agent framework (e.g. LangChain) can orchestrate reading the PDF filings, retrieving rules, and computing checks. This AI “brain” thus emulates KSERC’s prudence checks in a scalable way, using learned logic from historical decisions to automatically approve or flag each line item【79†L247-L254】【81†L158-L166】.

**Sources:** Official KSERC tariff and truing-up orders (see citations) and AI literature on RAG【79†L247-L254】【81†L158-L166】.