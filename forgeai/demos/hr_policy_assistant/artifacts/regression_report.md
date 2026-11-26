# 🔄 Document Regression Analysis Report

**Updated Document Folder:** `forgeai/demos/hr_policy_assistant/documents`
**Historical Eval Cases Evaluated:** `24`
**Baseline Score:** `78.7%` → **Post-Update Score:** `78.7%`
**Status:** ✅ No Regressions Detected

## 📊 Score Impact Summary

| Metric | Value |
|---|---|
| Baseline Score | `78.7%` |
| Post-Regeneration Score | `78.7%` |
| Regressed Cases | **0** |
| Improved Cases | 0 |
| Passed Cases | 19/24 |

---

## 🚨 What Broke (Regressions)

No regressions detected! The updated documents did not break existing eval criteria.

---

## 🛠️ Actionable Recommendations

1. **Re-baseline Test Cases**: If document policies intentionally changed (e.g., policy updates or catalogue price changes), the evaluation generator must be rerun to synthesize new gold expected facts.

2. **Check Chunk Overlap**: If failures are categorized as `retrieval_miss`, inspect if new document structure requires adjusting `chunk_size` or `top_k`.