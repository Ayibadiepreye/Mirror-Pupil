import re

TP_RE = re.compile(
    r'\b(?:tp|t\.p|t/p|t\s+p|take\s*profit|takeprofit|take-profit|target)(?:\s*\d+)?\s*[:\-.]?\s+([\d.]+)',
    re.IGNORECASE
)

text = "Take Profit: 3981.7185\nTake Profit 2:"

matches = list(TP_RE.finditer(text))
print(f'Found {len(matches)} matches in: {repr(text)}')
print()
for i, m in enumerate(matches):
    print(f'Match {i+1}:')
    print(f'  Full match: "{m.group(0)}"')
    print(f'  Captured value: "{m.group(1)}"')
    print(f'  Position: {m.start()}-{m.end()}')
    print(f'  Has colon: {":"  in m.group(0)}')
    if ':' in m.group(0):
        colon_pos = m.group(0).rfind(':')
        value_start = m.group(0).find(m.group(1))
        print(f'  Colon position: {colon_pos}, Value position: {value_start}')
        print(f'  Value before colon? {value_start < colon_pos}')
    print()
