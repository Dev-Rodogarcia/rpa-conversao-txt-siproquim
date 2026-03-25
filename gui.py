"""Ponto de entrada da GUI PySide6."""

from __future__ import annotations

import sys

from src.gui.app_qt import criar_app_qt


def main() -> int:
    app, janela = criar_app_qt()
    janela.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
