import json
with open('scenarios.json') as f:
    data = json.load(f)
total = len(data)
pdf = [s for s in data if s.get('expected_detector') == 'PolicyDeviationFlagger']
ccc = [s for s in data if s.get('expected_detector') == 'CommitmentConsistencyChecker']
md  = [s for s in data if s.get('expected_detector') == 'ManipulationDetector']
benign = [s for s in data if s.get('expected_detector') is None]
print(f'Total entries: {total}')
print(f'PolicyDeviationFlagger expected_detector: {len(pdf)}')
print(f'CommitmentConsistencyChecker expected_detector: {len(ccc)}')
print(f'ManipulationDetector expected_detector: {len(md)}')
print(f'None (benign): {len(benign)}')
policy = [s for s in data if s['category'] in (0, 4)]
commit = [s for s in data if s['category'] == 0 or s.get('expected_detector') == 'CommitmentConsistencyChecker']
manip  = [s for s in data if s['category'] == 0 or s.get('expected_detector') == 'ManipulationDetector']
print()
print('Per-detector eval count (matching run_benchmark.py routing):')
print(f'PolicyDeviationFlagger: {len(policy)}')
print(f'CommitmentConsistencyChecker: {len(commit)}')
print(f'ManipulationDetector: {len(manip)}')
cat0 = len([s for s in data if s['category'] == 0])
print(f'Benign overlap (cat 0): {cat0} scenarios evaluated by ALL THREE')
