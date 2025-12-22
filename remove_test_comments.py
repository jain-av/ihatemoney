#!/usr/bin/env python3
import re
import sys

def remove_comments_and_docstrings(content):
    lines = content.split('\n')
    result = []
    in_multiline_string = False
    string_delimiter = None
    skip_next_string = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        if in_multiline_string:
            if string_delimiter in line:
                if line.rstrip().endswith(string_delimiter):
                    in_multiline_string = False
                    string_delimiter = None
                    i += 1
                    continue
            i += 1
            continue

        if stripped.startswith('"""') or stripped.startswith("'''"):
            delimiter = '"""' if stripped.startswith('"""') else "'''"

            if stripped == delimiter or (len(stripped) > 3 and not stripped[3:].strip()):
                in_multiline_string = True
                string_delimiter = delimiter
                i += 1
                continue
            elif stripped.count(delimiter) >= 2:
                i += 1
                continue
            else:
                in_multiline_string = True
                string_delimiter = delimiter
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
            new_line = []

            for j, char in enumerate(line):
                if escape_next:
                    new_line.append(char)
                    escape_next = False
                    continue

                if char == '\\':
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
        i += 1

    return '\n'.join(result)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: remove_test_comments.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    cleaned_content = remove_comments_and_docstrings(content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

    print(f"Processed {file_path}")
