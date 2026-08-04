"""Wrap remaining store message mutators with thread-aware commit."""
from pathlib import Path

path = Path("e:/WORK/CODE/ims-ai-desktop/apps/desktop/src/components/AiAssistant/store.ts")
text = path.read_text(encoding="utf-8")

needle = "set((s) => ({\n          messages: s.messages.map("
count = 0
while True:
    idx = text.find(needle)
    if idx < 0:
        break
    obj_start = text.find("{", idx)
    depth = 0
    i = obj_start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                obj_end = i
                break
        i += 1
    else:
        raise SystemExit("unbalanced braces")

    obj_body = text[obj_start + 1 : obj_end]
    body = obj_body.strip()
    if not body.startswith("messages: s.messages.map("):
        raise SystemExit(f"unexpected body start: {body[:80]!r}")
    if body.endswith(","):
        body = body[:-1].rstrip()
    map_expr = body[len("messages: ") :]
    if not map_expr.startswith("s.messages.map("):
        raise SystemExit("map expr mismatch")
    inner_map = "base.map(" + map_expr[len("s.messages.map(") :]

    replacement = (
        "set((s) => {\n"
        "          const { threadId, messages: base } = baseMessagesForWrite(s);\n"
        "          return commitThreadMessages(s, threadId, "
        + inner_map
        + ");\n"
        "        })"
    )

    # set((s) => ({ ... }))  → after object `}` comes `))`
    close = text[obj_end + 1 : obj_end + 3]
    if close != "))":
        raise SystemExit(f"expected )) after object, got {close!r} at {obj_end}")
    end = obj_end + 3
    text = text[:idx] + replacement + text[end:]
    count += 1

path.write_text(text, encoding="utf-8")
print(f"wrapped {count} mutators")
print("commitThreadMessages count:", text.count("commitThreadMessages"))
print("remaining s.messages.map:", text.count("s.messages.map"))
