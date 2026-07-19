import json
with open('qa_lighthouse.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
metrics = data['audits']
for key in ['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift', 'speed-index', 'interactive']:
    if key in metrics:
        print(f"{key}: {metrics[key].get('displayValue', 'N/A')}")
print('\nTop Opportunities:')
for key, audit in metrics.items():
    if audit.get('details') and audit['details'].get('type') == 'opportunity' and audit.get('score', 1) < 1:
        print(f"- {audit.get('title')}: {audit.get('displayValue', '')}")
