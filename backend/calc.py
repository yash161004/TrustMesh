import re

# Raw experiment dump was archived to docs/qa-history/ in the Phase 0 cleanup.
_RESULTS = '../docs/qa-history/experiment_results.txt'
try:
    content = open(_RESULTS, encoding='utf-16').read()
except UnicodeError:
    content = open(_RESULTS, encoding='utf-8').read()
sections = re.split(r'=== (MAJORITY VOTE|SINGLE MODEL) ===', content)

def parse_section(text):
    runs = re.split(r'--- Run \d ---', text)[1:]
    total_tokens_all = 0
    total_cost_all = 0.0
    for i, run in enumerate(runs, 1):
        costs = [float(c) for c in re.findall(r'cost=\$([0-9.]+)', run)]
        tokens = [int(t) for t in re.findall(r'tokens=(\d+)', run)]
        prec = re.search(r'Precision\s+:\s+([0-9.]+)', run)
        rec = re.search(r'Recall\s+:\s+([0-9.]+)', run)
        f1 = re.search(r'F1 Score\s+:\s+([0-9.]+)', run)
        if prec:
            r_tokens = sum(tokens)
            r_cost = sum(costs)
            total_tokens_all += r_tokens
            total_cost_all += r_cost
            print(f'Run {i}: Precision={prec.group(1)} Recall={rec.group(1)} F1={f1.group(1)} | Tokens={r_tokens} Cost=${r_cost:.6f}')
    print(f'Total for condition -> Tokens: {total_tokens_all}, Cost: ${total_cost_all:.6f}\n')

print('MAJORITY VOTE')
parse_section(sections[2])
print('SINGLE MODEL')
parse_section(sections[4])
