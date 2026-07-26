# Windows 安装包 + GitHub Release 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AudioToLyrics 打包为 Windows setup.exe（轻量版，无 AI 组件），通过 GitHub Actions 打 tag 自动构建并发布 Release。

**Architecture:** 代码侧做三处小改造（可写数据目录、AI 功能降级、stderr 守卫）+ requirements 拆分；打包侧 PyInstaller onedir + Inno Setup；发布侧 tag 触发的 GitHub Actions workflow。

**Tech Stack:** PyInstaller 6、Inno Setup 6（GitHub windows-latest 镜像自带）、GitHub Actions、`gh` CLI。

**依据：** `docs/superpowers/specs/2026-07-26-windows-installer-release-design.md`（已批准）

## Global Constraints

- 分支：`feature/packaging`（已从 main 创建）；提交信息用中文，结尾带 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- 项目**无 pytest 基础设施**（spec 明确不新增）：验证方式为 `python -m compileall` + 脚本化冒烟
- requirements*.txt 必须**纯 ASCII**（pip 无 BOM 时按系统区域编码 GBK 解码，中文注释会崩——已踩过的坑）
- 版本号单一来源 `config.VERSION = "4.0"`；Release tag 用 `v4.0.0`
- 源码运行的行为必须**零变化**（数据仍写项目根目录；仅 frozen 时改写 %APPDATA%）
- 本地试构建用 `D:/Program/Coding/Python/python.exe`（3.13，核心依赖已装；无 demucs/faster-whisper，正好是 AI 降级的天然测试环境）；中文输出加 `-X utf8`
- 注意：main 上的 requirements.txt 是含中文注释的旧版（d2f8c06 的 ASCII 修复在游离分支上未合并），Task 3 重写时直接以 ASCII 落地，**不要**从 main 的版本改起

---

### Task 1: 可写数据目录（paths.py + 三处写入点 + stderr 守卫）

**Files:**
- Create: `utils/paths.py`
- Modify: `utils/logging_setup.py`（log 目录 + stderr 守卫）
- Modify: `utils/settings_store.py`（设置文件路径）
- Modify: `core/decryptor.py:22,30-32`（tools 目录）

**Interfaces:**
- Produces: `utils.paths.app_data_dir() -> Path`、`utils.paths.is_frozen() -> bool`（Task 5 spec 调试也用）

- [ ] **Step 1: 写 `utils/paths.py`**

```python
"""应用数据目录解析：源码运行写项目目录，打包运行写 %APPDATA%"""

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """是否以 PyInstaller 打包形式运行"""
    return getattr(sys, "frozen", False)


def app_data_dir() -> Path:
    """
    可写的应用数据目录（logs/、user_settings.json、tools/ 的父目录）。

    - 源码运行：项目根目录（现状不变）
    - 打包运行：%APPDATA%/AudioToLyrics（Program Files 只读，必须重定向）
    """
    if is_frozen():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "AudioToLyrics"
    return Path(__file__).resolve().parent.parent
```

- [ ] **Step 2: 改 `utils/logging_setup.py`**

- `log_dir = Path(__file__).resolve().parent.parent / "logs"` → `log_dir = app_data_dir() / "logs"`（import `from utils.paths import app_data_dir`）
- stderr 守卫：控制台 handler 部分包进 `if sys.stderr is not None:`（frozen 窗口模式 stderr 为 None）

- [ ] **Step 3: 改 `utils/settings_store.py` 与 `core/decryptor.py`**

- `_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "user_settings.json"` → `app_data_dir() / "user_settings.json"`
- decryptor：删 `ROOT_DIR = Path(__file__).resolve().parent.parent`，`_get_um_cli_path()` 返回 `app_data_dir() / "tools" / UM_CLI_NAME`

- [ ] **Step 4: 验证**

```bash
"D:/Program/Coding/Python/python.exe" -X utf8 -c "
import sys
from utils.paths import app_data_dir, is_frozen
assert not is_frozen() and app_data_dir().name == 'AudioToLyrics' and 'AppData' not in str(app_data_dir())
sys.frozen = True
assert is_frozen() and 'AppData' in str(app_data_dir())
del sys.frozen
from utils.logging_setup import setup_logging; setup_logging()
import utils.settings_store, core.decryptor
assert str(utils.settings_store._SETTINGS_PATH).endswith('user_settings.json')
assert str(core.decryptor._get_um_cli_path()).endswith('tools\\\\um.exe')
# stderr=None 守卫
sys.stderr = None
setup_logging()
print('TASK1_OK')
"
```
另跑 `python main.py` 6 秒启动冒烟（GUI 无回归）。

- [ ] **Step 5: Commit**

```bash
git add utils/paths.py utils/logging_setup.py utils/settings_store.py core/decryptor.py
git commit -m "打包准备：可写数据目录（frozen→%APPDATA%）+ logging stderr 守卫"
```

---

### Task 2: AI 功能优雅降级

**Files:**
- Create: `utils/deps.py`
- Modify: `gui/settings_panel.py`（复选框禁用 + 提示；`make_checkbox` 需支持 state 透传 → 先给 `gui/styles.py` 的 `make_checkbox` 加 `**kwargs`）
- Modify: `core/transcriber.py`（ImportError 友好化）
- Modify: `core/separator.py`（demucs 缺失前置检查）

**Interfaces:**
- Consumes: `gui/styles.py` 的 `make_checkbox`（Task 2 给其加 `**kwargs`）
- Produces: `utils.deps.has_demucs() -> bool`、`utils.deps.has_whisper() -> bool`

- [ ] **Step 1: 写 `utils/deps.py`**

```python
"""可选依赖探测：AI 组件（demucs/faster-whisper）在安装版中不打包"""

import importlib.util


def has_demucs() -> bool:
    """demucs 人声分离是否可用"""
    return importlib.util.find_spec("demucs") is not None


def has_whisper() -> bool:
    """faster-whisper 语音识别是否可用"""
    return importlib.util.find_spec("faster_whisper") is not None
```

- [ ] **Step 2: `gui/styles.py` 的 `make_checkbox` 加 `**kwargs`**

签名改 `make_checkbox(parent, text, variable, command=None, **kwargs)`，末尾 `**kwargs` 透传给 CTkCheckBox。

- [ ] **Step 3: `gui/settings_panel.py` 降级逻辑**

- 顶部 `from utils.deps import has_demucs, has_whisper`
- `_build_ui` 开头：`self._demucs_available = has_demucs()`、`self._whisper_available = has_whisper()`
- Demucs 复选框：不可用时 `state="disabled"`；提示文案改 `安装版未包含 Demucs 组件（源码版可 pip install -r requirements-ai.txt）`，颜色 `S.FG_DISABLED`；Whisper 同理
- `apply_settings` 末尾加：
```python
        # 安装版无 AI 组件：忽略持久化中的启用状态
        if not self._demucs_available:
            self._use_demucs_var.set(False)
        if not self._whisper_available:
            self._use_whisper_var.set(False)
```

- [ ] **Step 4: transcriber / separator 友好报错**

transcriber `_get_model` 内：
```python
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(
                "未安装 faster-whisper（安装版不含 AI 组件；"
                "源码版请 pip install -r requirements-ai.txt）"
            ) from e
```
separator `separate_vocals` 函数体开头：
```python
    if importlib.util.find_spec("demucs") is None:
        raise RuntimeError(
            "未安装 demucs（安装版不含 AI 组件；"
            "源码版请 pip install -r requirements-ai.txt）"
        )
```

- [ ] **Step 5: 验证**（D:\Python3.13 无 demucs/faster-whisper，天然降级环境）

```bash
"D:/Program/Coding/Python/python.exe" -X utf8 -c "
from utils.deps import has_demucs, has_whisper
assert not has_demucs() and not has_whisper()
from core.transcriber import _get_model
try: _get_model('tiny'); raise SystemExit('NO ERROR')
except RuntimeError as e: assert 'requirements-ai' in str(e)
from core.separator import separate_vocals
try: separate_vocals('x.mp3'); raise SystemExit('NO ERROR')
except RuntimeError as e: assert 'requirements-ai' in str(e)
from gui.app import App
app = App()
assert str(app._settings_panel._use_demucs_var.get()) == 'False'
print('TASK2_OK'); app.destroy()
"
```

- [ ] **Step 6: Commit**

```bash
git add utils/deps.py gui/settings_panel.py gui/styles.py core/transcriber.py core/separator.py
git commit -m "AI 组件缺失时优雅降级：GUI 禁用 + 友好报错"
```

---

### Task 3: requirements 拆分 + README + 清理游离分支

**Files:**
- Modify: `requirements.txt`（全量重写为 ASCII 核心 6 依赖）
- Create: `requirements-ai.txt`
- Modify: `README.md`（安装说明、安装包下载说明）

- [ ] **Step 1: 重写 `requirements.txt`（纯 ASCII！）**

```
# Core dependencies (optional AI features: see requirements-ai.txt).
customtkinter>=5.2.2,<7.0
syncedlyrics>=0.8,<2.0
mutagen>=1.46,<2.0
requests>=2.31,<3.0
zhconv>=1.4.3,<2.0
imageio-ffmpeg>=0.4.9,<1.0
```

- [ ] **Step 2: 写 `requirements-ai.txt`（纯 ASCII）**

```
# Optional AI features (source install only): Demucs vocal separation + Whisper ASR.
# For GPU acceleration install CUDA PyTorch FIRST (see README).
demucs>=4.0.1,<5.0
faster-whisper>=1.0.3,<2.0
```

- [ ] **Step 3: README 更新**

安装段改为：
````markdown
```bash
pip install -r requirements.txt        # 核心功能
pip install -r requirements-ai.txt     # 可选：AI 识别（Demucs/Whisper）
```
> **Windows 安装包**：不想装 Python 可直接到 [Releases](https://github.com/huqiu0313/AudioToLyrics/releases) 下载 `AudioToLyrics-Setup-*.exe`（安装版不含 AI 识别组件）。
> **GPU 加速**：安装 AI 组件前先装 CUDA 版 PyTorch（原说明保留）
````

- [ ] **Step 4: 验证 pip 解析（GBK 坑回归）**

```bash
"D:/Program/Coding/Python/python.exe" -c "
from pip._internal.utils.encoding import auto_decode
for f in ('requirements.txt', 'requirements-ai.txt'):
    auto_decode(open(f, 'rb').read())
print('REQ_ASCII_OK')
"
```

- [ ] **Step 5: 删除游离分支并提交**

`origin/refactor/theme-and-arch` 上唯一的 d2f8c06（ASCII 修复）已被本任务的新 requirements 完全取代：
```bash
git push origin --delete refactor/theme-and-arch
git add requirements.txt requirements-ai.txt README.md
git commit -m "requirements 拆分为核心+AI 可选（纯 ASCII 修复 GBK 解析崩溃）"
```

---

### Task 4: PyInstaller spec + 本地试构建验证

**Files:**
- Create: `packaging/audiotolyrics.spec`

**Interfaces:**
- Consumes: `utils/paths.py`、`utils/deps.py`（frozen 行为在构建产物上验证）

- [ ] **Step 1: 写 `packaging/audiotolyrics.spec`**

```python
# PyInstaller spec：AudioToLyrics 轻量版（无 AI 组件）
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas, binaries, hiddenimports = [], [], []
for pkg in ('customtkinter', 'imageio_ffmpeg'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=['torch', 'torchaudio', 'demucs', 'faster_whisper', 'ctranslate2'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='AudioToLyrics',
    console=False,          # 窗口模式，无控制台
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    name='AudioToLyrics',
)
```

- [ ] **Step 2: 本地构建**

```bash
"D:/Program/Coding/Python/python.exe" -m pip install -q pyinstaller
"D:/Program/Coding/Python/python.exe" -m PyInstaller --noconfirm --clean packaging/audiotolyrics.spec
```

- [ ] **Step 3: 验证构建产物**

```bash
# 启动冒烟：6 秒内无异常退出、无 stderr
"./dist/AudioToLyrics/AudioToLyrics.exe" & sleep 6; kill %1  # 无 traceback 即过
```
再验证 frozen 写路径：`%APPDATA%/AudioToLyrics/logs/audiotolyrics.log` 在启动后生成；`dist` 内无 torch/demucs 目录（`ls dist/AudioToLyrics/_internal | grep -i torch` 应为空）。

- [ ] **Step 4: Commit**

```bash
git add packaging/audiotolyrics.spec
git commit -m "PyInstaller spec（轻量版 onedir 窗口模式）"
```

---

### Task 5: Inno Setup 脚本 + Release workflow

**Files:**
- Create: `packaging/installer.iss`
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: Task 4 的 `dist/AudioToLyrics/` 产物；`config.VERSION`

- [ ] **Step 1: 写 `packaging/installer.iss`**

```iss
; AudioToLyrics 安装包（Inno Setup 6，版本号由 CI 经 /DAppVersion 传入）
#ifndef AppVersion
  #define AppVersion "4.0"
#endif

[Setup]
AppName=AudioToLyrics
AppVersion={#AppVersion}
AppPublisher=huqiu0313
DefaultDirName={autopf}\AudioToLyrics
DefaultGroupName=AudioToLyrics
OutputDir={#SourcePath}
OutputBaseFilename=AudioToLyrics-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallMode=x64compatible
PrivilegesRequired=admin

[Files]
Source: "..\dist\AudioToLyrics\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\AudioToLyrics"; Filename: "{app}\AudioToLyrics.exe"
Name: "{autodesktop}\AudioToLyrics"; Filename: "{app}\AudioToLyrics.exe"

[Run]
Filename: "{app}\AudioToLyrics.exe"; Flags: postinstall skipifsilent nowait
```
（安装界面为英文：Inno 官方不含简体中文语言包，v1 不做）

- [ ] **Step 2: 写 `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  build-installer:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt pyinstaller

      - name: Build app bundle
        run: pyinstaller --noconfirm --clean packaging/audiotolyrics.spec

      - name: Build installer
        shell: pwsh
        run: |
          $ver = python -c "import config; print(config.VERSION)"
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "/DAppVersion=$ver" packaging/installer.iss
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Publish release
        shell: pwsh
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          $ver = python -c "import config; print(config.VERSION)"
          $exe = "packaging/AudioToLyrics-Setup-$ver.exe"
          $hash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
          "$hash  $(Split-Path $exe -Leaf)" | Out-File -Encoding ascii "$exe.sha256"
          gh release create $env:GITHUB_REF_NAME $exe "$exe.sha256" `
            --title "AudioToLyrics $env:GITHUB_REF_NAME" --generate-notes
```

- [ ] **Step 3: 静态检查**

- workflow YAML 语法：`python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml', encoding='utf-8'))"`（pyyaml 若缺则 pip 装）
- iss 无本机验证手段（未装 Inno），靠 CI 首跑验证

- [ ] **Step 4: Commit**

```bash
git add packaging/installer.iss .github/workflows/release.yml
git commit -m "Inno Setup 安装包脚本 + tag 触发的 Release workflow"
```

---

### Task 6: PR 合并 → 打 tag → 验证 Release

- [ ] **Step 1: 推送并创建 PR**

```bash
git push -u origin feature/packaging
gh pr create --base main --title "Windows 安装包打包与 Release 发布流水线" --body "（设计文档 + 变更摘要 + 验证情况）"
```

- [ ] **Step 2: 合并 PR（待用户确认后），main 打 tag**

```bash
gh pr merge --squash --delete-branch
git checkout main && git pull
git tag v4.0.0 && git push origin v4.0.0
```

- [ ] **Step 3: 盯 workflow 并验证产物**

```bash
gh run list --workflow=release.yml --limit 1
gh run watch            # 失败则 gh run view --log 排查迭代
gh release view v4.0.0  # 确认 setup.exe + sha256 已上传
```

- [ ] **Step 4: 交付**

告知用户 Release 地址，请其下载 setup.exe 实机验证（安装 → 启动 → 联网搜索一首歌 → 卸载），SmartScreen 提示属未签名正常现象。

---

## Self-Review 记录

- Spec 覆盖：§1.1→Task1、§1.2→Task2、§1.3→Task1-Step2、§1.4→Task3、§2→Task4/5、§3→Task5、§4→Task6 ✓ 无缺口
- 占位符：无 TBD/TODO；所有步骤含具体代码/命令
- 类型一致性：`app_data_dir()`、`has_demucs()/has_whisper()`、`make_checkbox(**kwargs)` 跨任务签名一致；Task4 引用 `SPECPATH`（PyInstaller spec 内置变量）正确
