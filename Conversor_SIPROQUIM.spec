# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('public', 'public')]
binaries = []
hiddenimports = ['pdfplumber', 'unidecode', 'src.extrator', 'src.gerador', 'src.extrator.pdf_extractor', 'src.extrator.tabela_parser', 'src.extrator.campo_extractor', 'src.gerador.txt_generator', 'src.gerador.sanitizers', 'src.gui.app_qt', 'src.gui.constants', 'src.gui.log_manager_qt', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']
tmp_ret = collect_all('src')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Conversor_SIPROQUIM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['public\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Conversor_SIPROQUIM',
)
