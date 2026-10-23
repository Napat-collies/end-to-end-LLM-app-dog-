# Held-out set: manual review

Automatic check: agent 11/20, baseline 4/20. Each agent answer in `agent_heldout_set.json` was then read by hand.
The system was NOT changed after seeing these results.

| id | Question (short) | Auto | Manual | Reason |
|---|---|---|---|---|
| h01 | Breed for a 35 m2 condo | ✓ | ✓ | Grounded recommendation with citations |
| h02 | What to buy before a puppy arrives | ✗ | ✓ | Correct refusal (not in corpus); checker missed the phrasing "นอกเหนือขอบเขต" |
| h03 | House training | ✓ | ✓ | Correct refusal |
| h04 | Toxic human foods | ✗ | ✓ | Correct refusal; checker missed the phrasing |
| h05 | Heaviest breed | ✓ | ✓ | query_breeds, Mastiff |
| h06 | Lightest breed | ✓ | ✓ | query_breeds, Chihuahua |
| h07 | Number of officially recognised breeds | ✗ | ✗ (ambiguous) | Refused without a tool; the database count (283) is not a worldwide official count, so the question is ambiguous |
| h08 | First-year vaccination cost | ✗ | ✓ | Correct refusal; checker missed "ไม่สามารถ" |
| h09 | Teething and chewing | ✗ | ✓ | Correct refusal; checker missed the phrasing |
| h10 | Desk ergonomics (off-topic) | ✓ | ✓ | Refused |
| h11 | French Bulldog vs Corgi for a condo | ✗ | partial | Grounded comparison of exercise needs; barking not covered by the documents and said so |
| h12 | Golden Retriever with children | ✓ | ✓ | Grounded |
| h13 | Husky shedding and double coat | ✓ | ✓ | Grounded |
| h14 | Shiba Inu for first-time owners | ✓ | ✓ | Grounded |
| h15 | Poodle sizes compared | ✗ | partial | General Poodle facts cited; size differences not found and said so |
| h16 | Border Collie energy, owner away all day | ✗ | ✗ | Retrieval miss: Description/Health chunks returned instead of the paragraph on energy |
| h17 | Beagle history and howling | ✓ | ✓ | Grounded |
| h18 | Chihuahua weight, lightest? | ✓ | ✓ | First call rejected (no sort direction), model repaired it on step 2 |
| h19 | Great Dane vs Yorkshire life span | ✗ | ✗ | Regression from the v2 fix: both lookups rejected for missing `descending`; the model gave up instead of repairing |
| h20 | Labrador weight and height | ✓ | ✓ | Weight from the table; height is not in the data |

**Manual total: 15 correct, 2 partial, 3 wrong.**

Proposed fix for h19 (not applied, to keep this set held out): require `descending` only when the
query can return more than one row, i.e. not when filtering by an exact breed name.
