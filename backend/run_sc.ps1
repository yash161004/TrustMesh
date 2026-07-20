echo "=== SELF-CONSISTENCY SAMPLING ===" > sc_results.txt
for ($i=1; $i -le 3; $i++) {
    echo "--- Run $i ---" >> sc_results.txt
    python scripts/run_manipulation_holdout.py --limit 8 --no-cache >> sc_results.txt 2>&1
}
echo "DONE" >> sc_results.txt
