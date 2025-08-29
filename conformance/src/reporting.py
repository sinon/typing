"""
Generates a summary of the type checker conformant tests.
"""

from pathlib import Path

import tomli

from test_groups import get_test_cases, get_test_groups
from type_checker import TYPE_CHECKERS


def generate_summary(root_dir: Path):
    print("Generating summary report")
    template_file = root_dir / "src" / "results_template.html"
    with open(template_file, "r") as f:
        template = f.read()

    summary = template.replace("{{summary}}", generate_summary_html(root_dir))

    results_file = root_dir / "results" / "results.html"

    with open(results_file, "w") as f:
        f.write(summary)


def generate_summary_html(root_dir: Path) -> str:
    column_count = len(TYPE_CHECKERS) + 1
    test_groups = get_test_groups(root_dir)
    test_cases = get_test_cases(test_groups, root_dir / "tests")

    # Initialize counters for summary statistics
    summary_stats = {}
    for type_checker in TYPE_CHECKERS:
        summary_stats[type_checker.name] = {
            'passes': 0,
            'partial': 0,
            'false_positives': 0,
            'false_negatives': 0,
        }

    summary_html = ['<div class="table_container"><table><tbody>']
    summary_html.append('<tr><th class="col1">&nbsp;</th>')

    for type_checker in TYPE_CHECKERS:
        # Load the version file for the type checker.
        version_file = root_dir / "results" / type_checker.name / "version.toml"

        try:
            with open(version_file, "rb") as f:
                existing_info = tomli.load(f)
        except FileNotFoundError:
            existing_info = {}
        except tomli.TOMLDecodeError:
            print(f"Error decoding {version_file}")
            existing_info = {}

        version = existing_info["version"] or "Unknown version"

        summary_html.append(f"<th class='tc-header'><div class='tc-name'>{version}</div>")
        summary_html.append("</th>")

    summary_html.append("</tr>")

    for test_group_name, test_group in test_groups.items():
        tests_in_group = [
            case for case in test_cases if case.name.startswith(f"{test_group_name}_")
        ]

        tests_in_group.sort(key=lambda x: x.name)

        # Are there any test cases in this group?
        if len(tests_in_group) > 0:
            summary_html.append(f'<tr><th class="column" colspan="{column_count}">')
            summary_html.append(
                f'<a class="test_group" href="{test_group.href}">{test_group.name}</a>'
            )
            summary_html.append("</th></tr>")

            for test_case in tests_in_group:
                test_case_name = test_case.stem

                summary_html.append(f'<tr><th class="column col1">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{test_case_name}</th>')

                for type_checker in TYPE_CHECKERS:
                    try:
                        results_file = (
                            root_dir
                            / "results"
                            / type_checker.name
                            / f"{test_case_name}.toml"
                        )
                        with open(results_file, "rb") as f:
                            results = tomli.load(f)
                    except FileNotFoundError:
                        results = {}

                    raw_notes = results.get("notes", "").strip()
                    raw_errors_diff = results.get("errors_diff", "").strip()
                    conformance = results.get("conformant", "Unknown")
                    if conformance == "Unknown":
                        # Try to look up the automated test results and use
                        # that if the test passes
                        automated = results.get("conformance_automated")
                        if automated == "Pass":
                            conformance = "Pass"
                    notes = "".join(
                        [f"<p>{note}</p>" for note in raw_notes.split("\n")]
                    )
                    false_negative_count = len([l for l in raw_errors_diff.split("\n") if ": Expected " in l])
                    false_positive_count = len([l for l in raw_errors_diff.split("\n") if ": Unexpected errors" in l])

                    if conformance == "Pass":
                        summary_stats[type_checker.name]['passes'] += 1
                    elif conformance in ["Partial", "Unknown"]:
                        summary_stats[type_checker.name]['partial'] += 1
                    
                    summary_stats[type_checker.name]['false_negatives'] += false_negative_count
                    summary_stats[type_checker.name]['false_positives'] += false_positive_count

                    conformance_class = (
                        "conformant"
                        if conformance == "Pass"
                        else "partially-conformant"
                        if conformance == "Partial"
                        else "not-conformant"
                    )

                    # Add an asterisk if there are notes to display for a "Pass".
                    if raw_notes != "" and conformance == "Pass":
                        conformance = "Pass*"
                    
                    if conformance == "Unknown":
                        conformance = f"Unknown ({false_negative_count}f-/{false_positive_count}f+)"

                    conformance_cell = f"{conformance}"
                    
                    expander_content = ""
                    if raw_notes != "":
                        expander_content += f"<div style='margin-bottom: 10px;'><strong>Notes:</strong>{notes}</div>"
                    if raw_errors_diff != "":
                        errors_diff_html = raw_errors_diff.replace("\n", "<br>")
                        expander_content += f"<div><strong>Errors Diff:</strong><br><pre style='margin: 5px 0; font-size: 0.9em; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word;'>{errors_diff_html}</pre></div>"
                    
                    if expander_content != "":
                        conformance_cell = f'<div class="hover-text">{conformance_cell}<span class="tooltip-text" id="bottom" style="max-width: 400px; width: max-content; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; text-align: left;">{expander_content}</span></div>'

                    summary_html.append(f'<th class="column col2 {conformance_class}">{conformance_cell}</th>')

                summary_html.append("</tr>")

    summary_html.append("</tbody></table></div>\n")

    # Add summary statistics table
    summary_html.append('<div style="margin-top: 30px;"><h3>Summary Statistics</h3>')
    summary_html.append('<div class="table_container"><table><tbody>')
    
    # Header row for summary table
    summary_html.append('<tr><th class="col1">Type Checker</th>')
    summary_html.append('<th class="column">Total Test Case Passes</th>')
    summary_html.append('<th class="column">Total Test Case Partial</th>')
    summary_html.append('<th class="column">Total False Positives</th>')
    summary_html.append('<th class="column">Total False Negatives</th>')
    summary_html.append('</tr>')
    
    # Data rows for each type checker
    for type_checker in TYPE_CHECKERS:
        stats = summary_stats[type_checker.name]
        
        # Load the version file for the type checker for display name
        version_file = root_dir / "results" / type_checker.name / "version.toml"
        try:
            with open(version_file, "rb") as f:
                existing_info = tomli.load(f)
        except FileNotFoundError:
            existing_info = {}
        except tomli.TOMLDecodeError:
            existing_info = {}
        
        version = existing_info.get("version", "Unknown version")
        
        summary_html.append(f'<tr><th class="col1">{version}</th>')
        summary_html.append(f'<td class="column conformant">{stats["passes"]}</td>')
        summary_html.append(f'<td class="column partially-conformant">{stats["partial"]}</td>')
        summary_html.append(f'<td class="column">{stats["false_positives"]}</td>')
        summary_html.append(f'<td class="column">{stats["false_negatives"]}</td>')
        summary_html.append('</tr>')
    
    summary_html.append("</tbody></table></div></div>\n")

    return "\n".join(summary_html)
