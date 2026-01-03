#!/usr/bin/env python3
"""
LeafReader — EPUB & FB2 desktop reader.

Minimalist desktop e-book reader built with Python and Qt (PySide6).
Focused on readability, stability, and a clean reading experience.
"""

__author__ = "nikitinsergey1998"
__license__ = "MIT"

import binascii
import html
import json
import sys
import traceback
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from types import TracebackType
from typing import Dict, List, Optional, Tuple, Type

from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub
from lxml import etree, html as lxml_html
from pypdf import PdfReader
from PySide6 import QtCore, QtGui, QtWidgets

STATE_PATH = Path.home() / ".book_reader_state.json"
CACHE_DIR = Path.home() / ".book_reader_cache"
DEFAULT_FONT_SIZE = 12
RESOURCE_SCHEME_EPUB = "epub"
RESOURCE_SCHEME_FB2 = "fb2"


@dataclass
class BookState:
    path: str
    kind: str
    page: int
    scroll: int
    chapter: int
    font_size: int


class RichTextBrowser(QtWidgets.QTextBrowser):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._image_map: Dict[str, bytes] = {}

    def set_image_map(self, image_map: Dict[str, bytes]) -> None:
        self._image_map = image_map

    def loadResource(self, resource_type: int, url: QtCore.QUrl) -> object:
        if resource_type == QtGui.QTextDocument.ResourceType.ImageResource:
            key = url.toString()
            if key.startswith(f"{RESOURCE_SCHEME_EPUB}://") or key.startswith(
                f"{RESOURCE_SCHEME_FB2}://"
            ):
                key = url.path().lstrip("/")
            data = self._image_map.get(key) or self._image_map.get(url.path().lstrip("/"))
            if data:
                image = QtGui.QImage.fromData(data)
                if not image.isNull():
                    return image
        return super().loadResource(resource_type, url)


class BookReader(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Book Reader")
        self.resize(1024, 768)

        self.viewer = RichTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self.viewer.setReadOnly(True)
        self.font_size = DEFAULT_FONT_SIZE
        self.viewer.setFont(QtGui.QFont("Serif", self.font_size))
        self.setCentralWidget(self.viewer)

        self.current_path: Optional[Path] = None
        self.current_kind: Optional[str] = None
        self.current_page = 0
        self.current_chapter = 0
        self.pdf_reader: Optional[PdfReader] = None
        self.epub_html: Optional[str] = None
        self.epub_items: List[Dict[str, str]] = []
        self.image_map: Dict[str, bytes] = {}

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_chapter_dock()
        self.statusBar()
        self._restore_state_on_startup()

    def _build_actions(self) -> None:
        self.open_action = QtGui.QAction("Открыть", self)
        self.open_action.triggered.connect(self.open_file)

        self.next_action = QtGui.QAction("Следующая страница", self)
        self.next_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_PageDown))
        self.next_action.triggered.connect(self.next_page)

        self.prev_action = QtGui.QAction("Предыдущая страница", self)
        self.prev_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_PageUp))
        self.prev_action.triggered.connect(self.prev_page)

        self.fullscreen_action = QtGui.QAction("Полный экран", self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)

        self.zoom_in_action = QtGui.QAction("Увеличить текст", self)
        self.zoom_in_action.setShortcut(QtGui.QKeySequence.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self._adjust_font_size(1))

        self.zoom_out_action = QtGui.QAction("Уменьшить текст", self)
        self.zoom_out_action.setShortcut(QtGui.QKeySequence.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self._adjust_font_size(-1))

        self.reset_zoom_action = QtGui.QAction("Сбросить масштаб", self)
        self.reset_zoom_action.triggered.connect(self._reset_font_size)

        self.clear_cache_action = QtGui.QAction("Очистить кеш", self)
        self.clear_cache_action.triggered.connect(self._clear_cache)

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("Файл")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.clear_cache_action)

        view_menu = menu.addMenu("Просмотр")
        view_menu.addAction(self.fullscreen_action)
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)

        nav_menu = menu.addMenu("Навигация")
        nav_menu.addAction(self.prev_action)
        nav_menu.addAction(self.next_action)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.prev_action)
        toolbar.addAction(self.next_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_out_action)
        toolbar.addAction(self.zoom_in_action)
        toolbar.addSeparator()
        toolbar.addAction(self.fullscreen_action)

    def _build_chapter_dock(self) -> None:
        self.chapter_list = QtWidgets.QListWidget()
        self.chapter_list.currentRowChanged.connect(self._on_chapter_selected)
        dock = QtWidgets.QDockWidget("Оглавление", self)
        dock.setWidget(self.chapter_list)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        dock.setVisible(False)
        self.chapter_dock = dock

    def _restore_state_on_startup(self) -> None:
        state = self._load_state()
        if state and Path(state.path).exists():
            self._open_path(Path(state.path), restore=True)
            self._apply_font_size(state.font_size)
            if state.kind == "pdf":
                self.current_page = state.page
                self._render_pdf_page(state.page)
            elif state.kind == "epub":
                self.current_chapter = state.chapter
                self._render_epub_chapter(state.chapter)
                QtCore.QTimer.singleShot(
                    0, lambda: self.viewer.verticalScrollBar().setValue(state.scroll)
                )
            else:
                QtCore.QTimer.singleShot(
                    0, lambda: self.viewer.verticalScrollBar().setValue(state.scroll)
                )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._save_state()
        super().closeEvent(event)

    def toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def open_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Открыть книгу",
            str(Path.home()),
            "Книги (*.epub *.fb2 *.pdf)"
        )
        if file_path:
            self._open_path(Path(file_path))

    def _open_path(self, path: Path, restore: bool = False) -> None:
        suffix = path.suffix.lower()
        self.current_path = path
        self.current_page = 0
        self.current_chapter = 0
        self.pdf_reader = None
        self.epub_html = None
        self.epub_items = []
        self.image_map = {}
        self.viewer.set_image_map(self.image_map)

        if suffix == ".pdf":
            self.current_kind = "pdf"
            self.pdf_reader = PdfReader(str(path))
            if not restore:
                self._render_pdf_page(0)
            self.chapter_dock.setVisible(False)
        elif suffix == ".epub":
            self.current_kind = "epub"
            self.epub_items, self.image_map = self._load_epub(path)
            self.viewer.set_image_map(self.image_map)
            self._populate_chapters()
            if not restore:
                self._render_epub_chapter(0)
        elif suffix == ".fb2":
            self.current_kind = "fb2"
            self.epub_html, self.image_map = self._load_fb2(path)
            self.viewer.set_image_map(self.image_map)
            self.viewer.setHtml(self.epub_html)
            self.chapter_dock.setVisible(False)
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат")
        self._update_status()

    def _render_pdf_page(self, page_index: int) -> None:
        if not self.pdf_reader:
            return
        max_page = len(self.pdf_reader.pages) - 1
        page_index = max(0, min(page_index, max_page))
        self.current_page = page_index
        page = self.pdf_reader.pages[page_index]
        text = page.extract_text() or ""
        header = f"<h3>Страница {page_index + 1} / {max_page + 1}</h3>"
        content = "<pre style='white-space: pre-wrap;'>" + text + "</pre>"
        self.viewer.setHtml(header + content)
        self.viewer.verticalScrollBar().setValue(0)
        self._update_status()

    def _render_epub_chapter(self, chapter_index: int) -> None:
        if not self.epub_items:
            return
        max_index = len(self.epub_items) - 1
        chapter_index = max(0, min(chapter_index, max_index))
        self.current_chapter = chapter_index
        item = self.epub_items[chapter_index]
        title = html.escape(item["title"])
        content = item["content"]
        self.viewer.setHtml(f"<h3>{title}</h3>{content}")
        self.viewer.verticalScrollBar().setValue(0)
        self.chapter_list.blockSignals(True)
        self.chapter_list.setCurrentRow(chapter_index)
        self.chapter_list.blockSignals(False)
        self._update_status()

    def next_page(self) -> None:
        if self.current_kind == "pdf" and self.pdf_reader:
            self._render_pdf_page(self.current_page + 1)
        elif self.current_kind == "epub":
            self._render_epub_chapter(self.current_chapter + 1)
        else:
            self._scroll_page(1)

    def prev_page(self) -> None:
        if self.current_kind == "pdf" and self.pdf_reader:
            self._render_pdf_page(self.current_page - 1)
        elif self.current_kind == "epub":
            self._render_epub_chapter(self.current_chapter - 1)
        else:
            self._scroll_page(-1)

    def _scroll_page(self, direction: int) -> None:
        scroll = self.viewer.verticalScrollBar()
        step = scroll.pageStep()
        scroll.setValue(scroll.value() + direction * step)

    def _load_epub(self, path: Path) -> Tuple[List[Dict[str, str]], Dict[str, bytes]]:
        cache_path = self._cache_path(path, "epub.json")
        image_map: Dict[str, bytes] = {}
        book = epub.read_epub(str(path))
        if cache_path.exists():
            parts = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            parts = []
            for item in book.get_items():
                if item.get_type() == ITEM_DOCUMENT:
                    title = Path(item.get_name()).stem or "Глава"
                    content = self._rewrite_epub_html(item.get_content().decode("utf-8"))
                    parts.append(
                        {
                            "title": title,
                            "content": content,
                        }
                    )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(parts, ensure_ascii=False), encoding="utf-8")
        for item in book.get_items():
            if item.get_type() == ITEM_IMAGE:
                image_map[item.get_name()] = item.get_content()
                image_map[self._normalize_resource_key(item.get_name())] = item.get_content()
        return parts, image_map

    def _load_fb2(self, path: Path) -> Tuple[str, Dict[str, bytes]]:
        cache_path = self._cache_path(path, "fb2.html")
        image_map: Dict[str, bytes] = {}
        tree = etree.parse(str(path))
        if cache_path.exists():
            cached = cache_path.read_text(encoding="utf-8")
        else:
            cached = ""
        body = tree.find(".//{*}body")
        if body is None:
            return cached, image_map
        for binary in tree.findall(".//{*}binary"):
            binary_id = binary.get("id")
            if binary_id and binary.text:
                try:
                    image_map[binary_id] = QtCore.QByteArray.fromBase64(
                        binary.text.encode("utf-8")
                    ).data()
                except (ValueError, binascii.Error):
                    continue
        if cache_path.exists():
            return cached, image_map
        html_parts = ["<html><body>"]
        for elem in body.iter():
            if elem.tag.endswith("p"):
                text = (elem.text or "").strip()
                if text:
                    html_parts.append(f"<p>{html.escape(text)}</p>")
            elif elem.tag.endswith("image"):
                href = self._fb2_href(elem)
                if href:
                    html_parts.append(
                        f"<img src=\"{RESOURCE_SCHEME_FB2}://{href}\"/>"
                    )
        html_parts.append("</body></html>")
        content = "".join(html_parts)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
        return content, image_map

    def _rewrite_epub_html(self, content: str) -> str:
        try:
            root = lxml_html.fromstring(content)
        except etree.ParserError:
            return content
        for img in root.iter("img"):
            src = img.get("src")
            if not src:
                continue
            normalized = self._normalize_resource_key(src)
            img.set("src", f"{RESOURCE_SCHEME_EPUB}://{normalized}")
        return lxml_html.tostring(root, encoding="unicode")

    def _normalize_resource_key(self, value: str) -> str:
        normalized = value.replace("\\", "/")
        while normalized.startswith("../"):
            normalized = normalized[3:]
        return normalized.lstrip("./").lstrip("/")

    def _fb2_href(self, elem: etree._Element) -> Optional[str]:
        for key, value in elem.attrib.items():
            if key.endswith("href"):
                return value.lstrip("#")
        return None

    def _cache_path(self, path: Path, suffix: str) -> Path:
        key = f"{path.resolve()}::{path.stat().st_mtime}".encode("utf-8")
        digest = sha1(key).hexdigest()
        return CACHE_DIR / digest / suffix

    def _clear_cache(self) -> None:
        if CACHE_DIR.exists():
            for child in CACHE_DIR.rglob("*"):
                if child.is_file():
                    child.unlink()
            for child in sorted(CACHE_DIR.glob("**/*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
        QtWidgets.QMessageBox.information(self, "Кеш", "Кеш очищен.")

    def _populate_chapters(self) -> None:
        self.chapter_list.clear()
        for item in self.epub_items:
            self.chapter_list.addItem(item["title"])
        self.chapter_dock.setVisible(True)

    def _on_chapter_selected(self, row: int) -> None:
        if row >= 0:
            self._render_epub_chapter(row)

    def _adjust_font_size(self, delta: int) -> None:
        self._apply_font_size(self.font_size + delta)

    def _reset_font_size(self) -> None:
        self._apply_font_size(DEFAULT_FONT_SIZE)

    def _apply_font_size(self, size: int) -> None:
        self.font_size = max(8, min(size, 32))
        self.viewer.setFont(QtGui.QFont("Serif", self.font_size))
        self._update_status()

    def _update_status(self) -> None:
        if self.current_kind == "pdf" and self.pdf_reader:
            total = len(self.pdf_reader.pages)
            self.statusBar().showMessage(
                f"PDF: {self.current_page + 1} / {total} • Шрифт {self.font_size}pt"
            )
        elif self.current_kind == "epub" and self.epub_items:
            total = len(self.epub_items)
            self.statusBar().showMessage(
                f"EPUB: глава {self.current_chapter + 1} / {total} • Шрифт {self.font_size}pt"
            )
        elif self.current_kind:
            self.statusBar().showMessage(f"Шрифт {self.font_size}pt")

    def _load_state(self) -> Optional[BookState]:
        if not STATE_PATH.exists():
            return None
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not data:
            return None
        return BookState(
            path=data.get("path", ""),
            kind=data.get("kind", ""),
            page=data.get("page", 0),
            scroll=data.get("scroll", 0),
            chapter=data.get("chapter", 0),
            font_size=data.get("font_size", DEFAULT_FONT_SIZE),
        )

    def _save_state(self) -> None:
        if not self.current_path:
            return
        scroll = self.viewer.verticalScrollBar().value()
        data = {
            "path": str(self.current_path),
            "kind": self.current_kind,
            "page": self.current_page,
            "scroll": scroll,
            "chapter": self.current_chapter,
            "font_size": self.font_size,
        }
        STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)

    def exception_handler(
        exc_type: Type[BaseException],
        exc: BaseException,
        tb: Optional[TracebackType],
    ) -> None:
        message = "".join(traceback.format_exception(exc_type, exc, tb))
        QtWidgets.QMessageBox.critical(None, "Ошибка запуска", message)
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = exception_handler

    try:
        window = BookReader()
        window.show()
        sys.exit(app.exec())
    except Exception:
        exception_handler(*sys.exc_info())


if __name__ == "__main__":
    main()
