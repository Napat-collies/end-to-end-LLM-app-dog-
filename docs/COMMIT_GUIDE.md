# วิธี commit เป็นขั้นๆ

อาจารย์ให้คะแนน commit history ที่ "แสดงงานที่ค่อยๆ ทำจริง" ดังนั้นอย่า commit ทั้งโปรเจกต์ในครั้งเดียว

ให้เพิ่มไฟล์ทีละกลุ่มตามลำดับนี้ **รันคำสั่งตรวจของแต่ละขั้นให้ผ่านก่อน** แล้วค่อย commit การทำแบบนี้ยังช่วยให้คุณเข้าใจแต่ละส่วนก่อนไปส่วนถัดไป ซึ่งจำเป็นตอนสอบสด

**ครั้งแรก:** `git init` แล้วตรวจด้วย `git status` ว่า `.env` **ไม่**อยู่ในรายการก่อนทุก commit

| # | ไฟล์ที่เพิ่ม (`git add ...`) | ตรวจก่อน commit | ข้อความ commit |
|---|---|---|---|
| 1 | `pyproject.toml uv.lock .gitignore .env.example app/__init__.py app/core scripts/__init__.py scripts/check_connection.py` | `uv run python -m scripts.check_connection` | `Project setup: config, LLM client, connection check` |
| 2 | `data/wiki_breeds.txt scripts/fetch_data.py scripts/build_db.py data/raw` | รัน fetch_data และ build_db แล้วดูค่าตัวอย่าง | `Add data fetch script, raw data and breed database builder` |
| 3 | `app/schemas app/retrieval scripts/build_index.py` | `uv run python -m scripts.build_index` | `Add chunking, bge-m3 embedding cache, dense/BM25/hybrid retrieval` |
| 4 | `evaluation/__init__.py evaluation/metrics.py evaluation/retrieval_set.jsonl evaluation/unanswerable_set.jsonl evaluation/eval_retrieval.py` | `uv run python -m evaluation.eval_retrieval` | `Add retrieval eval set and harness (BM25 baseline, sweeps)` |
| 5 | `app/core/config.py evaluation/results/retrieval.*` (หลังปรับค่าตามผล eval) | รัน eval_retrieval ใหม่ | `Tune chunk size and min_score from eval results` |
| 6 | `app/tools app/services scripts/ask.py` | `uv run python -m scripts.ask "Which 3 breeds are the heaviest?"` | `Add guarded SQL tool, search tool and agent loop with guardrails` |
| 7 | `tests` | `uv run pytest` | `Add offline unit tests for tools, retrieval and agent loop` |
| 8 | `evaluation/agent_set.jsonl evaluation/eval_agent.py evaluation/results/agent.*` | `uv run python -m evaluation.eval_agent` | `Add end-to-end agent eval vs no-tools baseline` |
| 9 | `app/api` | `uv run uvicorn app.api.main:app` แล้วเปิดเว็บ | `Add FastAPI endpoint and web page` |
| 10 | `README.md docs` | อ่าน README ทวนแล้วใส่ตัวเลขผลจริง | `Write README with results and docs` |

ถ้าระหว่างทางแก้บั๊กหรือปรับค่า ให้ commit แยกเป็นครั้งเล็กๆ ได้เลย เช่น `Fix group names in agent eval set` เป็นประวัติที่ดีและแสดงงานจริง

**หลังจบทั้งหมด:** สร้าง repo แบบ Public บน GitHub แล้ว push
```bash
git remote add origin https://github.com/<username>/dog-breed-advisor.git
git branch -M main
git push -u origin main
```
