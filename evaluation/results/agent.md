# Agent evaluation

22 questions. Baseline = same model, no tools, no retrieval. temperature=0.

| Subset | n | Tool selection | SQL exec match | Answer acc. (agent) | Answer acc. (baseline) |
|---|---|---|---|---|---|
| SQL questions | 10 | 1.00 (10/10) | 1.00 (10/10) | 1.00 (10/10) | 0.10 (1/10) |
| Document questions | 7 | 0.71 (5/7) | - | 0.71 (5/7) | 0.86 (6/7) |
| Both tools | 2 | 1.00 (2/2) | - | 1.00 (2/2) | 0.50 (1/2) |
| Off-topic / not covered | 3 | 1.00 (2/2) | - | 1.00 (3/3) | 0.00 (0/3) |
| All except off-topic | 19 | 0.89 (17/19) | 1.00 (10/10) | 0.89 (17/19) | 0.42 (8/19) |
| All | 22 | 0.90 (19/21) | 1.00 (10/10) | 0.91 (20/22) | 0.36 (8/22) |

Average agent steps: 1.86; stopped by guardrail: 0

## Items the agent got wrong

### a15: Which famous loyal dog from Japan was an Akita?
- expected tools ['search_breed_docs'], called []; sql_match=None
- gold: None
- agent answer: 'I am sorry, but I could not find that information in the documents.'

### a16: สุนัขพันธุ์บางแก้วมาจากจังหวัดอะไร
- expected tools ['search_breed_docs'], called []; sql_match=None
- gold: None
- agent answer: 'ฉันไม่สามารถค้นหาข้อมูลเกี่ยวกับจังหวัดที่สุนัขพันธุ์บางแก้วมาจากได้ค่ะ ฉันสามารถให้ข้อมูลเกี่ยวกับลักษณะนิสัย ประวัติ การดูแล สุขภาพ หรือการออกกำลังกายของสุนัขพันธุ์ต่างๆ ได้ หากคุณสนใจข้อมูลเหล่านี้ โปรดระบุชื่อสายพันธุ์มาได้เลยค่ะ'
