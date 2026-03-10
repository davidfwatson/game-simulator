#!/usr/bin/env python3
"""Quick utility to show rendered output for a range of plays."""
import sys
import subprocess

def main():
    fixture = sys.argv[1] if len(sys.argv) > 1 else "test_fixture_pbp_example_3.json"

    plays = []
    for arg in sys.argv[2:]:
        if '-' in arg:
            start, end = arg.split('-')
            plays.extend(range(int(start), int(end) + 1))
        else:
            plays.append(int(arg))

    if not plays:
        plays = range(0, 7)

    for p in plays:
        result = subprocess.run(
            ["python", "pbp_tools.py", "inspect-play", fixture, "--play", str(p)],
            capture_output=True, text=True
        )
        output = result.stdout
        marker = "RENDERED OUTPUT FOR THIS PLAY"
        if marker in output:
            idx = output.index(marker)
            rendered = output[idx:].split("=" * 70 + "\n", 1)
            if len(rendered) > 1:
                print(f"=== PLAY {p} ===")
                print(rendered[1].strip())
                print()
            else:
                # Try with different separator
                after = output[idx + len(marker):]
                lines = after.strip().split('\n')
                # Skip the === line
                content = '\n'.join(l for l in lines if not l.startswith('==='))
                print(f"=== PLAY {p} ===")
                print(content.strip())
                print()

if __name__ == "__main__":
    main()
