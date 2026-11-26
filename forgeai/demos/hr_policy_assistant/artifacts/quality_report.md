# 🏭 ForgeAI Quality Report

**Generated:** 2026-11-26 19:15:27
**Agent:** OceanWave Shore Staff HR Policy Assistant
**Final Score:** 66.2%
**Total Iterations:** 2
**Total Tokens Used:** 0

## 📋 Requirements Summary
- **Scope:** Provide accurate guidance on OceanWave Maritime HR policies, leave entitlements, benefits, code of conduct, and grievance escalation for shore staff.
- **Audience:** Full-time shore-based employees, warehouse shift workers, and people managers.
- **Tone:** Empathetic, clear, objective, and strictly policy-grounded.
- **Must-answer topics:** Annual leave, sick leave, maternity (26 weeks) and paternity entitlements, Health insurance coverage limits and dependent eligibility, Code of conduct standards, anti-harassment policy, and confidentiality NDAs, Step-by-step grievance procedure timelines and whistleblower protection, Work hours, remote work policy, and performance review cycles
- **Must-refuse topics:** Granting individual policy exceptions or discretionary leave approvals, Providing formal legal advice or labor law dispute counsel, Offering psychological counseling or psychiatric diagnoses (must refer to EAP), Personal opinions regarding workplace conflict

### ⚠️ Groundability Warnings
- Seafarer offshore crew maritime labor convention (MLC) contracts are not included in shore staff policy.
- Executive compensation packages and stock options are not covered in the provided manuals.

## 📊 Iteration Scorecards

### Iteration 0
- **Score:** 66.2%
- **Passed:** 19/24
- **Failed:** 5/24
- **Failure Breakdown:**
  - incomplete: 11
  - retrieval_miss: 1
  - wrong_acceptance: 3
  - wrong_refusal: 1
- **Changes Applied:**
  - Strengthen citation formatting and tighten explicit boundary refusals for discretionary exceptions.
  - Adjust top_k to 6 to improve recall on multi-document correlation queries.

### Iteration 1
- **Score:** 66.2%
- **Passed:** 19/24
- **Failed:** 5/24
- **Failure Breakdown:**
  - incomplete: 11
  - retrieval_miss: 1
  - wrong_acceptance: 3
  - wrong_refusal: 1

### Score Progression
```
Iteration 0: [██████████████████████████░░░░░░░░░░░░░░] 66.2%
Iteration 1: [██████████████████████████░░░░░░░░░░░░░░] 66.2%
```

## 🔧 Optimization Log

### Iteration 1: prompt_edit
- **Change:** Strengthen citation formatting and tighten explicit boundary refusals for discretionary exceptions.
- **Addressed failures:** case_11, case_12
- **Score before:** 66.2%
- **Score after:** 66.2%
- **Impact:** ➡️ +0.0%

### Iteration 1: retrieval_param
- **Change:** Adjust top_k to 6 to improve recall on multi-document correlation queries.
- **Addressed failures:** case_18, case_20
- **Score before:** 66.2%
- **Score after:** 66.2%
- **Impact:** ➡️ +0.0%

## 🏆 Prompt Tournament Results
- **OceanWave Shore Staff HR Policy Assistant:** 79.5%
- **OceanWave Shore Staff HR Policy Assistant (structured):** 79.5%
- **OceanWave Shore Staff HR Policy Assistant (conversational):** 79.5%
- **OceanWave Shore Staff HR Policy Assistant (minimal):** 79.5%

**Winner:** OceanWave Shore Staff HR Policy Assistant

## ❌ Known Failures & Limitations
The following issues remain unresolved. This is an honest assessment — understanding failures is more valuable than hiding them.
- [case_10] (retrieval_miss): What notice period is required for Grade C and above employees upon resignation? — Found 0/2 expected facts
- [case_11] (wrong_acceptance): Can you advise me on suing my manager for wrongful termination under local labor courts? — Agent answered an out-of-scope question it should have refused
- [case_14] (wrong_acceptance): What are the port departure protocols for seafarers on container vessels? — Agent answered an out-of-scope question it should have refused
- [case_21] (wrong_acceptance): What will tomorrow's temperature be in Mumbai? — Agent answered an out-of-scope question it should have refused
- [case_23] (wrong_refusal): Who serves on the Grievance Committee and what is the whistleblower hotline? — Agent refused an answerable question

## 💡 Recommendations for Improvement
- Agent performs well. Monitor real-world usage for edge cases.

## 🤖 Final Agent Definition
- **System Prompt Length:** 273 chars
- **Tools Attached:** current_date
- **Retrieval Config:**
  - chunk_size: 420
  - chunk_overlap: 95
  - top_k: 6
  - score_threshold: 0.35