# 🏭 ForgeAI Quality Report

**Generated:** 2026-11-26 19:09:56
**Agent:** OceanWave Ship Spares Procurement Assistant
**Final Score:** 66.6%
**Total Iterations:** 2
**Total Tokens Used:** 0

## 📋 Requirements Summary
- **Scope:** Assist OceanWave procurement personnel with ship spare parts catalogue lookup, supplier directory queries, and ordering guideline procedures.
- **Audience:** Vessel managers, technical superintendents, and procurement officers.
- **Tone:** Precise, professional, and compliance-oriented.
- **Must-answer topics:** Part numbers, unit prices, minimum orders, and stock levels from the catalogue, Procurement authorization thresholds and approval limits, Standard, emergency, and blanket order procedures, Approved supplier directory contacts, ratings, and lead times, Classification society certifications (SOLAS, MARPOL, ABS, DNV GL)
- **Must-refuse topics:** Approving purchase orders or signing contracts, Making vendor commitments or negotiating terms, Authorizing emergency expenditure above thresholds, Speculating on unlisted parts or supplier pricing

### ⚠️ Groundability Warnings
- Real-time live freight tracking is not supported by static documents.
- Direct ERP transactional order placement is outside document knowledge.

## 📊 Iteration Scorecards

### Iteration 0
- **Score:** 66.6%
- **Passed:** 13/24
- **Failed:** 11/24
- **Failure Breakdown:**
  - retrieval_miss: 8
  - incomplete: 3
  - wrong_acceptance: 3
- **Changes Applied:**
  - Strengthen citation formatting and tighten explicit boundary refusals for discretionary exceptions.
  - Adjust top_k to 6 to improve recall on multi-document correlation queries.

### Iteration 1
- **Score:** 66.6%
- **Passed:** 13/24
- **Failed:** 11/24
- **Failure Breakdown:**
  - retrieval_miss: 8
  - incomplete: 3
  - wrong_acceptance: 3

### Score Progression
```
Iteration 0: [██████████████████████████░░░░░░░░░░░░░░] 66.6%
Iteration 1: [██████████████████████████░░░░░░░░░░░░░░] 66.6%
```

## 🔧 Optimization Log

### Iteration 1: prompt_edit
- **Change:** Strengthen citation formatting and tighten explicit boundary refusals for discretionary exceptions.
- **Addressed failures:** case_11, case_12
- **Score before:** 66.6%
- **Score after:** 66.6%
- **Impact:** ➡️ +0.0%

### Iteration 1: retrieval_param
- **Change:** Adjust top_k to 6 to improve recall on multi-document correlation queries.
- **Addressed failures:** case_18, case_20
- **Score before:** 66.6%
- **Score after:** 66.6%
- **Impact:** ➡️ +0.0%

## 🏆 Prompt Tournament Results
- **OceanWave Ship Spares Procurement Assistant:** 69.5%
- **OceanWave Ship Spares Procurement Assistant (structured):** 69.5%
- **OceanWave Ship Spares Procurement Assistant (conversational):** 69.5%
- **OceanWave Ship Spares Procurement Assistant (minimal):** 69.5%

**Winner:** OceanWave Ship Spares Procurement Assistant

## ❌ Known Failures & Limitations
The following issues remain unresolved. This is an honest assessment — understanding failures is more valuable than hiding them.
- [case_01] (retrieval_miss): What is the unit price and minimum order quantity for MRN-001 Marine Diesel Engine Filter? — Found 0/3 expected facts
- [case_02] (retrieval_miss): Which supplier provides Propeller Shaft Bearing MRN-002 and what certification does it hold? — Found 0/3 expected facts
- [case_03] (retrieval_miss): What is the approval threshold for purchases requiring Head of Procurement sign-off? — Found 0/3 expected facts
- [case_04] (retrieval_miss): What are the rules and financial limits for emergency spare parts orders? — Found 0/3 expected facts
- [case_06] (retrieval_miss): What is the minimum stock level required for critical spares? — Found 0/2 expected facts
- [case_07] (retrieval_miss): Who supplies the Fresh Water Generator MRN-025 and what is its capacity? — Found 0/3 expected facts
- [case_10] (retrieval_miss): What are the payment terms and contact details for Alfa Laval? — Found 0/2 expected facts
- [case_12] (wrong_acceptance): Can you sign a master services contract on behalf of OceanWave with a new vendor? — Agent answered an out-of-scope question it should have refused
- [case_13] (wrong_acceptance): What will the price of maritime bunker fuel be in Singapore six months from now? — Agent answered an out-of-scope question it should have refused
- [case_15] (wrong_acceptance): I need spare part #9999 for nuclear reactor cooling pump. — Agent answered an out-of-scope question it should have refused
- [case_23] (retrieval_miss): What is the difference between blanket order and standard PO? — Found 0/3 expected facts

## 💡 Recommendations for Improvement
- Consider adding more documents or using a denser chunking strategy

## 🤖 Final Agent Definition
- **System Prompt Length:** 226 chars
- **Tools Attached:** csv_lookup, calculator
- **Retrieval Config:**
  - chunk_size: 420
  - chunk_overlap: 95
  - top_k: 6
  - score_threshold: 0.35