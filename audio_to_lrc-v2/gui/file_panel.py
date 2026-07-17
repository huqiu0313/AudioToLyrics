"""文件选择面板：添加/删除音频文件，展示待处理文件列表"""

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from gui import styles as S
from config import SUPPORTED_FORMATS


class FilePanel(ctk.CTkFrame):
    """文件管理面板：显示文件列表，支持添加/删除/清空"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=S.BG_PANEL,
            corner_radius=S.CORNER_RADIUS,
            **kwargs,
        )
        self._files: list[str] = []   # 存储文件绝对路径
        self._build_ui()

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def get_files(self) -> list[str]:
        return list(self._files)

    def clear_all(self) -> None:
        self._files.clear()
        self._refresh_tree()

    def set_file_status(self, index: int, status: str) -> None:
        """更新指定索引行的状态列（由外部线程通过 after 调用）"""
        items = self._tree.get_children()
        if 0 <= index - 1 < len(items):
            item = items[index - 1]
            values = list(self._tree.item(item, "values"))
            values[1] = status
            self._tree.item(item, values=values)

    def remove_paths(self, paths: set[str]) -> None:
        """从列表中移除指定路径的文件（用于处理完成后清理）"""
        if not paths:
            return
        self._files = [p for p in self._files if p not in paths]
        self._refresh_tree()

    # ── 内部 UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="📁 待处理文件", font=S.get_font_heading(), text_color=S.FG_PRIMARY,
        ).pack(anchor="w", padx=S.PAD_INNER, pady=(S.PAD_INNER, 4))

        # 按钮栏
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=S.PAD_INNER, pady=(0, S.PAD_BETWEEN))
        for txt, cmd, st in [
            ("添加文件", self._add_files, S.SECONDARY_BTN()),
            ("添加文件夹", self._add_folder, S.SECONDARY_BTN()),
            ("删除选中", self._remove_selected, S.DANGER_BTN()),
            ("清空列表", self.clear_all, S.DANGER_BTN()),
        ]:
            ctk.CTkButton(
                btn_bar, text=txt, width=100, command=cmd, **st,
            ).pack(side="left", padx=(0, 6))

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

        # Treeview 文件列表
        tree_frame = ctk.CTkFrame(self, fg_color=S.BG_INPUT, corner_radius=6)
        tree_frame.pack(fill="both", expand=True, padx=S.PAD_INNER, pady=(0, S.PAD_INNER))

        import tkinter.ttk as ttk

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background=S.BG_INPUT,
            foreground=S.FG_PRIMARY,
            fieldbackground=S.BG_INPUT,
            borderwidth=0,
            rowheight=28,
            font=(S.FONT_FAMILY, 11),
        )
        style.configure("Custom.Treeview.Heading", background=S.BG_PANEL, foreground=S.FG_PRIMARY)
        style.map("Custom.Treeview", background=[("selected", S.FG_ACCENT)])

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("filename", "status"),
            show="headings",
            style="Custom.Treeview",
            selectmode="browse",
        )
        self._tree.heading("filename", text="文件名")
        self._tree.heading("status", text="状态")
        self._tree.column("filename", width=340, minwidth=120)
        self._tree.column("status", width=90, minwidth=60, anchor="center")

        scrollbar = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)

    # ── 事件处理 ──────────────────────────────────────────────────────────────

    def _add_files(self) -> None:
        filetypes = [(f"音频文件 ({' '.join(SUPPORTED_FORMATS)})", " ".join(f"*{e}" for e in SUPPORTED_FORMATS))]
        paths = filedialog.askopenfilenames(title="选择音频文件", filetypes=filetypes)
        for p in paths:
            if p and p not in self._files:
                self._files.append(p)
        self._refresh_tree()

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return
        for root, _, files in os.walk(folder):
            for name in files:
                if Path(name).suffix.lower() in SUPPORTED_FORMATS:
                    full = os.path.join(root, name)
                    if full not in self._files:
                        self._files.append(full)
        self._refresh_tree()

    def _remove_selected(self) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        item = selected[0]
        idx = self._tree.index(item)
        if 0 <= idx < len(self._files):
            self._files.pop(idx)
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for path in self._files:
            name = Path(path).name
            self._tree.insert("", "end", values=(name, "待处理"))
        self._count_label.configure(text=f"共 {len(self._files)} 个文件")
