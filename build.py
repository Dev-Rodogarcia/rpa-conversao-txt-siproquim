"""
Script de build para distribuicao:

1) Gera a aplicacao em modo pasta (onedir):
   dist/Conversor_SIPROQUIM/Conversor_SIPROQUIM.exe

2) Opcionalmente gera instalador Setup.exe (Inno Setup):
   python build.py --setup
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Configura encoding para Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


APP_NAME = "Conversor_SIPROQUIM"
ENTRY_SCRIPT = "gui.py"
DIST_DIR = Path("dist") / APP_NAME
APP_EXE_PATH = DIST_DIR / f"{APP_NAME}.exe"
LEGACY_ONEFILE_EXE = Path("dist") / f"{APP_NAME}.exe"
ISS_SCRIPT_PATH = Path("installer") / "Conversor_SIPROQUIM.iss"
SETUP_OUTPUT_PATH = Path("installer") / "output" / "Setup_Conversor_SIPROQUIM.exe"


def ensure_pyinstaller() -> None:
    """Garante que o PyInstaller esteja disponivel."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[ERRO] PyInstaller nao esta instalado!")
        print("[INFO] Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller instalado com sucesso!\n")


def ensure_icon() -> Optional[Path]:
    """Converte icon.png para icon.ico se necessario e retorna o caminho do icone."""
    icon_png = Path("public/icon.png")
    icon_ico = Path("public/icon.ico")

    if icon_png.exists() and (not icon_ico.exists() or icon_png.stat().st_mtime > icon_ico.stat().st_mtime):
        try:
            from PIL import Image

            print("[INFO] Convertendo icon.png para icon.ico...")
            img = Image.open(icon_png)
            img.save(icon_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            print("[OK] Icone convertido com sucesso!\n")
        except ImportError:
            print("[AVISO] PIL/Pillow nao encontrado. Tentando sem converter...")
        except Exception as exc:
            print(f"[AVISO] Erro ao converter icone: {exc}")

    return icon_ico if icon_ico.exists() else None


def remove_legacy_onefile() -> None:
    """Remove o exe onefile legado para evitar confusao no dist."""
    if LEGACY_ONEFILE_EXE.exists():
        try:
            LEGACY_ONEFILE_EXE.unlink()
            print(f"[INFO] Removido executavel antigo: {LEGACY_ONEFILE_EXE}")
        except OSError as exc:
            print(f"[AVISO] Nao foi possivel remover {LEGACY_ONEFILE_EXE}: {exc}")


def build_app_onedir(icon_path: Optional[Path]) -> Path:
    """Executa o PyInstaller em modo onedir."""
    remove_legacy_onefile()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--hidden-import",
        "pdfplumber",
        "--hidden-import",
        "unidecode",
        "--hidden-import",
        "src.extrator",
        "--hidden-import",
        "src.gerador",
        "--hidden-import",
        "src.extrator.pdf_extractor",
        "--hidden-import",
        "src.extrator.tabela_parser",
        "--hidden-import",
        "src.extrator.campo_extractor",
        "--hidden-import",
        "src.gerador.txt_generator",
        "--hidden-import",
        "src.gerador.sanitizers",
        "--hidden-import",
        "src.gui.app_qt",
        "--hidden-import",
        "src.gui.constants",
        "--hidden-import",
        "src.gui.log_manager_qt",
        "--collect-all",
        "src",
        "--collect-all",
        "PySide6",
        "--hidden-import",
        "PySide6.QtCore",
        "--hidden-import",
        "PySide6.QtGui",
        "--hidden-import",
        "PySide6.QtWidgets",
        ENTRY_SCRIPT,
    ]

    if icon_path:
        cmd.extend(["--icon", str(icon_path)])
        print(f"[INFO] Usando icone: {icon_path}")
    else:
        print("[INFO] Sem icone personalizado (usando padrao do Windows)")

    print("[INFO] Comando de build:")
    print("   " + " ".join(cmd[:3]) + " ... [modulos] ...")
    print("\n[INFO] Gerando pasta de distribuicao (onedir)...\n")

    subprocess.check_call(cmd)

    if not APP_EXE_PATH.exists():
        raise FileNotFoundError(f"Executavel nao encontrado: {APP_EXE_PATH}")

    return APP_EXE_PATH


def find_iscc() -> Optional[Path]:
    """Localiza o compilador do Inno Setup (ISCC)."""
    candidates = []

    env_path = os.getenv("ISCC_PATH")
    if env_path:
        candidates.append(Path(env_path))

    iscc_in_path = shutil.which("ISCC")
    if iscc_in_path:
        candidates.append(Path(iscc_in_path))

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
            Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        ]
    )

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate

    return None


def build_setup(iscc_path: Path) -> Optional[Path]:
    """Compila o instalador Setup.exe via Inno Setup."""
    if not ISS_SCRIPT_PATH.exists():
        print(f"[AVISO] Script do instalador nao encontrado: {ISS_SCRIPT_PATH}")
        return None

    print(f"[INFO] Compilando instalador com Inno Setup: {iscc_path}")
    cmd = [str(iscc_path), str(ISS_SCRIPT_PATH)]
    subprocess.check_call(cmd)

    if SETUP_OUTPUT_PATH.exists():
        return SETUP_OUTPUT_PATH

    print(f"[AVISO] Setup nao encontrado no caminho esperado: {SETUP_OUTPUT_PATH}")
    return None


def format_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build do Conversor SIPROQUIM")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Compila tambem o Setup.exe (requer Inno Setup instalado).",
    )
    args = parser.parse_args()

    print("Iniciando build da aplicacao...\n")

    ensure_pyinstaller()
    icon_path = ensure_icon()

    try:
        exe_path = build_app_onedir(icon_path)

        print("\n" + "=" * 60)
        print("[OK] BUILD DA APLICACAO CONCLUIDO!")
        print("=" * 60)
        print(f"\n[INFO] Executavel (modo pasta):\n   {exe_path.absolute()}")
        print(f"[INFO] Tamanho do .exe: {format_size_mb(exe_path):.1f} MB")
        print(f"[INFO] Pasta de distribuicao:\n   {DIST_DIR.absolute()}\n")
        print("[INFO] IMPORTANTE:")
        print("   [OK] Use a pasta inteira 'dist/Conversor_SIPROQUIM' para execucao manual")
        print("   [OK] Nao envie apenas o .exe desta pasta sem os arquivos ao lado")

        if args.setup:
            iscc_path = find_iscc()
            if not iscc_path:
                print("\n[AVISO] Inno Setup (ISCC) nao encontrado.")
                print("        Instale o Inno Setup 6 e rode novamente:")
                print("        python build.py --setup")
            else:
                setup_path = build_setup(iscc_path)
                if setup_path:
                    print("\n" + "=" * 60)
                    print("[OK] SETUP GERADO COM SUCESSO!")
                    print("=" * 60)
                    print(f"\n[INFO] Instalador:\n   {setup_path.absolute()}")
                    print(f"[INFO] Tamanho do setup: {format_size_mb(setup_path):.1f} MB")
                    print("\n[INFO] O Setup.exe nao inclui a pasta 'backups'.")

    except subprocess.CalledProcessError as exc:
        print(f"\n[ERRO] Erro durante o build: {exc}")
        print("\n[DICA] Troubleshooting:")
        print("   - Verifique se todas as dependencias estao instaladas")
        print("   - Tente executar: python -m pip install -r requirements.txt")
        print("   - Verifique se ha mensagens de erro acima")
        sys.exit(1)
    except FileNotFoundError as exc:
        print(f"\n[ERRO] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[AVISO] Build cancelado pelo usuario.")
        sys.exit(1)


if __name__ == "__main__":
    main()
