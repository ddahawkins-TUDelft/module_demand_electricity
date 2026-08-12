from pathlib import Path
import re


FORBIDDEN_PATTERNS = (
    r"\bsys\.path\b",
    r"^\s*from\s+cleaning\b",
    r"^\s*import\s+cleaning\b",
    r"^\s*from\s+common\b",
    r"^\s*import\s+common\b",
    r"^\s*import\s+pandas\b",
    r"^\s*from\s+pandas\b",
    r"^\s*import\s+numpy\b",
    r"^\s*from\s+numpy\b",
    r"^\s*import\s+geopandas\b",
    r"^\s*from\s+geopandas\b",
    r"^\s*import\s+rioxarray\b",
    r"^\s*from\s+rioxarray\b",
    r"^\s*import\s+pandera\b",
    r"^\s*from\s+pandera\b",
)


def test_snakemake_host_code_has_no_module_runtime_dependencies():
    workflow_files = [
        Path("workflow/Snakefile"),
        *Path("workflow/rules").glob("*.smk"),
    ]

    violations = []

    for path in workflow_files:
        text = path.read_text(encoding="utf-8")

        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.MULTILINE):
                violations.append(
                    f"{path}: {pattern}"
                )

    assert not violations, (
        "Snakemake host code must not depend on module runtime "
        "packages:\n"
        + "\n".join(violations)
    )
