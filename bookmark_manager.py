import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from config import BOOKMARKS_FILE


class Bookmark:
    def __init__(self, file_path: str, position: int, name: str = "", 
                 folder: str = "默认", timestamp: float = None):
        self.file_path = file_path
        self.position = position
        self.name = name or Path(file_path).name
        self.folder = folder
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "position": self.position,
            "name": self.name,
            "folder": self.folder,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Bookmark':
        return cls(
            data["file_path"],
            data["position"],
            data.get("name", ""),
            data.get("folder", "默认"),
            data.get("timestamp")
        )


class BookmarkManager:
    def __init__(self):
        self.bookmarks: List[Bookmark] = []
        self.folders: List[str] = ["默认"]
        self._load_bookmarks()

    def _load_bookmarks(self):
        try:
            if BOOKMARKS_FILE.exists():
                with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.bookmarks = [Bookmark.from_dict(b) for b in data.get("bookmarks", [])]
                    self.folders = data.get("folders", ["默认"])
        except Exception:
            self.bookmarks = []
            self.folders = ["默认"]

    def _save_bookmarks(self):
        try:
            data = {
                "bookmarks": [b.to_dict() for b in self.bookmarks],
                "folders": self.folders
            }
            with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_bookmark(self, bookmark: Bookmark) -> bool:
        self.bookmarks.append(bookmark)
        self._save_bookmarks()
        return True

    def remove_bookmark(self, index: int) -> bool:
        if 0 <= index < len(self.bookmarks):
            del self.bookmarks[index]
            self._save_bookmarks()
            return True
        return False

    def update_bookmark(self, index: int, name: Optional[str] = None, 
                       folder: Optional[str] = None) -> bool:
        if 0 <= index < len(self.bookmarks):
            if name is not None:
                self.bookmarks[index].name = name
            if folder is not None:
                self.bookmarks[index].folder = folder
            self._save_bookmarks()
            return True
        return False

    def get_bookmarks_for_file(self, file_path: str) -> List[Bookmark]:
        try:
            target_path = Path(file_path).resolve()
            return [b for b in self.bookmarks if Path(b.file_path).resolve() == target_path]
        except Exception:
            return [b for b in self.bookmarks if b.file_path == file_path]

    def get_bookmarks_by_folder(self, folder: str) -> List[Bookmark]:
        return [b for b in self.bookmarks if b.folder == folder]

    def search_bookmarks(self, query: str) -> List[Bookmark]:
        query = query.lower()
        return [b for b in self.bookmarks if query in b.name.lower()]

    def get_all_bookmarks(self) -> List[Bookmark]:
        return list(self.bookmarks)

    def add_folder(self, folder_name: str) -> bool:
        if folder_name and folder_name not in self.folders:
            self.folders.append(folder_name)
            self._save_bookmarks()
            return True
        return False

    def rename_folder(self, old_name: str, new_name: str) -> bool:
        if old_name in self.folders and new_name and new_name not in self.folders:
            idx = self.folders.index(old_name)
            self.folders[idx] = new_name
            for b in self.bookmarks:
                if b.folder == old_name:
                    b.folder = new_name
            self._save_bookmarks()
            return True
        return False

    def delete_folder(self, folder_name: str, move_to: str = "默认") -> bool:
        if folder_name in self.folders and folder_name != "默认":
            self.folders.remove(folder_name)
            for b in self.bookmarks:
                if b.folder == folder_name:
                    b.folder = move_to
            self._save_bookmarks()
            return True
        return False
