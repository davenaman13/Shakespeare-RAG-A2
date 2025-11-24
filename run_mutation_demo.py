import subprocess
import sys
import shutil
from pathlib import Path

# --- Configuration for Multiple Files ---
TARGETS = [
    {
        "file": Path("julius_etl/etl_julius.py"),
        "test": ["pytest", "tests/test_etl.py"],
        "mutations": [
            ("AOR: Change split threshold", "WORD_SPLIT_THRESHOLD=900", "WORD_SPLIT_THRESHOLD=999999"),
            ("LCR: Break Roman Logic", "return int(s)", "return int(s) + 1"),
            ("SDL: Delete Sanitization", 'txt = ISOLATED_NUM_RE.sub("", txt)', '# txt = ISOLATED_NUM_RE.sub("", txt)')
        ]
    },
    {
        # 🌟 NEW: Frontend Mutations 🌟
        "file": Path("frontend_ui/frontend.py"),
        "test": ["pytest", "tests/test_frontend.py"],
        "mutations": [
            # 1. Break Payload Construction (API will fail if key is wrong)
            ("ASR: Break Payload Key", '"query": user_query', '"search": user_query'),
            
            # 2. Break Timeout (Performance testing implication)
            ("AOR: Reduce Timeout", 'timeout=90', 'timeout=0.001'),
            
            # 3. Delete Error Handling (Resilience testing)
            ("EHD: Remove raise_for_status", 'response.raise_for_status()', '# response.raise_for_status()')
        ]
    }
]

def run_tests(cmd):
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def main():
    print("🧬 Starting Full-Stack Mutation Testing...\n")
    
    for target in TARGETS:
        file_path = target["file"]
        print(f"📂 Target: {file_path}")
        print(f"{'ID':<4} | {'Mutation Operator':<30} | {'Status':<10} | {'Detail'}")
        print("-" * 65)

        backup_file = file_path.with_suffix(".py.bak")
        shutil.copy(file_path, backup_file)

        try:
            # Check baseline
            if not run_tests(target["test"]):
                print("❌ Baseline tests failed! Skipping this file.")
                continue

            for i, (desc, original, mutant) in enumerate(target["mutations"], 1):
                content = backup_file.read_text(encoding='utf-8')
                if original not in content:
                    print(f"{i:<4} | {desc:<30} | SKIPPED    | Code not found")
                    continue
                
                # Apply Mutation
                file_path.write_text(content.replace(original, mutant), encoding='utf-8')
                
                # Run Test
                killed = not run_tests(target["test"])
                status = "KILLED ✅" if killed else "SURVIVED ❌"
                print(f"{i:<4} | {desc:<30} | {status} | ...")

        finally:
            shutil.copy(backup_file, file_path)
            backup_file.unlink()
            print("\n")

if __name__ == "__main__":
    main()