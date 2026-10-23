# Agent evaluation

22 questions. Baseline = same model, no tools, no retrieval. temperature=0.

| Subset | n | Tool selection | SQL exec match | Answer acc. (agent) | Answer acc. (baseline) |
|---|---|---|---|---|---|
| SQL questions | 10 | 1.00 (10/10) | 0.90 (9/10) | 0.90 (9/10) | 0.10 (1/10) |
| Document questions | 7 | 0.86 (6/7) | - | 0.71 (5/7) | 0.86 (6/7) |
| Both tools | 2 | 1.00 (2/2) | - | 1.00 (2/2) | 0.50 (1/2) |
| Off-topic / not covered | 3 | 1.00 (2/2) | - | 1.00 (3/3) | 0.00 (0/3) |
| All | 22 | 0.95 (20/21) | 0.90 (9/10) | 0.86 (19/22) | 0.36 (8/22) |

Average agent steps: 1.82; stopped by guardrail: 0

## Items the agent got wrong

### a06: Which breed in the Herding Group is the heaviest?
- expected tools ['query_breeds'], called ['query_breeds']; sql_match=False
- gold: {'names': ['Beauceron'], 'total': 32}
- agent answer: 'The heaviest breed in the Herding Group among the results provided is the Cardigan Welsh Corgi, with a weight range of 11-17 kg.'

### a13: Which country does the Chihuahua come from?
- expected tools ['search_breed_docs'], called ['search_breed_docs']; sql_match=None
- gold: None
- agent answer: 'The Chihuahua is a Mexican breed of toy dog [1].'

### a16: สุนัขพันธุ์บางแก้วมาจากจังหวัดอะไร
- expected tools ['search_breed_docs'], called []; sql_match=None
- gold: None
- agent answer: 'ฉันไม่พบข้อมูลเกี่ยวกับจังหวัดที่สุนัขพันธุ์บางแก้วมาจากในเอกสารที่มีอยู่ค่ะ'
