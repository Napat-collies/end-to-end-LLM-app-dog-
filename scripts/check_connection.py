"""ทดสอบ 3 อย่าง: แชท, embedding และ tool calling

รัน:  uv run python -m scripts.check_connection
"""
import json
import math

from openai import APIConnectionError, AuthenticationError

from app.core.config import CHAT_MODEL, EMBED_DIM, EMBED_MODEL
from app.core.llm import get_client


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_chat(client) -> None:
    print("=== 1. Chat ===")
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,  # ให้ผลเหมือนเดิมทุกครั้ง
        messages=[{"role": "user", "content": "In one sentence, what is a Shiba Inu?"}],
    )
    print(resp.choices[0].message.content)


def test_embedding(client) -> None:
    print("\n=== 2. Embedding (Thai question vs English docs) ===")
    query = "สุนัขพันธุ์ไหนเหมาะกับคอนโดเล็กๆ"
    docs = [
        "The French Bulldog is a small, quiet breed well suited to apartment living.",
        "The Siberian Husky needs a lot of space and hours of daily exercise.",
        "The stock market fell sharply today.",
    ]
    resp = client.embeddings.create(model=EMBED_MODEL, input=[query] + docs)
    vecs = [d.embedding for d in resp.data]  # data[i] คู่กับ input[i] เสมอ
    assert len(vecs[0]) == EMBED_DIM, f"expected {EMBED_DIM} dims, got {len(vecs[0])}"
    print(f"dimensions: {len(vecs[0])}")
    for doc, vec in sorted(zip(docs, vecs[1:]), key=lambda p: -cosine(vecs[0], p[1])):
        print(f"  {cosine(vecs[0], vec):.3f}  {doc}")


def test_tool_calling(client) -> None:
    print("\n=== 3. Tool calling ===")
    tools = [{
        "type": "function",
        "function": {
            "name": "get_breed_weight",
            "description": "Look up the typical adult weight range of a dog breed.",
            "parameters": {
                "type": "object",
                "properties": {"breed": {"type": "string", "description": "Breed name"}},
                "required": ["breed"],
            },
        },
    }]
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": "How heavy is an adult Beagle?"}],
        tools=tools,
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        call = msg.tool_calls[0]
        print(f"OK - model called: {call.function.name}")
        try:
            print(f"arguments: {json.loads(call.function.arguments)}")
        except json.JSONDecodeError:
            print(f"WARNING - arguments are not valid JSON: {call.function.arguments!r}")
    else:
        print("WARNING - model answered without calling a tool:")
        print(msg.content)


def main() -> None:
    try:
        client = get_client()
        test_chat(client)
        test_embedding(client)
        test_tool_calling(client)
    except RuntimeError as e:
        print(f"ERROR: {e}")
    except AuthenticationError:
        print("ERROR: API key ไม่ถูกต้อง ตรวจ OPENAI_API_KEY ใน .env")
    except APIConnectionError:
        print("ERROR: เชื่อมต่อ proxy ไม่ได้ ตรวจ OPENAI_BASE_URL ใน .env และอินเทอร์เน็ต")


if __name__ == "__main__":
    main()
