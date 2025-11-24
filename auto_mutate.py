import subprocess
import sys
import shutil
import re
from pathlib import Path

# --- Configuration ---
# Files to mutate and their corresponding tests
TARGETS = [
    {"file": "julius_etl/etl_julius.py", "test": "tests/test_etl_mutation.py"},
    {"file": "api_rag/api_rag.py", "test": "tests/test_api_logic_mutation.py"},
    {"file": "frontend_ui/frontend.py", "test": "tests/test_frontend_mutation.py"}
]

# Regex patterns to find and the mutation to apply
# Format: (Regex Pattern, Replacement, Description)
MUTATION_RULES = [
    (r" == ", " != ", "Flip Equality (== to !=)"),
    (r" != ", " == ", "Flip Inequality (!= to ==)"),
    (r" < ", " >= ", "Boundary Change (< to >=)"),
    (r" > ", " <= ", "Boundary Change (> to <=)"),
    (r" and ", " or ", "Logic Flip (and to or)"),
    (r" or ", " and ", "Logic Flip (or to and)"),
    (r" \+ ", " - ", "Math Flip (+ to -)"),
    (r" - ", " + ", "Math Flip (- to +)"),
    (r"True", "False", "Boolean Flip (True to False)"),
    (r"False", "True", "Boolean Flip (False to True)"),
]

def run_tests(test_cmd):
    """Runs pytest and returns True if passed, False if failed."""
    cmd = f"pytest {test_cmd}"
    result = subprocess.run(
        cmd, 
        shell=True, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def main():
    print("🧬 Starting Automated Mutation Testing Engine...")
    print("=" * 80)
    print(f"{'File':<25} | {'Line':<5} | {'Original':<10} -> {'Mutant':<10} | {'Status'}")
    print("-" * 80)

    total_mutants = 0
    total_killed = 0

    for target in TARGETS:
        file_path = Path(target["file"])
        test_cmd = target["test"]
        
        if not file_path.exists():
            print(f"Skipping {file_path}: Not found.")
            continue

        # 1. Backup original
        backup_file = file_path.with_suffix(".py.bak")
        shutil.copy(file_path, backup_file)
        
        original_lines = file_path.read_text(encoding="utf-8").splitlines()

        try:
            # 2. Scan every line for mutation opportunities
            for line_idx, line_content in enumerate(original_lines):
                # Skip comments and empty lines
                if not line_content.strip() or line_content.strip().startswith("#"):
                    continue

                for pattern, replacement, desc in MUTATION_RULES:
                    # If the pattern exists in the line, mutate it
                    if re.search(pattern, line_content):
                        
                        # Create Mutant Code
                        mutated_line = re.sub(pattern, replacement, line_content, count=1)
                        
                        # Don't mutate if no change (sanity check)
                        if mutated_line == line_content: 
                            continue

                        # Write Mutant to File
                        mutated_file_content = list(original_lines)
                        mutated_file_content[line_idx] = mutated_line
                        file_path.write_text("\n".join(mutated_file_content), encoding="utf-8")

                        # 3. Run Tests against Mutant
                        survived = run_tests(test_cmd)
                        
                        # 4. Report
                        status = "❌ SURVIVED" if survived else "✅ KILLED"
                        original_snippet = re.search(pattern, line_content).group().strip()
                        mutant_snippet = replacement.strip()
                        
                        print(f"{file_path.name:<25} | {line_idx+1:<5} | {original_snippet:<10} -> {mutant_snippet:<10} | {status}")
                        
                        total_mutants += 1
                        if not survived:
                            total_killed += 1

        finally:
            # 5. Restore Original
            shutil.copy(backup_file, file_path)
            backup_file.unlink()

    print("=" * 80)
    if total_mutants > 0:
        score = (total_killed / total_mutants) * 100
        print(f"📊 Final Mutation Score: {score:.2f}% ({total_killed}/{total_mutants} mutants killed)")
    else:
        print("No mutants generated. Check patterns.")

if __name__ == "__main__":
    main()