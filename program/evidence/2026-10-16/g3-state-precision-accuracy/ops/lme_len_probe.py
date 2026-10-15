"""G3 CPU probe (no GPU, no network): LongMemEval-S full-haystack prompt lengths in the
Qwen3.5 tokenizer, for sizing. Text-free output: ids, types, counts."""
import json, sys, time
from datetime import datetime
from transformers import AutoTokenizer

FMT = "%Y/%m/%d (%a) %H:%M"
HEAD = ("Below are your earlier chat sessions with the user, in chronological order, "
        "each with its date.\n\n")
TAIL = ("\n\nCurrent date: {d}\nQuestion: {q}\n\nAnswer the question in one short sentence "
        "based on the chat sessions. If they do not contain the answer, say \"I don't know\".")

def render(rec):
    order = sorted(range(len(rec["haystack_sessions"])),
                   key=lambda i: (datetime.strptime(rec["haystack_dates"][i], FMT), i))
    parts = []
    for n, i in enumerate(order, 1):
        lines = [f"### Session {n} ({rec['haystack_dates'][i]})"]
        for t in rec["haystack_sessions"][i]:
            lines.append(f"{t['role']}: {str(t['content']).strip()}")
        parts.append("\n".join(lines))
    return HEAD + "\n\n".join(parts) + TAIL.format(d=rec["question_date"], q=rec["question"])

t0 = time.time()
data = json.load(open("/inputs/lme.json"))
tok = AutoTokenizer.from_pretrained("/model-cache/cotcodec-models/qwen3.5-9b")
out = []
for rec in data:
    msg = render(rec)
    text = tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    n = len(tok(text, add_special_tokens=False)["input_ids"])
    sorted_already = rec["haystack_dates"] == sorted(rec["haystack_dates"], key=lambda d: datetime.strptime(d, FMT))
    out.append({"qid": rec["question_id"], "type": rec["question_type"],
                "sessions": len(rec["haystack_sessions"]), "chars": len(msg), "tokens": n,
                "dates_sorted": sorted_already})
lens = sorted(o["tokens"] for o in out)
print(json.dumps({"n": len(out), "min": lens[0], "p50": lens[len(lens)//2], "p90": lens[int(.9*len(lens))],
                  "max": lens[-1], "sum": sum(lens), "all_sorted": all(o["dates_sorted"] for o in out),
                  "secs": round(time.time()-t0,1)}))
json.dump(out, open("/outputs/lme-lengths.json", "w"))
