# PyInstaller spec：AudioToLyrics 轻量版（onedir 窗口模式，无 AI 组件）
# 构建：pyinstaller --noconfirm --clean packaging/audiotolyrics.spec

import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas, binaries, hiddenimports = [], [], []
for pkg in ('customtkinter', 'imageio_ffmpeg', 'charset_normalizer', 'certifi', 'chardet'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    # AI 组件不打包（轻量版）：即使构建环境中已安装也排除
    excludes=['torch', 'torchaudio', 'demucs', 'faster_whisper', 'ctranslate2'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioToLyrics',
    console=False,  # 窗口模式，无控制台
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='AudioToLyrics',
)
