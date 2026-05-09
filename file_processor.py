import os
import json
import hashlib
import chardet
from pathlib import Path
from typing import Optional, List, Tuple
from config import (
    ENCODINGS, MAX_RECENT_FILES, CHUNK_SIZE, MAX_SINGLE_LOAD,
    RECENT_FILES_FILE, CACHE_DIR
)

try:
    from epub_processor import EPUBProcessor
    EPUB_SUPPORTED = True
except ImportError:
    EPUB_SUPPORTED = False


class FileProcessor:
    def __init__(self):
        self.current_file: Optional[Path] = None
        self.current_encoding: str = "utf-8"
        self.file_size: int = 0
        self.total_chunks: int = 0
        self.cache: dict = {}
        self.recent_files: List[dict] = self._load_recent_files()
        self.epub_processor = EPUBProcessor() if EPUB_SUPPORTED else None
        self.is_epub = False

    def detect_encoding(self, file_path: Path) -> str:
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
                result = chardet.detect(raw_data)
                if result['confidence'] > 0.7:
                    return result['encoding']
        except Exception:
            pass
        
        for encoding in ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                    return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        return "utf-8"

    def open_file(self, file_path: str) -> Tuple[str, bool]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return "文件不存在", False
        
        self.current_file = path
        self.is_epub = False
        
        # 检查是否为EPUB文件
        if path.suffix.lower() == '.epub' and self.epub_processor:
            return self._open_epub_file(path)
        
        self.file_size = path.stat().st_size
        self.current_encoding = self.detect_encoding(path)
        
        self._add_to_recent_files(path)
        
        if self.file_size <= MAX_SINGLE_LOAD:
            content = self._load_entire_file()
            return content, True
        else:
            self.total_chunks = (self.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            return self._load_chunk(0), True
    
    def _open_epub_file(self, path: Path) -> Tuple[str, bool]:
        """
        处理EPUB文件
        """
        self.is_epub = True
        
        try:
            content = self.epub_processor.extract_text_from_epub(str(path))
            if not content:
                return "无法从EPUB文件中提取内容", False
            
            self.file_size = len(content.encode('utf-8'))
            self.current_encoding = 'utf-8'
            self._add_to_recent_files(path)
            
            if self.file_size <= MAX_SINGLE_LOAD:
                return content, True
            else:
                self.total_chunks = (self.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
                # 将EPUB内容存入缓存以便分块加载
                self.cache['epub_content'] = content
                return content[:CHUNK_SIZE], True
                
        except Exception as e:
            return f"读取EPUB文件失败: {str(e)}", False

    def _load_entire_file(self) -> str:
        try:
            with open(self.current_file, 'r', encoding=self.current_encoding) as f:
                return f.read()
        except Exception as e:
            return f"读取文件失败: {str(e)}"

    def _load_chunk(self, chunk_index: int) -> str:
        if chunk_index < 0 or chunk_index >= self.total_chunks:
            return ""
        
        # EPUB文件从缓存中读取
        if self.is_epub and 'epub_content' in self.cache:
            content = self.cache['epub_content']
            start_pos = chunk_index * CHUNK_SIZE
            return content[start_pos:start_pos + CHUNK_SIZE]
        
        cache_key = self._get_cache_key(chunk_index)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            with open(self.current_file, 'rb') as f:
                start_pos = chunk_index * CHUNK_SIZE
                f.seek(start_pos)
                raw_data = f.read(CHUNK_SIZE)
                content = raw_data.decode(self.current_encoding, errors='replace')
                self.cache[cache_key] = content
                
                if len(self.cache) > 20:
                    self._cleanup_cache()
                
                return content
        except Exception as e:
            return f"加载失败: {str(e)}"

    def _get_cache_key(self, chunk_index: int) -> str:
        file_hash = hashlib.md5(str(self.current_file).encode()).hexdigest()
        return f"{file_hash}_{chunk_index}"

    def _cleanup_cache(self):
        keys = list(self.cache.keys())
        for key in keys[:10]:
            del self.cache[key]

    def get_chunks_around(self, current_chunk: int, count: int = 2) -> List[Tuple[int, str]]:
        chunks = []
        for i in range(current_chunk - count, current_chunk + count + 1):
            if 0 <= i < self.total_chunks:
                chunks.append((i, self._load_chunk(i)))
        return chunks

    def _load_recent_files(self) -> List[dict]:
        try:
            if RECENT_FILES_FILE.exists():
                with open(RECENT_FILES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_recent_files(self):
        try:
            with open(RECENT_FILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.recent_files, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _add_to_recent_files(self, path: Path):
        file_info = {
            "path": str(path.absolute()),
            "name": path.name,
            "last_opened": str(os.path.getmtime(path))
        }
        
        self.recent_files = [f for f in self.recent_files if f["path"] != file_info["path"]]
        self.recent_files.insert(0, file_info)
        self.recent_files = self.recent_files[:MAX_RECENT_FILES]
        self._save_recent_files()

    def get_recent_files(self) -> List[dict]:
        valid_files = []
        for f in self.recent_files:
            if Path(f["path"]).exists():
                valid_files.append(f)
        return valid_files

    def clear_cache(self):
        self.cache.clear()
        for cache_file in CACHE_DIR.glob("*"):
            try:
                cache_file.unlink()
            except Exception:
                pass
