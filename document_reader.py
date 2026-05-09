import os
import chardet
from pathlib import Path
from typing import Optional, List, Tuple


class DocumentReader:
    def __init__(self):
        self.file_path: Optional[Path] = None
        self.encoding: str = "utf-8"
        self.file_size: int = 0
        self.total_content: str = ""
        self.page_size: int = 5000
        self.current_page: int = 0
        self.total_pages: int = 0
        self.cache: dict = {}
    
    def detect_encoding(self, file_path: Path) -> str:
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
                result = chardet.detect(raw_data)
                if result['confidence'] > 0.7:
                    return result['encoding']
        except Exception:
            pass
        
        for encoding in ["utf-8", "gbk", "gb2312", "gb18030"]:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                    return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        return "utf-8"
    
    def open_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return False
        
        self.file_path = path
        self.file_size = path.stat().st_size
        self.encoding = self.detect_encoding(path)
        
        try:
            with open(path, 'r', encoding=self.encoding, errors='ignore') as f:
                self.total_content = f.read()
            
            self.total_pages = max(1, (len(self.total_content) + self.page_size - 1) // self.page_size)
            self.current_page = 0
            return True
        except Exception as e:
            print(f'打开文件失败: {e}')
            return False
    
    def get_page(self, page_num: int) -> str:
        if page_num < 0 or page_num >= self.total_pages:
            return ""
        
        cache_key = f"page_{page_num}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        start = page_num * self.page_size
        end = start + self.page_size
        
        content = self.total_content[start:end]
        self.cache[cache_key] = content
        
        if len(self.cache) > 10:
            oldest = list(self.cache.keys())[0]
            del self.cache[oldest]
        
        return content
    
    def get_current_page(self) -> str:
        return self.get_page(self.current_page)
    
    def close_file(self):
        self.file_path = None
        self.encoding = "utf-8"
        self.file_size = 0
        self.total_content = ""
        self.current_page = 0
        self.total_pages = 0
        self.cache = {}
    
    def next_page(self) -> bool:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def go_to_page(self, page_num: int) -> bool:
        if 0 <= page_num < self.total_pages:
            self.current_page = page_num
            return True
        return False
    
    def get_text_for_tts(self, start_pos: int = 0, length: int = 10000) -> str:
        return self.total_content[start_pos:start_pos + length]
    
    def get_total_length(self) -> int:
        return len(self.total_content)
    
    def get_sentences(self, start_pos: int = 0, count: int = 50) -> List[Tuple[int, str]]:
        import re
        text = self.total_content[start_pos:]
        sentences = re.split(r'[。！？.!?\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        result = []
        current_pos = start_pos
        for sentence in sentences[:count]:
            result.append((current_pos, sentence))
            current_pos += len(sentence) + 1
        
        return result
