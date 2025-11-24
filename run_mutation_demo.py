import subprocess
import sys
import shutil
from pathlib import Path

# Configuration
TARGET_FILE = Path("julius_etl/etl_julius.py")
TEST_CMD = ["pytest", "tests/test_etl.py"]

# Define Mutations: (Description, Original String, Mutated String)
# We choose mutations that should definitely break your new logic tests.
MUTATIONS = [
    (
        "AOR: Change split threshold",
        "WORD_SPLIT_THRESHOLD=900",
        "WORD_SPLIT_THRESHOLD=999999" 
    ),
    (
        "LCR: Break Roman Numeral Logic",
        "return int(s)",
        "return int(s) + 1"
    ),
    (
        "SDL: Delete Sanitization Step",
        'txt = ISOLATED_NUM_RE.sub("", txt)',
        '# txt = ISOLATED_NUM_RE.sub("", txt)'
    ),
    (
        "RCR: Break Page Logic",
        "if not text:",
        "if text:"
    )
]

def run_tests():
    """Runs pytest and returns True if tests PASS, False if they FAIL."""
    result = subprocess.run(
        TEST_CMD, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def main():
    print(f"🧬 Starting Custom Mutation Testing on {TARGET_FILE}...\n")
    print(f"{'ID':<4} | {'Mutation Operator':<30} | {'Status':<10} | {'Detail'}")
    print("-" * 65)

    # 1. Backup the original file
    backup_file = TARGET_FILE.with_suffix(".py.bak")
    shutil.copy(TARGET_FILE, backup_file)

    try:
        # 2. Initial Clean Run
        if not run_tests():
            print("❌ Baseline tests failed! Fix tests before mutating.")
            sys.exit(1)

        # 3. Apply Mutations
        for i, (desc, original, mutant) in enumerate(MUTATIONS, 1):
            # Read fresh content
            content = backup_file.read_text(encoding='utf-8')
            
            # Inject Mutation
            if original not in content:
                print(f"{i:<4} | {desc:<30} | SKIPPED    | Original code not found")
                continue
            
            mutated_content = content.replace(original, mutant)
            TARGET_FILE.write_text(mutated_content, encoding='utf-8')

            # Run Tests
            tests_passed = run_tests()

            # Analysis: If tests PASS, Mutant SURVIVED (Bad). If tests FAIL, Mutant KILLED (Good).
            status = "SURVIVED" if tests_passed else "KILLED"
            status_icon = "❌" if tests_passed else "✅"
            
            print(f"{i:<4} | {desc:<30} | {status} {status_icon} | Changed '{original[:10]}...'")

    finally:
        # 4. Restore Original File
        shutil.copy(backup_file, TARGET_FILE)
        backup_file.unlink()
        print("-" * 65)
        print("🔄 Restoration complete. Original file restored.")

if __name__ == "__main__":
    main()