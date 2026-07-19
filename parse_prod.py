import json

with open('qa_lighthouse_prod.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

metrics = data['audits']
for key in ['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift', 'speed-index', 'interactive']:
    if key in metrics:
        print(f"{key}: {metrics[key].get('displayValue', 'N/A')}")

scores = { cat: data['categories'][cat]['score'] * 100 for cat in data['categories'] if data['categories'][cat].get('score') is not None }
print(f'Scores: {scores}')
