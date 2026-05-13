import sys
import threading
import time
from PyQt5.QtWidgets import (
    QMainWindow, QTextEdit, QToolBar, QAction, QFileDialog, QMenu,
    QSlider, QLabel, QVBoxLayout, QWidget, QPushButton, QComboBox,
    QDockWidget, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QLineEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from document_reader import DocumentReader
from settings_manager import SettingsManager
from bookmark_manager import BookmarkManager, Bookmark
from tts_engine import TTSEngine
from config import (
    APP_NAME, APP_VERSION, MIN_FONT_SIZE, MAX_FONT_SIZE,
    MIN_TTS_RATE, MAX_TTS_RATE, COLOR_THEMES
)


class MainWindow(QMainWindow):
    sentence_changed = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        self.document_reader = DocumentReader()
        self.settings = SettingsManager()
        self.bookmark_manager = BookmarkManager()
        self.tts_engine = TTSEngine()
        self.tts_current_pos = 0
        self._setup_ui()
        self._setup_connections()
        self._apply_settings()
        self._setup_tts_callbacks()
    
    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self._create_toolbar()
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.main_layout.addWidget(self.text_edit)
        
        self._create_page_navigation()
        self._create_control_bar()
        self._create_bookmark_dock()
    
    def _create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        toolbar.addAction(open_action)
        
        close_action = QAction("关闭", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self._close_file)
        toolbar.addAction(close_action)
        
        toolbar.addSeparator()
        
        font_plus_action = QAction("A+", self)
        font_plus_action.triggered.connect(self._increase_font)
        toolbar.addAction(font_plus_action)
        
        font_minus_action = QAction("A-", self)
        font_minus_action.triggered.connect(self._decrease_font)
        toolbar.addAction(font_minus_action)
        
        toolbar.addSeparator()
        
        theme_menu = QMenu("主题", self)
        for theme_name in COLOR_THEMES:
            action = QAction(theme_name, self)
            action.triggered.connect(lambda checked, t=theme_name: self._change_theme(t))
            theme_menu.addAction(action)
        
        theme_action = QAction("主题", self)
        theme_action.setMenu(theme_menu)
        toolbar.addAction(theme_action)
        
        toolbar.addSeparator()
        
        bookmark_action = QAction("添加书签", self)
        bookmark_action.setShortcut("Ctrl+B")
        bookmark_action.triggered.connect(self._add_bookmark)
        toolbar.addAction(bookmark_action)
        
        self.show_bookmark_action = QAction("显示书签", self)
        self.show_bookmark_action.setCheckable(True)
        self.show_bookmark_action.triggered.connect(self._toggle_bookmark_panel)
        toolbar.addAction(self.show_bookmark_action)
        
        toolbar.addSeparator()
        
        self.recent_menu = QMenu("最近打开", self)
        recent_action = QAction("最近打开", self)
        recent_action.setMenu(self.recent_menu)
        toolbar.addAction(recent_action)
    
    def _create_page_navigation(self):
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.clicked.connect(self._prev_page)
        nav_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("第 1/1 页")
        nav_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("下一页")
        self.next_btn.clicked.connect(self._next_page)
        nav_layout.addWidget(self.next_btn)
        
        nav_layout.addWidget(QLabel("跳转到:"))
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(50)
        self.page_input.returnPressed.connect(self._go_to_page_by_input)
        nav_layout.addWidget(self.page_input)
        
        self.jump_btn = QPushButton("跳转")
        self.jump_btn.clicked.connect(self._go_to_page_by_input)
        nav_layout.addWidget(self.jump_btn)
        
        self.jump_error_label = QLabel("")
        self.jump_error_label.setStyleSheet("color: red;")
        nav_layout.addWidget(self.jump_error_label)
        
        nav_layout.addStretch()
        
        nav_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setFixedWidth(150)
        self.search_input.returnPressed.connect(self._search_content)
        nav_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self._search_content)
        nav_layout.addWidget(self.search_btn)
        
        self.search_next_btn = QPushButton("下一个")
        self.search_next_btn.clicked.connect(self._search_next)
        self.search_next_btn.setEnabled(False)
        nav_layout.addWidget(self.search_next_btn)
        
        self.search_result_label = QLabel("")
        nav_layout.addWidget(self.search_result_label)
        
        self.search_matches = []
        self.search_current_index = -1
        
        self.main_layout.addWidget(nav_bar)
    
    def _create_control_bar(self):
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        self.play_btn = QAction("播放", self)
        self.play_btn.triggered.connect(self._toggle_play)
        self.stop_btn = QAction("停止", self)
        self.stop_btn.triggered.connect(self._stop_tts)
        
        toolbar = QToolBar("控制栏")
        toolbar.addActions([self.play_btn, self.stop_btn])
        control_layout.addWidget(toolbar)
        
        control_layout.addWidget(QLabel("语速:"))
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setMinimum(int(MIN_TTS_RATE * 100))
        self.rate_slider.setMaximum(int(MAX_TTS_RATE * 100))
        self.rate_slider.setValue(int(self.settings.get("tts_rate", 1.0) * 100))
        self.rate_slider.setFixedWidth(100)
        control_layout.addWidget(self.rate_slider)
        
        self.rate_label = QLabel("1.0x")
        control_layout.addWidget(self.rate_label)
        
        control_layout.addWidget(QLabel("音量:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(self.settings.get("tts_volume", 0.8) * 100))
        self.volume_slider.setFixedWidth(100)
        control_layout.addWidget(self.volume_slider)
        
        self.voice_combo = QComboBox()
        voices = self.tts_engine.get_voices() if hasattr(self.tts_engine, 'get_voices') else []
        self.voice_combo.addItems(voices)
        self.voice_combo.setCurrentIndex(self.settings.get("tts_voice", 0))
        control_layout.addWidget(QLabel("语音:"))
        control_layout.addWidget(self.voice_combo)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("就绪")
        control_layout.addWidget(self.status_label)
        
        self.addToolBarBreak()
        temp_toolbar = QToolBar()
        temp_toolbar.addWidget(control_bar)
        self.addToolBar(Qt.BottomToolBarArea, temp_toolbar)
    
    def _create_bookmark_dock(self):
        self.bookmark_dock = QDockWidget("书签", self)
        self.bookmark_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        bookmark_widget = QWidget()
        layout = QVBoxLayout(bookmark_widget)
        
        search_box = QLineEdit()
        search_box.setPlaceholderText("搜索书签...")
        search_box.textChanged.connect(self._search_bookmarks)
        layout.addWidget(search_box)
        
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemDoubleClicked.connect(self._go_to_bookmark)
        layout.addWidget(self.bookmark_list)
        
        btn_layout = QHBoxLayout()
        add_folder_btn = QPushButton("新建文件夹")
        delete_bookmark_btn = QPushButton("删除书签")
        btn_layout.addWidget(add_folder_btn)
        btn_layout.addWidget(delete_bookmark_btn)
        layout.addLayout(btn_layout)
        
        self.bookmark_dock.setWidget(bookmark_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.bookmark_dock)
        self.bookmark_dock.hide()
    
    def _setup_connections(self):
        self.rate_slider.valueChanged.connect(self._on_rate_changed)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self.sentence_changed.connect(self._on_sentence_change_gui)
    
    def _setup_tts_callbacks(self):
        self.tts_engine.on_play_start = self._on_tts_start
        self.tts_engine.on_play_end = self._on_tts_end
        self.tts_engine.on_sentence_change = self._on_sentence_change_signal
    
    def _apply_settings(self):
        font = QFont(
            self.settings.get("font_family"),
            self.settings.get("font_size")
        )
        self.text_edit.setFont(font)
        
        colors = self.settings.get_theme_colors()
        self._apply_colors(colors)
        
        if hasattr(self.tts_engine, 'set_rate'):
            self.tts_engine.set_rate(self.settings.get("tts_rate", 1.0))
        if hasattr(self.tts_engine, 'set_volume'):
            self.tts_engine.set_volume(self.settings.get("tts_volume", 0.8))
        if hasattr(self.tts_engine, 'set_voice'):
            self.tts_engine.set_voice(self.settings.get("tts_voice", 0))
    
    def _apply_colors(self, colors):
        style = f"""
            QTextEdit {{
                background-color: {colors['background']};
                color: {colors['foreground']};
            }}
        """
        self.text_edit.setStyleSheet(style)
    
    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", "文本和EPUB文件 (*.txt *.epub);;文本文件 (*.txt);;EPUB文件 (*.epub);;所有文件 (*.*)"
        )
        if file_path:
            self._load_file(file_path)
    
    def _close_file(self):
        if self.document_reader.file_path:
            self.tts_engine.stop()
            self.document_reader.close_file()
            self.text_edit.clear()
            self.page_label.setText("第 1/1 页")
            self.setWindowTitle(f"{APP_NAME}")
            self._update_bookmark_list()
    
    def _load_file(self, file_path):
        if self.document_reader.open_file(file_path):
            self._update_page_display()
            self.setWindowTitle(f"{file_path} - {APP_NAME}")
            self._update_bookmark_list()

            bookmarks = self.bookmark_manager.get_bookmarks_for_file(file_path)
            if bookmarks:
                latest = max(bookmarks, key=lambda b: b.timestamp)
                self._jump_to_position(latest.position)
    
    def _update_page_display(self):
        content = self.document_reader.get_current_page()
        self.text_edit.setPlainText(content)
        self.page_label.setText(f"第 {self.document_reader.current_page + 1}/{self.document_reader.total_pages} 页")
        self.prev_btn.setEnabled(self.document_reader.current_page > 0)
        self.next_btn.setEnabled(self.document_reader.current_page < self.document_reader.total_pages - 1)
    
    def _prev_page(self):
        if self.document_reader.prev_page():
            self._update_page_display()
    
    def _next_page(self):
        if self.document_reader.next_page():
            self._update_page_display()
    
    def _go_to_page_by_input(self):
        self.jump_error_label.setText("")
        input_text = self.page_input.text().strip()
        
        if not input_text.isdigit():
            self.jump_error_label.setText("请输入有效数字")
            return
        
        target_page = int(input_text) - 1
        
        if target_page < 0 or target_page >= self.document_reader.total_pages:
            self.jump_error_label.setText(f"页码范围: 1-{self.document_reader.total_pages}")
            return
        
        if self.document_reader.go_to_page(target_page):
            self._update_page_display()
            self.page_input.clear()
    
    def _search_content(self):
        search_text = self.search_input.text().strip()
        
        if not search_text:
            self.search_result_label.setText("")
            self.search_next_btn.setEnabled(False)
            self.search_matches = []
            self.search_current_index = -1
            return
        
        self.search_matches = []
        total_content = self.document_reader.total_content
        page_size = self.document_reader.page_size
        index = 0
        
        while index < len(total_content):
            pos = total_content.find(search_text, index)
            if pos == -1:
                break
            
            page_num = pos // page_size
            page_offset = pos % page_size
            
            context_start = max(pos - 20, 0)
            context_end = min(pos + len(search_text) + 20, len(total_content))
            context = total_content[context_start:context_end]
            if context_start > 0:
                context = "..." + context
            if context_end < len(total_content):
                context = context + "..."
            
            self.search_matches.append({
                'pos': pos,
                'page': page_num,
                'context': context
            })
            
            index = pos + len(search_text)
        
        if not self.search_matches:
            self.search_result_label.setText("未找到匹配结果")
            self.search_next_btn.setEnabled(False)
            self.search_current_index = -1
        else:
            self.search_current_index = 0
            match = self.search_matches[self.search_current_index]
            self.search_result_label.setText(f"找到 {len(self.search_matches)} 个结果 (1/{len(self.search_matches)})")
            self.search_next_btn.setEnabled(True)
            self._jump_to_search_match(match)
    
    def _search_next(self):
        if not self.search_matches or self.search_current_index < 0:
            return
        
        self.search_current_index += 1
        if self.search_current_index >= len(self.search_matches):
            self.search_current_index = 0
        
        match = self.search_matches[self.search_current_index]
        self.search_result_label.setText(f"找到 {len(self.search_matches)} 个结果 ({self.search_current_index + 1}/{len(self.search_matches)})")
        self._jump_to_search_match(match)
    
    def _jump_to_search_match(self, match):
        self.document_reader.go_to_page(match['page'])
        self._update_page_display()
        
        cursor = self.text_edit.textCursor()
        cursor.setPosition(match['pos'] % self.document_reader.page_size)
        cursor.setPosition((match['pos'] % self.document_reader.page_size) + len(self.search_input.text()), QTextCursor.KeepAnchor)
        
        format = cursor.charFormat()
        format.setBackground(Qt.yellow)
        cursor.setCharFormat(format)
        
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
    
    def _increase_font(self):
        size = self.settings.get("font_size") + 1
        size = min(size, MAX_FONT_SIZE)
        self.settings.set("font_size", size)
        font = self.text_edit.font()
        font.setPointSize(size)
        self.text_edit.setFont(font)
    
    def _decrease_font(self):
        size = self.settings.get("font_size") - 1
        size = max(size, MIN_FONT_SIZE)
        self.settings.set("font_size", size)
        font = self.text_edit.font()
        font.setPointSize(size)
        self.text_edit.setFont(font)
    
    def _change_theme(self, theme_name):
        self.settings.set("color_theme", theme_name)
        colors = self.settings.get_theme_colors()
        self._apply_colors(colors)
    
    def _toggle_bookmark_panel(self, checked):
        if checked:
            self.bookmark_dock.show()
        else:
            self.bookmark_dock.hide()
    
    def _add_bookmark(self):
        if not self.document_reader.file_path:
            return

        cursor = self.text_edit.textCursor()
        page_offset = cursor.position()
        absolute_pos = self.document_reader.current_page * self.document_reader.page_size + page_offset

        default_name = "书签"
        sentences = self.document_reader.get_sentences(absolute_pos, 1)
        if sentences:
            first_sentence = sentences[0][1]
            default_name = first_sentence[:5] if len(first_sentence) >= 5 else first_sentence

        dialog = QDialog(self)
        dialog.setWindowTitle("添加书签")
        layout = QVBoxLayout(dialog)

        name_edit = QLineEdit(default_name)
        layout.addWidget(QLabel("名称:"))
        layout.addWidget(name_edit)
        
        folder_combo = QComboBox()
        folder_combo.addItems(self.bookmark_manager.folders)
        layout.addWidget(QLabel("文件夹:"))
        layout.addWidget(folder_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            bookmark = Bookmark(
                str(self.document_reader.file_path),
                absolute_pos,
                name_edit.text(),
                folder_combo.currentText()
            )
            self.bookmark_manager.add_bookmark(bookmark)
            self._update_bookmark_list()
    
    def _go_to_bookmark(self, item):
        position = item.data(Qt.UserRole)
        self._jump_to_position(position)
    
    def _jump_to_position(self, position):
        page_num = position // self.document_reader.page_size
        if self.document_reader.go_to_page(page_num):
            self._update_page_display()
            cursor = self.text_edit.textCursor()
            cursor.setPosition(position % self.document_reader.page_size)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()
    
    def _search_bookmarks(self, text):
        self.bookmark_list.clear()
        if not self.document_reader.file_path:
            return
        
        file_path = str(self.document_reader.file_path)
        if text:
            try:
                target_path = Path(file_path).resolve()
                bookmarks = [b for b in self.bookmark_manager.search_bookmarks(text) if Path(b.file_path).resolve() == target_path]
            except Exception:
                bookmarks = [b for b in self.bookmark_manager.search_bookmarks(text) if b.file_path == file_path]
        else:
            bookmarks = self.bookmark_manager.get_bookmarks_for_file(file_path)
        
        for b in bookmarks:
            item = QListWidgetItem(b.name)
            item.setData(Qt.UserRole, b.position)
            self.bookmark_list.addItem(item)
    
    def _update_bookmark_list(self):
        self.bookmark_list.clear()
        if self.document_reader.file_path:
            file_path = str(self.document_reader.file_path)
            bookmarks = self.bookmark_manager.get_bookmarks_for_file(file_path)
            for b in bookmarks:
                item = QListWidgetItem(b.name)
                item.setData(Qt.UserRole, b.position)
                self.bookmark_list.addItem(item)
    
    def _toggle_play(self):
        if self.tts_engine.is_playing_status():
            return
        
        cursor = self.text_edit.textCursor()
        page_offset = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        self.tts_current_pos = self.document_reader.current_page * self.document_reader.page_size + page_offset
        
        text_to_play = self.document_reader.get_text_for_tts(self.tts_current_pos, 50000)
        self.tts_engine.play(text_to_play, self.tts_current_pos)
    
    def _toggle_pause(self):
        if self.tts_engine.is_playing_status():
            if self.tts_engine.is_paused_status():
                self.tts_engine.resume()
            else:
                self.tts_engine.pause()
    
    def _stop_tts(self):
        self.tts_engine.stop()
        self._clear_highlights()
    
    def _on_tts_start(self):
        self.status_label.setText("正在朗读...")
    
    def _on_tts_end(self):
        self.status_label.setText("朗读结束")
        self.is_playing = False
    
    def _on_sentence_change_signal(self, index, sentence):
        self.sentence_changed.emit(index, sentence)
    
    def _on_sentence_change_gui(self, index, sentence):
        self._clear_highlights()
        
        if not self.document_reader.total_content:
            return
        
        search_start = max(0, self.tts_current_pos - 1000)
        pos = self.document_reader.total_content.find(sentence, search_start, search_start + 20000)
        if pos >= 0:
            self.tts_current_pos = pos
            page_num = pos // self.document_reader.page_size
            page_offset = pos % self.document_reader.page_size
            
            if page_num != self.document_reader.current_page:
                self.document_reader.go_to_page(page_num)
                self._update_page_display()
            
            cursor = self.text_edit.textCursor()
            cursor.setPosition(page_offset)
            cursor.setPosition(page_offset + len(sentence), QTextCursor.KeepAnchor)
            
            format = cursor.charFormat()
            format.setBackground(Qt.yellow)
            cursor.setCharFormat(format)
            
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()
    
    def _clear_highlights(self):
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        format = cursor.charFormat()
        format.clearBackground()
        cursor.setCharFormat(format)
    
    def _on_rate_changed(self, value):
        rate = value / 100.0
        if hasattr(self.tts_engine, 'set_rate'):
            self.tts_engine.set_rate(rate)
        self.rate_label.setText(f"{rate:.1f}x")
        self.settings.set("tts_rate", rate)
    
    def _on_volume_changed(self, value):
        volume = value / 100.0
        if hasattr(self.tts_engine, 'set_volume'):
            self.tts_engine.set_volume(volume)
        self.settings.set("tts_volume", volume)
    
    def _on_voice_changed(self, index):
        if hasattr(self.tts_engine, 'set_voice'):
            self.tts_engine.set_voice(index)
        self.settings.set("tts_voice", index)
    
    def closeEvent(self, event):
        self._stop_tts()
        super().closeEvent(event)
