"""Tests for Dockerfile structural rules.

Validates: Requirements 10.2, 10.3
"""

import re
from pathlib import Path

DOCKERFILE = Path(__file__).parent.parent / "Dockerfile"


def get_dockerfile_lines():
    return DOCKERFILE.read_text().splitlines()


def test_multistage_build():
    """Validates: Requirements 10.2 — Dockerfile uses a multi-stage build (at least 2 FROM instructions)."""
    lines = get_dockerfile_lines()
    from_instructions = [l for l in lines if re.match(r"^\s*FROM\s+", l, re.IGNORECASE)]
    assert len(from_instructions) >= 2, (
        f"Expected at least 2 FROM instructions for multi-stage build, found {len(from_instructions)}"
    )


def test_non_root_user():
    """Validates: Requirements 10.3 — The final stage must run as a non-root user."""
    lines = get_dockerfile_lines()

    # Find the last FROM instruction index (start of final stage)
    last_from_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s+", line, re.IGNORECASE):
            last_from_idx = i

    assert last_from_idx is not None, "No FROM instruction found in Dockerfile"

    final_stage_lines = lines[last_from_idx:]
    user_instructions = [
        l for l in final_stage_lines if re.match(r"^\s*USER\s+", l, re.IGNORECASE)
    ]

    assert user_instructions, "No USER instruction found in the final stage"

    last_user = user_instructions[-1]
    user_value = re.split(r"\s+", last_user.strip(), maxsplit=1)[1].strip()

    assert user_value.lower() != "root" and user_value != "0", (
        f"Final stage must not run as root, but USER is set to '{user_value}'"
    )
