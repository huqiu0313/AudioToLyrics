"""AudioToLyrics v2 程序入口"""

import sys
import os

# 确保项目根目录在 sys.path 中，以便直接 import core/gui/utils
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from gui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
