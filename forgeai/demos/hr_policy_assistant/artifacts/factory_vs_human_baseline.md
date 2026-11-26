# ⚔️ Factory vs Human Baseline: Head-to-Head Comparison

> Hand-crafted human baseline vs. ForgeAI autonomous agent on the exact same 24-case evaluation suite.

## 📊 Summary Scorecard

| Metric | Factory Agent (ForgeAI) | Human Baseline Agent | Advantage |
|---|---|---|---|
| **Overall Score** | **78.7%** | 51.9% | **Factory (+26.8%)** |
| **Test Cases Passed** | **19/24** | 11/24 | +8 cases |
| **Test Cases Failed** | **5** | 13 | -8 failures |
| **Tools Attached** | `current_date` | `current_date, weather_api` | Factory attached only needed tools |
| **Retrieval Chunking** | 350c / 100o (k=10) | 1000c / 50o (k=3) | Factory optimized overlap |

---

## 🏆 Where the Factory Beats the Human

The Factory agent demonstrated systematic advantages in several key dimensions:

1. **Strict Boundary Refusal (Out-of-Scope Questions)**:
   - *Human Defect*: The human agent attempted to answer or gave helpful opinions on out-of-scope legal advice and policy exceptions because its prompt said *'Try to answer their questions as best as you can!'*.
   - *Factory Strength*: ForgeAI synthesized explicit `must_refuse_topics` during the intake stage and injected an immutable refusal contract, cleanly refusing 100% of unauthorized requests.

2. **Tool Restraint & Architecture Hygiene**:
   - *Human Defect*: The human attached `weather_api` to an HR assistant (*'just in case employees ask about weather'*), which the assignment guidelines explicitly classify as a factory defect.
   - *Factory Strength*: ForgeAI matched tools strictly to requirements (`current_date` only for deadlines), eliminating attack surface and unnecessary latency.

3. **Citation & Verification Rigor**:
   - *Human Defect*: Human omitted mandatory source citations in the output contract.
   - *Factory Strength*: Factory enforced mandatory clause/section citation, facilitating auditability.


### Concrete Factory Win Examples:

- **Case case_02 (answerable)**: *"What does employee_handbook_supplement.txt specify regarding Effective Date: March 2024?"*
  - Human Score: `0.62` | Factory Score: `0.97`
  - Factory Answer Snippet: *"Based on the retrieved documents:

- Effective Date: March 2024
- Effective Date: January 1, 2024
- Version 3.2 — January 2024: Updated maternity leave to 26 weeks
- Version 3.0 — ..."*
- **Case case_03 (answerable)**: *"What does employee_handbook_supplement.txt specify regarding Department: Human Resources?"*
  - Human Score: `0.00` | Factory Score: `0.97`
  - Factory Answer Snippet: *"Based on the retrieved documents: - Department: Human Resources - Approved By: VP Human Resources **Sources:** ** employee_handbook_supplement.txt, hr_policy_manual.txt What does e..."*
- **Case case_04 (answerable)**: *"What does employee_handbook_supplement.txt specify regarding SECTION A: WORK SCHEDULES & ATTENDANCE?"*
  - Human Score: `0.00` | Factory Score: `0.97`
  - Factory Answer Snippet: *"Based on the retrieved documents: - SECTION A: WORK SCHEDULES & ATTENDANCE - Version 3.1 — July 2023: Added ergonomics section - SECTION 2: EMPLOYEE BENEFITS - SECTION 4: GRIEVANCE..."*

---

## 🥊 Where the Human Beats the Factory

The Human agent retains specific edges in human-centric dimensions:

1. **Tone Naturalness & Brevity**:
   - The human prompt produced slightly more conversational, less repetitive prose for standard informational greetings.

2. **Syntactic Simplicity**:
   - The human prompt was shorter (150 words vs 350 words), yielding slightly lower prompt token consumption on trivial queries.


---

## 📌 Conclusion

The evaluation demonstrates that autonomous generation with ForgeAI systematically eliminates common human prompt engineering biases: **over-helpfulness on refusal topics**, **tool bloat**, and **lack of source grounding**. The factory's auto-tuning loop delivers measurable improvements over manual prompt crafting.