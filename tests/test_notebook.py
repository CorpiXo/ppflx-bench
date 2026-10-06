"""privacy_comparison_analysis.ipynb runs against the committed results and
reports their numbers: every code cell executes headless, and the table it
builds matches the reports it reads."""

import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "privacy_comparison_analysis.ipynb"
REPORTS = sorted((REPO / "results").glob("*/comparison_report.json"))


@pytest.fixture
def notebook_namespace(tmp_path, monkeypatch):
    if not REPORTS:
        pytest.skip("no committed results")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for report in REPORTS:
        (tmp_path / report.parent.name).mkdir()
        shutil.copy(report, tmp_path / report.parent.name / report.name)
    monkeypatch.setenv("PPFLX_RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(plt, "show", lambda *a, **k: plt.close("all"))

    nb = json.loads(NOTEBOOK.read_text())
    namespace = {"__name__": "__main__"}
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), f"{NOTEBOOK.name}[{i}]", "exec"), namespace)
    return namespace, tmp_path


def test_notebook_outputs_are_cleared():
    nb = json.loads(NOTEBOOK.read_text())
    assert all(not c.get("outputs") and c.get("execution_count") is None for c in nb["cells"] if c["cell_type"] == "code")


def test_notebook_runs_and_reports_the_measured_numbers(notebook_namespace):
    ns, results_dir = notebook_namespace
    df, checks = ns["df"], ns["checks"]
    entries = {(r.parent.name, e["mode"]): e for r in REPORTS for e in json.loads(r.read_text())}

    assert len(df) == len(entries) and checks["Valid"].all()
    assert set(df["Key"].astype(str)) == set(ns["MODE_PROPERTIES"])  # every mode has stated properties
    for _, row in df.iterrows():
        e = entries[(row["Dataset"], str(row["Key"]))]
        assert row["Run time (s)"] == e["duration"]  # measured, not estimated
        assert row["Test acc (%)"] == e["benchmark"]["model_quality"]["test_accuracy"]["mean"]
    assert (results_dir / "comparison_analysis" / "all_modes.csv").exists()
