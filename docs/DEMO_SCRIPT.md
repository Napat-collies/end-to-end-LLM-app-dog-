# สคริปต์คลิปเดโม (3–6 นาที, 40 คะแนน)

**เตรียมก่อนอัด**
- รัน `uv run uvicorn app.api.main:app` แล้วเปิด http://127.0.0.1:8000
- เปิด `evaluation/results/retrieval.md` ไว้อีกแท็บ
- **ลองถามทุกคำถามด้านล่างก่อนอัด** เพื่อเลือกเคสที่สำเร็จและเคสที่ผิดจริง ห้ามแต่งผล

| เวลา | ภาพบนจอ | สิ่งที่พูด (แนวทาง) |
|---|---|---|
| 0:00–0:30 | หน้าเว็บ | "This is Dog Breed Advisor. It helps first-time owners choose a breed. It answers descriptive questions from 40 Wikipedia articles with citations, and numeric questions from a database of about 280 breeds. An agent decides which tool to use." |
| 0:30–1:15 | แผนภาพใน README | อธิบายเส้นทาง: คำถาม → agent → dispatcher (allow-list + Pydantic) → 2 tools → คำตอบพร้อมอ้างอิง |
| 1:15–2:00 | **สำเร็จ 1 (RAG):** "What is the temperament of a Shiba Inu?" | ชี้ว่าเรียก `search_breed_docs` มีเลข [1] [2] และกดลิงก์ Wikipedia ให้ดูว่าข้อความตรงกัน |
| 2:00–2:40 | **สำเร็จ 2 (SQL, ภาษาไทย):** "สุนัขพันธุ์ไหนอายุยืนที่สุด ขอ 3 อันดับ" | ชี้ว่าเรียก `query_breeds` และ argument เป็นแบบฟอร์ม ไม่ใช่ SQL พร้อมอธิบายความปลอดภัย 1 ประโยค |
| 2:40–3:30 | **ผิดพลาดจริง** เช่น "What is the temperament of the Xoloitzcuintli?" (ถ้าระบบตอบผิดจริง) | "Here the system fails. This breed is not in my documents, but its similarity score is above my min_score, because it is still about dogs. So it retrieves a different breed. My eval shows the same thing: min_score rejects all off-topic questions but only X of 4 uncovered breeds." |
| 3:30–4:30 | ตารางใน `retrieval.md` | อธิบายตัวเลข 1 ตัวให้ชัด เช่น "Dense retrieval gets Recall@5 of X versus Y for BM25. On Thai questions BM25 gets 0, because Thai words never match English text." และตาราง min_score: "with no floor we reject 0% of unanswerable questions; at 0.X we reject Z%." |
| 4:30–5:00 | - | สรุปข้อจำกัด 1 ข้อ และสิ่งที่จะทำต่อ 1 ข้อ |

**อัปโหลด:** YouTube แบบ Unlisted หรือ Google Drive (ตั้งค่าให้ทุกคนที่มีลิงก์ดูได้) แล้วลองเปิดลิงก์ในโหมด incognito ก่อนส่ง
