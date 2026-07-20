

echo "=== MAJORITY VOTE ===" > experiment_results.txt
for ($i=1; $i -le 3; $i++) {
    echo "--- Run $i ---" >> experiment_results.txt
    python scripts/run_manipulation_holdout.py --limit 8 --no-cache >> experiment_results.txt 2>&1
}

echo "=== SINGLE MODEL ===" >> experiment_results.txt
for ($i=1; $i -le 3; $i++) {
    echo "--- Run $i ---" >> experiment_results.txt
    python scripts/run_manipulation_holdout.py --limit 8 --no-cache >> experiment_results.txt 2>&1
}

echo "DONE" >> experiment_results.txt
