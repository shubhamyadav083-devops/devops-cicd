"""
Property-based tests for the CI/CD pipeline automation spec.
Uses Hypothesis with max_examples=100 for each property.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml():
    return Path(".gitlab-ci.yml").read_text(encoding="utf-8")


def _extract_yaml_string_values(yaml_content: str) -> list[str]:
    """Recursively collect all string leaf values from a parsed YAML document."""
    data = yaml.safe_load(yaml_content)

    values: list[str] = []

    def _walk(node):
        if isinstance(node, str):
            values.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)
    return values


def generate_junit_xml(test_cases: list[dict]) -> str:
    """Build a JUnit XML string from a list of test-case dicts."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="generated", tests=str(len(test_cases)))

    for tc in test_cases:
        # Sanitise text so ElementTree can serialise it (strip control chars)
        name = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(tc["name"]))
        classname = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(tc["classname"]))
        duration = tc["duration"]
        # Guard against NaN / inf which are not valid XML attribute values
        if not (duration == duration) or duration != duration:  # NaN check
            duration = 0.0
        try:
            duration_str = f"{float(duration):.6f}"
        except (ValueError, OverflowError):
            duration_str = "0.000000"

        attrib = {
            "name": name or "unnamed",
            "classname": classname or "unnamed",
            "time": duration_str,
        }
        case_el = ET.SubElement(suite, "testcase", **attrib)
        if not tc["passed"]:
            ET.SubElement(case_el, "failure", message="test failed")

    return ET.tostring(root, encoding="unicode")


# ---------------------------------------------------------------------------
# Property 1: No Hardcoded Secrets or Environment-Specific Values
# ---------------------------------------------------------------------------

@given(
    st.text(
        min_size=8,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_",
        ),
    )
)
@settings(max_examples=100)
def test_no_hardcoded_secrets(random_credential):
    # Feature: cicd-pipeline-automation, Property 1: no hardcoded secrets or environment-specific values
    # Validates: Requirements 4.2, 9.1, 9.2

    yaml_content = _load_yaml()

    # Dynamic check: any generated credential-like string must not appear as a
    # bare literal in the YAML (unless it starts with '$', meaning it is a
    # variable reference).
    if random_credential in yaml_content:
        assert random_credential.startswith("$"), (
            f"Credential-like string {random_credential!r} appears as a bare "
            "literal in .gitlab-ci.yml"
        )

    # Static scan: extract all string values from the YAML and assert none
    # match a URL pattern or a long token pattern.
    # localhost:5000 is explicitly allowed as a fixed local address.
    ALLOWED_LITERALS = {"localhost:5000"}

    url_pattern = re.compile(r"https?://", re.IGNORECASE)
    # Long alphanumeric strings > 20 chars that are not variable references
    token_pattern = re.compile(r"^[A-Za-z0-9]{21,}$")

    for value in _extract_yaml_string_values(yaml_content):
        # Skip variable references
        if value.startswith("$"):
            continue
        # Skip explicitly allowed literals
        if value in ALLOWED_LITERALS:
            continue
        # Skip values that contain allowed literals as substrings (e.g. image refs)
        if any(allowed in value for allowed in ALLOWED_LITERALS):
            continue

        assert not url_pattern.search(value), (
            f"Hardcoded URL found in .gitlab-ci.yml: {value!r}"
        )
        assert not token_pattern.match(value), (
            f"Long token-like literal found in .gitlab-ci.yml: {value!r}"
        )


# ---------------------------------------------------------------------------
# Property 2: Required Variable Guard Checks
# ---------------------------------------------------------------------------

@given(st.sampled_from(["IMAGE_TAG", "FULL_IMAGE_REF"]))
@settings(max_examples=100)
def test_required_variable_guard_checks(variable_name):
    # Feature: cicd-pipeline-automation, Property 2: required variable guard checks in job scripts
    # Validates: Requirements 9.3

    data = yaml.safe_load(_load_yaml())

    # Jobs that are expected to guard the given variable
    jobs_to_check = {
        "IMAGE_TAG": ["deploy-staging", "deploy-production"],
        "FULL_IMAGE_REF": ["test-unit", "deploy-staging", "deploy-production"],
    }

    target_jobs = jobs_to_check[variable_name]
    # Match both standalone guards and combined guards joined with || or &&
    # e.g. `if [ -z "$VAR" ]` or `if [ -z "$VAR" ] || [ -z "$OTHER" ]`
    guard_pattern = re.compile(
        r'if\b.*\[\s+-z\s+"?\$' + re.escape(variable_name) + r'"?\s*\]'
    )

    for job_name in target_jobs:
        job = data.get(job_name, {})
        script_lines: list[str] = job.get("script", [])

        # Flatten multi-line script entries into a single list of lines
        flat_lines: list[str] = []
        for entry in script_lines:
            flat_lines.extend(str(entry).splitlines())

        # Find the index of the guard check
        guard_index = None
        for idx, line in enumerate(flat_lines):
            if guard_pattern.search(line):
                guard_index = idx
                break

        assert guard_index is not None, (
            f"Job {job_name!r} has no guard check for ${variable_name} "
            f"(expected pattern: if [ -z \"${variable_name}\" ])"
        )

        # The guard must appear before the first substantive use of the variable
        # (i.e., before any line that references $VAR outside of the guard itself)
        use_pattern = re.compile(r"\$" + re.escape(variable_name) + r"(?!\s*\])")
        for idx, line in enumerate(flat_lines):
            if idx == guard_index:
                continue
            if use_pattern.search(line) and idx < guard_index:
                raise AssertionError(
                    f"Job {job_name!r}: ${variable_name} is used on line {idx} "
                    f"before the guard check on line {guard_index}.\n"
                    f"  Use line: {line!r}"
                )


# ---------------------------------------------------------------------------
# Property 3: JUnit XML Well-Formedness
# ---------------------------------------------------------------------------

test_case_strategy = st.fixed_dictionaries(
    {
        "name": st.text(min_size=1),
        "classname": st.text(min_size=1),
        "passed": st.booleans(),
        "duration": st.floats(min_value=0.0, max_value=60.0),
    }
)


@given(st.lists(test_case_strategy, min_size=1, max_size=20))
@settings(max_examples=100)
def test_junit_xml_wellformed(test_cases):
    # Feature: cicd-pipeline-automation, Property 3: JUnit XML is valid and well-formed
    # Validates: Requirements 3.2

    xml_output = generate_junit_xml(test_cases)

    # Must parse as valid XML
    root = ET.fromstring(xml_output)

    # Root tag must be testsuites or testsuite
    assert root.tag in ("testsuites", "testsuite"), (
        f"Root tag must be 'testsuites' or 'testsuite', got {root.tag!r}"
    )

    # Must contain at least one <testsuite>
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    else:
        suites = [root]

    assert len(suites) >= 1, "XML must contain at least one <testsuite> element"

    # Total <testcase> count across all suites must match input length
    total_cases = sum(len(suite.findall("testcase")) for suite in suites)
    assert total_cases == len(test_cases), (
        f"Expected {len(test_cases)} <testcase> elements, found {total_cases}"
    )
