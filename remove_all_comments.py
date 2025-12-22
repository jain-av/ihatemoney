#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def remove_comments_and_docstrings(content):
    lines = content.split('\n')
    result = []
    in_docstring = False
    docstring_delimiter = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if in_docstring:
            if docstring_delimiter in line:
                closing_index = line.find(docstring_delimiter)
                after_closing = line[closing_index + len(docstring_delimiter):]

                if not after_closing.strip() or after_closing.strip().startswith('#'):
                    in_docstring = False
                    docstring_delimiter = None
                    continue
                else:
                    in_docstring = False
                    docstring_delimiter = None
            continue

        if stripped.startswith('"""') or stripped.startswith("'''"):
            delimiter = '"""' if stripped.startswith('"""') else "'''"

            rest_of_line = stripped[len(delimiter):]
            if delimiter in rest_of_line:
                closing_index = rest_of_line.find(delimiter)
                after_closing = rest_of_line[closing_index + len(delimiter):]
                if not after_closing.strip() or after_closing.strip().startswith('#'):
                    continue
            else:
                in_docstring = True
                docstring_delimiter = delimiter
                continue

        if stripped.startswith('#'):
            continue

        clean_line = line
        if '#' in line:
            in_string = False
            string_char = None
            escape_next = False
            new_line = []

            for char in line:
                if escape_next:
                    new_line.append(char)
                    escape_next = False
                    continue

                if char == '\\' and in_string:
                    new_line.append(char)
                    escape_next = True
                    continue

                if char in ('"', "'"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                    new_line.append(char)
                elif char == '#' and not in_string:
                    break
                else:
                    new_line.append(char)

            clean_line = ''.join(new_line).rstrip()

        result.append(clean_line)

    return '\n'.join(result)

if __name__ == '__main__':
    files = [
        'ihatemoney/tests/main_test.py',
        'ihatemoney/tests/api_test.py',
        'ihatemoney/tests/budget_test.py',
        'ihatemoney/tests/history_test.py',
        'ihatemoney/tests/import_test.py',
    ]

    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            print(f"Skipping {file_path} - not found")
            continue

        print(f"Processing {file_path}...")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        cleaned_content = remove_comments_and_docstrings(content)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        print(f"✓ Completed {file_path}")

    print("\nAll test files processed successfully!")
