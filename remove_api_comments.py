#!/usr/bin/env python3
import re
import sys

def remove_comments_and_docstrings(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result = []
    i = 0
    in_multiline_docstring = False
    docstring_quote = None
    skip_next_docstring = False

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        if in_multiline_docstring:
            if docstring_quote in line:
                if line.rstrip().endswith(docstring_quote):
                    in_multiline_docstring = False
                    docstring_quote = None
                    i += 1
                    continue
            i += 1
            continue

        if (stripped.startswith('def ') or stripped.startswith('class ') or
            stripped.startswith('@')):
            skip_next_docstring = True
            result.append(line)
            i += 1
            continue

        if skip_next_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            quote = '"""' if stripped.startswith('"""') else "'''"

            if stripped.count(quote) >= 2:
                skip_next_docstring = False
                i += 1
                continue
            else:
                in_multiline_docstring = True
                docstring_quote = quote
                skip_next_docstring = False
                i += 1
                continue

        if i == 0 or (i > 0 and all(l.strip() == '' or l.strip().startswith('from ') or
                                      l.strip().startswith('import ') for l in lines[:i])):
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(quote) >= 2:
                    i += 1
                    continue
                else:
                    in_multiline_docstring = True
                    docstring_quote = quote
                    i += 1
                    continue

        skip_next_docstring = False

        comment_pos = -1
        in_string = False
        string_char = None
        escape_next = False

        for j, char in enumerate(line):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None

            if char == '#' and not in_string:
                comment_pos = j
                break

        if comment_pos != -1:
            line_without_comment = line[:comment_pos].rstrip() + '\n'
            if line_without_comment.strip():
                result.append(line_without_comment)
            elif not result or result[-1].strip():
                result.append('\n')
        else:
            result.append(line)

        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(result)

if __name__ == '__main__':
    files = [
        'ihatemoney/api/common.py',
        'ihatemoney/api/__init__.py',
        'ihatemoney/api/v1/__init__.py',
        'ihatemoney/api/v1/resources.py',
    ]

    for file_path in files:
        print(f"Processing {file_path}...")
        try:
            remove_comments_and_docstrings(file_path)
            print(f"  ✓ Completed {file_path}")
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")
            sys.exit(1)

    print("\nAll API files processed successfully!")
