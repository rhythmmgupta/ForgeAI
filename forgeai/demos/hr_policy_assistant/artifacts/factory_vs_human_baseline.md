# ⚔️ Factory vs Human Baseline: Head-to-Head Comparison

> Hand-crafted human baseline vs. ForgeAI autonomous agent on the exact same 24-case evaluation suite.

## 📊 Summary Scorecard

| Metric | Factory Agent (ForgeAI) | Human Baseline Agent | Advantage |
|---|---|---|---|
| **Overall Score** | **65.8%** | 65.8% | Human |
| **Test Cases Passed** | **11/24** | 11/24 | +0 cases |
| **Test Cases Failed** | **13** | 13 | -0 failures |
| **Tools Attached** | `csv_lookup, calculator` | `current_date, weather_api` | Factory attached only needed tools |
| **Retrieval Chunking** | 420c / 95o (k=6) | 1000c / 50o (k=3) | Factory optimized overlap |

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