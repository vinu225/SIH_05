import os

ignore_dirs = {'.git', 'venv', '__pycache__', '.pytest_cache', 'node_modules', '.vite', 'dist'}

def print_tree(startpath, max_depth=3):
    startpath = os.path.abspath(startpath)
    for root, dirs, files in os.walk(startpath):
        dirs[:] = sorted([d for d in dirs if d not in ignore_dirs])
        files = sorted(files)
        rel = os.path.relpath(root, startpath)
        depth = 0 if rel == '.' else rel.count(os.sep) + 1
        if depth > max_depth:
            continue
        indent = '  ' * depth
        base = os.path.basename(root)
        if rel == '.':
            print("SIH_2/")
        else:
            print(f"{indent}+-- {base}/")
        
        subindent = '  ' * (depth + 1)
        if depth == max_depth:
            if dirs:
                print(f"{subindent}+-- [{len(dirs)} subdirectories: {', '.join(dirs[:5])}]")
            if files:
                print(f"{subindent}+-- [{len(files)} files: {', '.join(files[:5])}...]")
        else:
            shown_files = files[:12]
            for f in shown_files:
                print(f"{subindent}+-- {f}")
            if len(files) > 12:
                print(f"{subindent}+-- ... ({len(files) - 12} more files)")

if __name__ == '__main__':
    print_tree('.', max_depth=3)
