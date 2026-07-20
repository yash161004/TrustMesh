import sys

def apply():
    with open('app/trust/detectors/manipulation.py', 'r') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('        if majority_vote:'):
            start_idx = i
            break
            
    if start_idx == -1:
        print("Could not find start index")
        sys.exit(1)
        
    with open('app/trust/detectors/manipulation_patch.py', 'r') as f:
        patch_content = f.read()
        
    new_lines = lines[:start_idx]
    
    with open('app/trust/detectors/manipulation.py', 'w') as f:
        f.writelines(new_lines)
        f.write(patch_content)
        f.write('\n')
        
    print("Patch applied")

if __name__ == '__main__':
    apply()
