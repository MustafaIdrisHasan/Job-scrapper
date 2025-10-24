"""Minimal Tkinter UI wrapper."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from typing import Callable

from .config import Settings


def launch(settings: Settings, run_callable: Callable[[], None]) -> None:
    root = tk.Tk()
    root.title("Internship Scraper")
    root.geometry("320x160")

    status_var = tk.StringVar(value="Idle")

    tk.Label(root, text="Startup Internship Scraper").pack(pady=10)
    status_label = tk.Label(root, textvariable=status_var)
    status_label.pack()

    def run_now() -> None:
        status_var.set("Running…")
        thread = threading.Thread(
            target=_run_background, args=(run_callable, status_var), daemon=True
        )
        thread.start()

    def open_output() -> None:
        path = Path(settings.output_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", str(path)], check=False)
            else:
                import subprocess

                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            status_var.set(f"Output: {path}")

    tk.Button(root, text="Run Now", command=run_now).pack(pady=5)
    tk.Button(root, text="Open Output Folder", command=open_output).pack(pady=5)

    root.mainloop()


def _run_background(run_callable: Callable[[], None], status_var: tk.StringVar) -> None:
    try:
        run_callable()
        status_var.set("Completed")
    except Exception as exc:  # noqa: BLE001
        status_var.set(f"Error: {exc}")
