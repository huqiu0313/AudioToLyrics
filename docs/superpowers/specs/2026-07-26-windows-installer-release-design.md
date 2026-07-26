# Windows 安装包 + GitHub Release 发布设计

日期：2026-07-26
状态：已获用户批准（2026-07-26）

## 背景与目标

AudioToLyrics 目前只能以源码方式运行（Python + pip 安装依赖），对非技术用户门槛高。
目标：发布 Windows `setup.exe` 安装包，用户下载安装即可使用，并通过 GitHub Actions 实现可重复的 Release 发布。

## 已确认的决策

| 决策点 | 结论 |
|---|---|
| AI 重依赖（demucs/faster-whisper/torch） | **不打包**（轻量版，安装包约 60-100MB）；安装版中 Demucs/Whisper 选项禁用并提示 |
| 构建位置 | **GitHub Actions**，打 `v*` tag 自动构建并发布 |
| 发布基准 | **先合并 PR #1 到 main**，从 main 打 `v4.0.0` tag |
| GPU 支持 | 安装版不提供（CUDA torch 超 2.5GB 不可打包），需 GPU 的用户走源码版 |

## 设计

### 1. 代码改造

**1.1 新增 `utils/paths.py`（可写数据目录）**

安装到 `Program Files` 后目录只读，运行时写入必须重定向到用户目录：

```python
def app_data_dir() -> Path:
    """源码运行 → 项目根目录（现状不变）；打包运行(sys.frozen) → %APPDATA%/AudioToLyrics"""
```

三个写入点改用它：
- `utils/logging_setup.py` → logs/ 目录
- `utils/settings_store.py` → user_settings.json
- `core/decryptor.py` → tools/um.exe（运行时自举下载目标）

**1.2 AI 功能优雅降级**

- 新增检测（`importlib.util.find_spec("demucs")` / `find_spec("faster_whisper")`），
  缺失时 settings_panel 的 Demucs/Whisper 复选框与模型下拉禁用，提示"（安装版未包含，请用源码版）"
- `core/transcriber._get_model` 的 ImportError 转为友好 RuntimeError（防止 user_settings.json 从源码版带来 use_whisper=true 时报错晦涩）

**1.3 logging 控制台守卫**

PyInstaller 窗口模式下 `sys.stderr` 为 None：`logging_setup` 仅在 `sys.stderr is not None` 时添加控制台 handler（文件 handler 不受影响）。

**1.4 requirements 拆分**

- `requirements.txt`：核心 6 依赖（customtkinter/syncedlyrics/mutagen/requests/zhconv/imageio-ffmpeg）
- `requirements-ai.txt`（新增）：demucs、faster-whisper（源码用户选装，附 GPU torch 说明）
- README 安装说明同步更新

### 2. 打包配置

- **`packaging/audiotolyrics.spec`**：PyInstaller onedir、窗口模式（无控制台）、排除 torch 系；
  `--collect-binaries imageio_ffmpeg`（随包携带 ffmpeg）；`--collect-all customtkinter`
- **`packaging/installer.iss`**：Inno Setup 中文界面，安装到 `{autopf}\AudioToLyrics`，
  开始菜单 + 桌面快捷方式，标准卸载；版本号由 CI 从 `config.VERSION` 提取经 `/DAppVersion` 传入

### 3. GitHub Actions（`.github/workflows/release.yml`）

触发：push tag `v*`。windows-latest（镜像自带 Inno Setup 6）：
1. checkout + setup-python 3.11
2. `pip install -r requirements.txt pyinstaller`
3. `pyinstaller packaging/audiotolyrics.spec` → `dist/AudioToLyrics/`
4. `ISCC /DAppVersion=<config.VERSION> packaging/installer.iss` → `AudioToLyrics-Setup-<version>.exe`
5. 生成 SHA256，`gh release create`（prerelease=false）上传 exe + sha256

无需额外 secrets（用内置 GITHUB_TOKEN）。

### 4. 发布流程

1. squash 合并 PR #1 到 main
2. 新分支 `feature/packaging` 实现 §1–§3
3. 本机（D:\Python3.13，核心依赖已装）试构建验证 spec，构建产物本地跑通"联网搜索官方歌词"路径
4. PR 合并 → main 打 `v4.0.0` tag → Actions 自动发布
5. Inno 脚本本机不预验（未安装 Inno），CI 报错则快速迭代

### 5. 验证清单

- 本地试构建：exe 启动、主题切换、设置持久化（写入 %APPDATA%）、联网搜索歌词+写 tag+存 LRC
- 安装版 AI 选项禁用且提示正确；logs/ 与 user_settings.json 落到 %APPDATA%
- CI 首次跑通后：下载 setup.exe 在干净用户会话安装验证（开始菜单/卸载）

## 明确不做（YAGNI）

不打 GPU 版、不打 AI 双版本、不做自动更新、不做代码签名（SmartScreen 提示属正常）、不做便携 zip 版。

## 风险

| 风险 | 规避 |
|---|---|
| PyInstaller 缺隐式依赖（syncedlyrics/zhconv 动态导入） | 本地先试构建跑通全流程再上 CI；缺失则 spec 加 hiddenimports |
| imageio_ffmpeg 二进制未被收集 | `--collect-binaries`；本地验证视频转码路径 |
| Inno 脚本语法问题 | 简单脚本 + CI 快速迭代 |
| 安装版误带 AI 配置导致报错 | transcriber 友好报错 + GUI 禁用双保险 |
