import conffwk
import oks
import shutil
import tempfile
import difflib
import os
from typing import Tuple


def filtered_diff(file1: str, file2: str) -> Tuple[bool, str]:
    """
    Execute a diff between two files with optional regex-based filtering.

    Args:
        file1: Path to the first file
        file2: Path to the second file
        filter_patterns: List of regex patterns to filter out from diff output.
                        Lines matching any pattern will be excluded from the diff.

    Returns:
        Tuple of (has_diff, diff_output) where:
            has_diff: True if there are differences after filtering, False otherwise
            diff_output: String containing the unified diff output
    """
    # Read the files
    with open(file1, 'r', encoding='utf-8') as f:
        file1_lines = f.readlines()

    with open(file2, 'r', encoding='utf-8') as f:
        file2_lines = f.readlines()

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        file1_lines,
        file2_lines,
        fromfile=file1,
        tofile=file2,
        lineterm=''
    ))

    if not diff_lines:
        return False, ""

    # Filter diff lines
    filtered_lines = []
    has_meaningful_diff = False

    for line in diff_lines:
        filtered_lines.append(line)

        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue

        if line.startswith('+<info') or line.startswith('-<info'):
            continue

        # Mark that we have meaningful differences (not just context or headers)
        if line.startswith('+') or line.startswith('-'):
            has_meaningful_diff = True

    diff_output = '\n'.join(filtered_lines).replace("\n\n", "\n")
    return has_meaningful_diff, diff_output

def oks_format(input_file: str, fix: bool = False) -> None:
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    shutil.copy2(input_file, tmpfile.name)

    diff=False
    err=False

    try:
        if ".data.xml" in input_file:
            print(f"Formatting database file {input_file}")
            dal = conffwk.dal.module("generated", "schema/confmodel/dunedaq.schema.xml")
            conffwk.Configuration(f"oksconflibs:{input_file}")
            oks_kernel = conffwk.Configuration(f"oksconflibs:{tmpfile.name}")

            testobj = dal.Service("Reformat-test-obj")
            oks_kernel.update_dal(testobj)
            oks_kernel.destroy_dal(testobj)

            oks_kernel.commit()
        elif ".schema.xml" in input_file:
            print(f"Formatting schema file {input_file}")

            oks_kernel = oks.OksKernel(silence_mode=True)
            schema = oks_kernel.load_schema(str(input_file))
            #oks_kernel.save_all_schema()
            oks_kernel.save_as_schema(str(tmpfile.name), schema)

        else:
            print(f"Don't know how to handle file {input_file}")
            err = True
    except Exception as e:
        print(f"Error occurred while formatting {input_file}: {e}")
        err = True

    diff, diff_output = filtered_diff(input_file, tmpfile.name)

    if diff:
        print(f"File {input_file} has differences after formatting:")
        print(diff_output)

    if err:
        print(f"Leaving temporary file {tmpfile.name} for inspection due to errors. (e.g. check oks_dump -f {tmpfile.name})")
        return 2

    if diff and fix:
        shutil.copy2(tmpfile.name, input_file)
        os.remove(tmpfile.name)
        return 0

    os.remove(tmpfile.name)
    if diff:
        return 1
    return 0
