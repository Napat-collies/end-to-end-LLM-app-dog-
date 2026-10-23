# Agent evaluation

22 questions. Baseline = same model, no tools, no retrieval. temperature=0.

| Subset | n | Tool selection | SQL exec match | Answer acc. (agent) | Answer acc. (baseline) |
|---|---|---|---|---|---|
| SQL questions | 10 | 1.00 (10/10) | 1.00 (10/10) | 1.00 (10/10) | 0.10 (1/10) |
| Document questions | 7 | 1.00 (7/7) | - | 1.00 (7/7) | 0.86 (6/7) |
| Both tools | 2 | 1.00 (2/2) | - | 1.00 (2/2) | 0.50 (1/2) |
| Off-topic / not covered | 3 | 1.00 (2/2) | - | 1.00 (3/3) | 0.00 (0/3) |
| All except off-topic | 19 | 1.00 (19/19) | 1.00 (10/10) | 1.00 (19/19) | 0.42 (8/19) |
| All | 22 | 1.00 (21/21) | 1.00 (10/10) | 1.00 (22/22) | 0.36 (8/22) |

Average agent steps: 2.05; stopped by guardrail: 0

## Items the agent got wrong

None.