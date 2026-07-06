# PROJECT_STATE.md — AuditX Capstone

## What this is
Multi-agent AI system (ADK) that analyzes corporate expense data, detects 
fraud/anomaly patterns, and produces a plain-English risk report — while 
masking employee PII before it reaches any LLM. Built for Kaggle's 
"AI Agents: Intensive Vibe Coding Capstone Project," Agents for Business track.

## Key decisions locked in
- Project name: AuditX | Track: Agents for Business | Positioning: fraud & compliance watchdog
- Dataset: data/expenses.csv, seed=42 (FIXED), 617 rows
- CANONICAL numbers: Engineering 95/$83,799.51 | Finance 82/$54,018.37 | 
  Marketing 134/$77,015.96 | Operations 130/$68,043.03 | Sales 176/$121,806.80
- Architecture: real data -> fraud detection (deterministic) -> mask 
  findings -> narrative agent (LLM, masked-only input) -> grounding 
  validation -> unmask -> outputs/audit_report.txt
- UI: Streamlit, dark GitHub-style theme only (no toggle, no Q&A - both removed)
- ⚠️ Gemini free-tier quota: 20 requests/day, resets daily - BUDGET LIVE 
  "Run audit" CLICKS CAREFULLY for remaining prep + recording
- Winning pitch (X-factor): "the AI writing the report never once saw a 
  real employee's name" - security-first framing, provable via 22/22 
  automated tests, not just claimed
- Supporting points: ~15-20hr manual audit reduced to under 1 minute; 
  detection generalized beyond seeded anomalies (found more than planted)
- Deliverable: Kaggle writeup + video + GitHub repo link
- GitHub repo: Auditx-capstone (public, not yet git-initialized/pushed) | 
  OS: Windows 11, Python 3.14.4

## Status log — CODING 100% COMPLETE AND VERIFIED
- [x] All core pipeline components built, tested, verified (22/22 evals)
- [x] Streamlit UI fully working, dark theme only, no toggle/Q&A
- [x] Final verification passed clean, outputs/audit_report.txt freshly 
      confirmed (this is the safety-copy report if quota runs out during recording)
- [x] .env confirmed safe (in .gitignore, git not yet initialized)
- [ ] Architecture diagram finalized for README/writeup — NEXT
- [ ] GitHub README polished
- [ ] Video recorded (budget quota carefully - 20 req/day limit)
- [ ] Kaggle writeup written
- [ ] git init + push to GitHub + Kaggle submission

## Next step
No more coding tasks planned. Sequence: (1) finalize architecture 
diagram, (2) polish README with diagram + results + quickstart, 
(3) record 2-3 min demo video (one clean take if possible, given quota 
limits), (4) write Kaggle writeup using the X-factor pitch above, 
(5) git init + push final repo, (6) submit on Kaggle before July 6, 
11:59 PM PT.