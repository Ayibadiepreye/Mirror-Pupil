#!/usr/bin/env python3
"""
Circular Import Checker for Mirror Pupil Backend
Analyzes import dependencies to identify potential circular import issues.
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import ast


class ImportAnalyzer:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.imports = defaultdict(set)  # file -> set of imported modules
        self.circular_chains = []
        
    def analyze_file(self, filepath):
        """Extract import statements from a Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(filepath))
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                        
            return imports
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
            return set()
    
    def normalize_module(self, module_name, current_file):
        """Convert relative imports to absolute module paths."""
        if module_name.startswith('.'):
            # Relative import
            current_package = current_file.relative_to(self.root_dir).parent
            parts = str(current_package).replace(os.sep, '.').split('.')
            
            # Count leading dots
            level = 0
            for char in module_name:
                if char == '.':
                    level += 1
                else:
                    break
            
            # Go up 'level' directories
            if level > len(parts):
                return None
                
            base_parts = parts[:len(parts) - level + 1]
            rest = module_name.lstrip('.')
            
            if rest:
                return '.'.join(base_parts + [rest])
            else:
                return '.'.join(base_parts)
        else:
            return module_name
    
    def find_circular_imports(self):
        """Find circular import chains using DFS."""
        def dfs(module, path, visited):
            if module in path:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                self.circular_chains.append(cycle)
                return
            
            if module in visited:
                return
            
            visited.add(module)
            path.append(module)
            
            if module in self.imports:
                for imported in self.imports[module]:
                    dfs(imported, path[:], visited)
        
        visited = set()
        for module in self.imports:
            if module not in visited:
                dfs(module, [], visited)
    
    def scan_directory(self, directory):
        """Scan all Python files in backend directory."""
        backend_dir = self.root_dir / directory
        
        for filepath in backend_dir.rglob('*.py'):
            if '__pycache__' in str(filepath):
                continue
                
            rel_path = filepath.relative_to(self.root_dir)
            module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
            
            imports = self.analyze_file(filepath)
            
            for imp in imports:
                normalized = self.normalize_module(imp, filepath)
                if normalized and normalized.startswith('backend'):
                    self.imports[module_path].add(normalized)
    
    def print_report(self):
        """Print analysis report."""
        print("=" * 80)
        print("CIRCULAR IMPORT ANALYSIS FOR MIRROR PUPIL BACKEND")
        print("=" * 80)
        print()
        
        # Print import graph
        print("IMPORT DEPENDENCIES:")
        print("-" * 80)
        for module, imports in sorted(self.imports.items()):
            if imports:
                print(f"\n{module} imports:")
                for imp in sorted(imports):
                    print(f"  → {imp}")
        
        print("\n" + "=" * 80)
        print("CIRCULAR IMPORT DETECTION:")
        print("-" * 80)
        
        if self.circular_chains:
            print(f"\n⚠️  Found {len(self.circular_chains)} potential circular import chain(s):\n")
            for i, chain in enumerate(self.circular_chains, 1):
                print(f"{i}. Circular chain:")
                for j, module in enumerate(chain):
                    if j < len(chain) - 1:
                        print(f"   {module}")
                        print(f"     ↓")
                    else:
                        print(f"   {module} (back to start)")
                print()
        else:
            print("\n✅ No circular imports detected!")
        
        # Check specific patterns that could cause issues
        print("\n" + "=" * 80)
        print("POTENTIAL ISSUES:")
        print("-" * 80)
        
        issues = []
        
        # Check if any route imports from main
        for module, imports in self.imports.items():
            if 'backend.api.routes' in module:
                if 'backend.api.main' in imports:
                    issues.append(f"⚠️  {module} imports from backend.api.main (use dependencies.py instead)")
        
        # Check if core modules import from api
        for module, imports in self.imports.items():
            if 'backend.core' in module:
                for imp in imports:
                    if 'backend.api' in imp and 'backend.api.dependencies' not in imp:
                        issues.append(f"⚠️  {module} imports from {imp} (potential circular import)")
        
        # Check if firebase_auth imports from main
        for module, imports in self.imports.items():
            if 'firebase_auth' in module:
                if 'backend.api.main' in imports:
                    issues.append(f"⚠️  {module} imports from backend.api.main (should use dependencies.py)")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ No obvious import pattern issues detected!")
        
        print("\n" + "=" * 80)


def main():
    script_dir = Path(__file__).parent
    analyzer = ImportAnalyzer(script_dir)
    
    print("Scanning backend directory for Python files...")
    analyzer.scan_directory('backend')
    
    print("Analyzing import dependencies...")
    analyzer.find_circular_imports()
    
    analyzer.print_report()


if __name__ == "__main__":
    main()
