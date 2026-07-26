"""文件选择面板：添加/删除音视频文件，展示待处理文件列表（CTk 原生行列表）"""

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from gui import styles as S
from config import SUPPORTED_MEDIA_FORMATS


class _FileRow(ctk.CTkFrame):
    """文件列表的一行：文件名 + 状态，整行可点击选中"""

    def __init__(self, master, path: str, on_select, **kwargs):
        super().__init__(
            master, fg_color="transparent", corner_radius=S.CORNER_RADIUS_SM, **kwargs
        )
        self.path = path
        self._on_select = on_select

        self._name_label = ctk.CTkLabel(
            self, text=Path(path).name, font=S.get_font_body(),
            text_color=S.FG_PRIMARY, anchor="w",
        )
        self._name_label.pack(
            side="left", fill="x", expand=True, padx=(S.PAD_BETWEEN, 4), pady=4
        )

        self._status_label = ctk.CTkLabel(
            self, text="待处理", font=S.get_font_small(),
            text_color=S.LEVEL_COLORS["pending"], width=70,
        )
        self._status_label.pack(side="right", padx=(4, S.PAD_BETWEEN))

        # 整行（含子控件）可点击选中
        for widget in (self, self._name_label, self._status_label):
            widget.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event) -> None:
        self._on_select(self.path)

    def set_status(self, text: str, level: str = "info") -> None:
        """更新状态文字并按级别着色（level 见 styles.LEVEL_COLORS）"""
        self._status_label.configure(
            text=text, text_color=S.LEVEL_COLORS.get(level, S.FG_SECONDARY)
        )

    def set_selected(self, selected: bool) -> None:
        self.configure(fg_color=S.BG_INPUT if selected else "transparent")


class FilePanel(ctk.CTkFrame):
    """文件管理面板：显示文件列表，支持添加/删除/清空"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=S.BG_PANEL,
            corner_radius=S.CORNER_RADIUS,
            **kwargs,
        )
        self._files: list[str] = []              # 文件绝对路径（顺序即处理顺序）
        self._rows: dict[str, _FileRow] = {}     # path → 行控件（键控，免疫索引漂移）
        self._selected_path: str | None = None
        self._build_ui()

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def get_files(self) -> list[str]:
        return list(self._files)

    def clear_all(self) -> None:
        self._files.clear()
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        self._selected_path = None
        self._update_count()

    def set_file_status(self, path: str, status: str, level: str = "info") -> None:
        """更新指定文件的状态列（由外部线程通过 after 调度到主线程调用）"""
        row = self._rows.get(path)
        if row:
            row.set_status(status, level)

    def remove_paths(self, paths: set[str]) -> None:
        """从列表中移除指定路径的文件（用于处理完成后清理）"""
        if not paths:
            return
        self._files = [p for p in self._files if p not in paths]
        for p in paths:
            row = self._rows.pop(p, None)
            if row:
                row.destroy()
        if self._selected_path in paths:
            self._selected_path = None
        self._update_count()

    # ── 内部 UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="📁 待处理文件", font=S.get_font_heading(), text_color=S.FG_PRIMARY,
        ).pack(anchor="w", padx=S.PAD_INNER, pady=(S.PAD_INNER, 4))

        # 按钮栏
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=S.PAD_INNER, pady=(0, S.PAD_BETWEEN))
        for txt, cmd, style in [
            ("添加文件", self._add_files, "secondary"),
            ("添加文件夹", self._add_folder, "secondary"),
            ("删除选中", self._remove_selected, "danger"),
            ("清空列表", self.clear_all, "danger"),
        ]:
            S.make_button(btn_bar, txt, cmd, style=style, width=S.BTN_WIDTH_SM).pack(
                side="left", padx=(0, 6)
            )

        # 文件命名提示
        ctk.CTkLabel(
            self,
            text="💡 文件名建议：歌名 或 歌手-歌名 或 歌名-歌手",
            font=S.get_font_small(),
            text_color=S.FG_SECONDARY,
        ).pack(anchor="w", padx=S.PAD_INNER, pady=(0, 4))

        # 文件计数
        self._count_label = ctk.CTkLabel(
            self, text="共 0 个文件", font=S.get_font_small(), text_color=S.FG_SECONDARY
        )
        self._count_label.pack(anchor="w", padx=S.PAD_INNER, pady=(0, 4))

        # 文件列表（可滚动）
        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=S.BG_INPUT, corner_radius=S.CORNER_RADIUS_SM
        )
        self._list_frame.pack(
            fill="both", expand=True, padx=S.PAD_INNER, pady=(0, S.PAD_INNER)
        )

    # ── 事件处理 ──────────────────────────────────────────────────────────────

    def _add_files(self) -> None:
        filetypes = [(
            f"音视频文件 ({' '.join(SUPPORTED_MEDIA_FORMATS)})",
            " ".join(f"*{e}" for e in SUPPORTED_MEDIA_FORMATS),
        )]
        paths = filedialog.askopenfilenames(title="选择音视频文件", filetypes=filetypes)
        self._add_paths(paths)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return
        paths = []
        for root, _, files in os.walk(folder):
            for name in files:
                if Path(name).suffix.lower() in SUPPORTED_MEDIA_FORMATS:
                    paths.append(os.path.join(root, name))
        self._add_paths(paths)

    def _add_paths(self, paths) -> None:
        added = False
        for p in paths:
            if p and p not in self._rows:
                self._files.append(p)
                self._create_row(p)
                added = True
        if added:
            self._update_count()

    def _create_row(self, path: str) -> None:
        row = _FileRow(self._list_frame, path, on_select=self._on_row_select)
        row.pack(fill="x", padx=2, pady=1)
        self._rows[path] = row

    def _on_row_select(self, path: str) -> None:
        if self._selected_path == path:
            return
        old = self._rows.get(self._selected_path)
        if old:
            old.set_selected(False)
        self._selected_path = path
        row = self._rows.get(path)
        if row:
            row.set_selected(True)

    def _remove_selected(self) -> None:
        if self._selected_path:
            self.remove_paths({self._selected_path})

    def _update_count(self) -> None:
        self._count_label.configure(text=f"共 {len(self._files)} 个文件")
