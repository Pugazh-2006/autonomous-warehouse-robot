"""Standalone entry point for the packaged Windows application."""

from __future__ import annotations

import ctypes
import sys
from typing import List


REQUIRED_MODULES = {
    "networkx": "NetworkX",
    "matplotlib": "Matplotlib",
    "tkinter": "Tkinter",
}


def _show_error(message: str) -> None:
    """Show a usable error even when the console is hidden in the EXE."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Autonomous Warehouse Robot", message)
        root.destroy()
    except Exception:
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "Autonomous Warehouse Robot",
            0x10,
        )


def check_requirements() -> List[str]:
    """Return friendly names for modules unavailable at startup."""
    missing: List[str] = []
    for module_name, friendly_name in REQUIRED_MODULES.items():
        try:
            __import__(module_name)
        except Exception:
            missing.append(friendly_name)
    return missing


def run() -> None:
    """Validate the runtime and launch the desktop simulator."""
    missing = check_requirements()
    if missing:
        _show_error(
            "The application cannot start because these components are missing:\n\n"
            + "\n".join(f"• {name}" for name in missing)
            + "\n\nPlease reinstall the packaged application or install the project requirements."
        )
        return

    try:
        import tkinter as tk

        from app import AutonomousWarehouseApp

        root = tk.Tk()
        AutonomousWarehouseApp(root)
        root.mainloop()
    except Exception as exc:
        _show_error(
            "The simulator could not start.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "Try running the EXE again or rebuild it with the project requirements."
        )
        raise


if __name__ == "__main__":
    run()
