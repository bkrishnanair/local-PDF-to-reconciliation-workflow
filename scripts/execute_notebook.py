"""Execute and save genuine notebook outputs using the current virtualenv."""
import os
from pathlib import Path
import subprocess
import sys

import nbformat
from nbclient import NotebookClient

from scripts.generate_demo import ROOT


def main():
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run with the project virtualenv: .venv/bin/python -m scripts.execute_notebook")
    for key, directory in {"IPYTHONDIR": "ipython", "JUPYTER_RUNTIME_DIR": "jupyter-runtime",
                           "JUPYTER_CONFIG_DIR": "jupyter-config"}.items():
        path = ROOT / "artifacts" / directory
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    subprocess.run([sys.executable, "-m", "ipykernel", "install", "--sys-prefix", "--name", "reconciliation",
                    "--display-name", "Reconciliation demo"], check=True)
    path = ROOT / "notebooks/ocr_evaluation.ipynb"
    notebook = nbformat.read(path, as_version=4)
    NotebookClient(notebook, timeout=120, kernel_name="reconciliation",
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(notebook, path)
    print(f"Executed and saved {path}")


if __name__ == "__main__":
    main()
