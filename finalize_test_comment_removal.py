#!/usr/bin/env python3
"""
Final script to remove all remaining comments and docstrings from test files.
This script processes all test files and ensures complete removal of:
- Module-level docstrings
- Function/method docstrings
- Class docstrings
- Inline # comments
- TODO/FIXME/BUG markers
"""

import re
from pathlib import Path

def remove_all_comments(content):
    lines = content.split('\n')
    result = []
    in_docstring = False
    docstring_delimiter = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        if in_docstring:
            if docstring_delimiter in line:
                end_idx = line.find(docstring_delimiter)
                remainder = line[end_idx + len(docstring_delimiter):]
                if not remainder.strip():
                    in_docstring = False
                    docstring_delimiter = None
                    i += 1
                    continue
                else:
                    in_docstring = False
                    docstring_delimiter = None
            i += 1
            continue

        if stripped.startswith('"""') or stripped.startswith("'''"):
            delimiter = '"""' if stripped.startswith('"""') else "'''"

            remaining = stripped[len(delimiter):]
            if delimiter in remaining:
                end_pos = remaining.find(delimiter)
                after_end = remaining[end_pos + len(delimiter):]
                if not after_end.strip():
                    i += 1
                    continue
            else:
                in_docstring = True
                docstring_delimiter = delimiter
                i += 1
                continue

        if stripped.startswith('#'):
            i += 1
            continue

        clean_line = line
        if '#' in line:
            in_string = False
            string_char = None
            escape_next = False
            chars = []

            for char in line:
                if escape_next:
                    chars.append(char)
                    escape_next = False
                    continue

                if char == '\\' and in_string:
                    chars.append(char)
                    escape_next = True
                    continue

                if char in ('"', "'"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                    chars.append(char)
                elif char == '#' and not in_string:
                    break
                else:
                    chars.append(char)

            clean_line = ''.join(chars).rstrip()

        result.append(clean_line)
        i += 1

    return '\n'.join(result)

def process_file(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"⚠ Skipping {file_path} - file not found")
        return False

    print(f"Processing {path.name}...")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        cleaned_content = remove_all_comments(original_content)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        original_lines = original_content.count('\n')
        cleaned_lines = cleaned_content.count('\n')
        removed_lines = original_lines - cleaned_lines

        print(f"  ✓ Removed {removed_lines} lines from {path.name}")
        return True

    except Exception as e:
        print(f"  ✗ Error processing {path.name}: {e}")
        return False

def main():
    print("=" * 60)
    print("Finalizing Test Comment Removal - Step 1.3")
    print("=" * 60)

    test_files = [
        'ihatemoney/tests/main_test.py',
        'ihatemoney/tests/api_test.py',
        'ihatemoney/tests/budget_test.py',
        'ihatemoney/tests/history_test.py',
        'ihatemoney/tests/import_test.py',
    ]

    success_count = 0
    for file_path in test_files:
        if process_file(file_path):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"Summary: {success_count}/{len(test_files)} files processed successfully")
    print("=" * 60)

    if success_count == len(test_files):
        print("\n✓ All test files have been processed!")
        print("  Next: Run syntax validation with `python3 -m py_compile`")
    else:
        print("\n⚠ Some files were not processed successfully")

if __name__ == '__main__':
    main()
