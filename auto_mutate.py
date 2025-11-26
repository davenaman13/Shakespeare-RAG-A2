import ast
import subprocess
import shutil
import os
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TARGETS = {
    "julius_etl/etl_julius.py": "tests_mutation/test_etl_mutation.py",
    "api_rag/api_rag.py": "tests_mutation/test_api_logic_mutation.py",
    "frontend_ui/frontend.py": "tests_mutation/test_frontend_mutation.py"
}

class MutationManager(ast.NodeTransformer):
    """
    Dual-purpose class:
    1. Mode 'scan': Counts and describes potential mutants.
    2. Mode 'apply': Applies exactly ONE mutation at the given index.
    """
    def __init__(self, mode="scan", target_idx=-1):
        self.mode = mode
        self.target_idx = target_idx
        self.counter = 0
        self.mutants_log = []

    def _mutate(self, old_node, new_node, desc):
        """Helper to handle the mutation logic based on mode."""
        if self.mode == "scan":
            self.mutants_log.append({"line": getattr(old_node, 'lineno', 0), "desc": desc})
            return old_node
        
        if self.mode == "apply":
            if self.counter == self.target_idx:
                self.counter += 1
                # Copy location info to ensure valid AST
                return ast.copy_location(new_node, old_node)
            self.counter += 1
            return old_node

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            return self._mutate(node, ast.BoolOp(op=ast.Or(), values=node.values), "and -> or")
        elif isinstance(node.op, ast.Or):
            return self._mutate(node, ast.BoolOp(op=ast.And(), values=node.values), "or -> and")
        return self.generic_visit(node)

    def visit_UnaryOp(self, node):
        # Critical fix: Transforming UnaryOp -> Name (Node Type Change)
        if isinstance(node.op, ast.Not):
            return self._mutate(node, node.operand, "not x -> x")
        return self.generic_visit(node)

    def visit_If(self, node):
        # Process child nodes first (depth-first)
        processed_node = self.generic_visit(node)
        
        # Then inject Control Flow mutants for the If statement itself
        # 1. Force True
        true_node = ast.If(test=ast.Constant(value=True), body=node.body, orelse=node.orelse)
        res = self._mutate(processed_node, true_node, "if X -> if True")
        if res is not processed_node: return res # Return immediately if mutation applied
        
        # 2. Force False
        false_node = ast.If(test=ast.Constant(value=False), body=node.body, orelse=node.orelse)
        return self._mutate(processed_node, false_node, "if X -> if False")

    def visit_Call(self, node):
        if node.keywords:
            new_keywords = [k for k in node.keywords if k.arg != 'timeout']
            if len(new_keywords) < len(node.keywords):
                new_node = ast.Call(func=node.func, args=node.args, keywords=new_keywords)
                return self._mutate(node, new_node, "remove timeout arg")
        return self.generic_visit(node)

    def visit_Compare(self, node):
        # Create mutant node with flipped operators
        new_ops = []
        desc = ""
        for op in node.ops:
            if isinstance(op, ast.Eq): new_ops.append(ast.NotEq()); desc = "== -> !="
            elif isinstance(op, ast.NotEq): new_ops.append(ast.Eq()); desc = "!= -> =="
            elif isinstance(op, ast.Lt): new_ops.append(ast.GtE()); desc = "< -> >="
            elif isinstance(op, ast.Gt): new_ops.append(ast.LtE()); desc = "> -> <="
            elif isinstance(op, ast.Is): new_ops.append(ast.IsNot()); desc = "is -> is not"
            elif isinstance(op, ast.IsNot): new_ops.append(ast.Is()); desc = "is not -> is"
            else: new_ops.append(op)
        
        if desc:
            new_node = ast.Compare(left=node.left, ops=new_ops, comparators=node.comparators)
            return self._mutate(node, new_node, desc)
        return self.generic_visit(node)

def run_tests(test_file):
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-x", "-q", "--disable-warnings"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.returncode != 0 

def process_file(source_file, test_file):
    print(f"\nScanning {source_file}...")
    with open(source_file, "r", encoding="utf-8") as f:
        source_code = f.read()
    
    # 1. Scan phase
    scanner = MutationManager(mode="scan")
    tree = ast.parse(source_code)
    scanner.visit(tree)
    mutants = scanner.mutants_log
    print(f"Found {len(mutants)} mutation points.")
    
    killed = 0
    survived = 0
    shutil.copy(source_file, source_file + ".bak")
    
    try:
        # 2. Apply phase (Iterate by index)
        for i, m in enumerate(mutants):
            # Parse fresh tree
            clean_tree = ast.parse(source_code)
            
            # Apply specific mutation by index
            applier = MutationManager(mode="apply", target_idx=i)
            mutated_tree = applier.visit(clean_tree)
            
            # Write to disk
            with open(source_file, "w", encoding="utf-8") as f:
                f.write(ast.unparse(mutated_tree))
            
            # Run Test
            if run_tests(test_file):
                print(f"  Mutant {i+1:<3} | Line {m['line']:<4} | {m['desc']:<20} | ✅ KILLED")
                killed += 1
            else:
                print(f"  Mutant {i+1:<3} | Line {m['line']:<4} | {m['desc']:<20} | ❌ SURVIVED")
                survived += 1
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        shutil.copy(source_file + ".bak", source_file)
        os.remove(source_file + ".bak")
        
    return killed, survived

def main():
    print("🧬 Starting Industrial-Grade AST Mutation Engine...")
    total_k, total_s = 0, 0
    for src, tst in TARGETS.items():
        if os.path.exists(src) and os.path.exists(tst):
            k, s = process_file(src, tst)
            total_k += k; total_s += s
        else:
            print(f"Skipping {src} (File not found)")
            
    total = total_k + total_s
    if total > 0:
        print(f"\n📊 Final Score: {(total_k/total)*100:.2f}% ({total_k}/{total} Killed)")

if __name__ == "__main__":
    main()