import os
import zipfile
from bs4 import BeautifulSoup

class EPUBProcessor:
    def __init__(self):
        pass

    def extract_text_from_epub(self, file_path):
        """
        从EPUB文件中提取纯文本内容
        :param file_path: EPUB文件路径
        :return: 提取的纯文本内容
        """
        text_content = ""
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # 获取所有文件列表
                files = zf.namelist()
                
                # 找到内容文件（通常在 OEBPS/ 目录下的 HTML/XHTML 文件）
                content_files = []
                for file in files:
                    # 排除某些目录和文件类型
                    if (file.startswith('OEBPS/') or file.startswith('EPUB/')) and \
                       (file.endswith('.html') or file.endswith('.xhtml') or file.endswith('.htm')):
                        content_files.append(file)
                
                # 如果没有找到 OEBPS 或 EPUB 目录，尝试找其他 HTML 文件
                if not content_files:
                    for file in files:
                        if (file.endswith('.html') or file.endswith('.xhtml') or file.endswith('.htm')):
                            content_files.append(file)
                
                # 按文件名排序，确保内容顺序正确
                content_files.sort()
                
                # 提取每个内容文件的文本
                for content_file in content_files:
                    try:
                        with zf.open(content_file) as f:
                            html_content = f.read().decode('utf-8', errors='ignore')
                            text = self._html_to_text(html_content)
                            if text.strip():
                                text_content += text + '\n\n'
                    except Exception as e:
                        print(f"读取文件 {content_file} 时出错: {e}")
                        continue
                        
        except Exception as e:
            print(f"打开 EPUB 文件失败: {e}")
            return ""
        
        return text_content.strip()
    
    def _html_to_text(self, html_content):
        """
        将HTML内容转换为纯文本
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 获取文本
        text = soup.get_text()
        
        # 清理多余的空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text

    def is_epub_file(self, file_path):
        """
        检查文件是否为EPUB格式
        """
        if not file_path.lower().endswith('.epub'):
            return False
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # EPUB 文件必须包含 mimetype 文件，且内容为 application/epub+zip
                if 'mimetype' in zf.namelist():
                    with zf.open('mimetype') as f:
                        content = f.read().decode('utf-8').strip()
                        return content == 'application/epub+zip'
            return False
        except:
            return False
