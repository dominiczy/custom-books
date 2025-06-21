"""
Document format converters for various file types.
"""

import re
from pathlib import Path

# Document conversion libraries
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from striprtf.striprtf import rtf_to_text
    RTF_AVAILABLE = True
except ImportError:
    RTF_AVAILABLE = False

try:
    from odf import text, teletype
    from odf.opendocument import load as odf_load
    ODT_AVAILABLE = True
except ImportError:
    ODT_AVAILABLE = False

try:
    from ebooklib import epub as epub_lib
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False


class DocumentConverter:
    """Converts various document formats to text."""
    
    def convert_to_text(self, file_path: Path) -> str:
        """
        Convert various document formats to text.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If the document format is unsupported
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.docx':
            return self._convert_docx_to_text(file_path)
        elif suffix == '.epub':
            return self._convert_epub_to_text(file_path)
        elif suffix == '.rtf':
            return self._convert_rtf_to_text(file_path)
        elif suffix == '.odt':
            return self._convert_odt_to_text(file_path)
        elif suffix == '.txt':
            return self._convert_txt_to_text(file_path)
        else:
            raise ValueError(f"Unsupported document format: {suffix}")
    
    def _convert_docx_to_text(self, file_path: Path) -> str:
        """Convert DOCX file to text."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not available. Install with: pip install python-docx")
        
        doc = DocxDocument(str(file_path))
        text_content = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        return '\n\n'.join(text_content)
    
    def _convert_epub_to_text(self, file_path: Path) -> str:
        """Convert EPUB file to text."""
        if not EPUB_AVAILABLE:
            raise ImportError("ebooklib not available. Install with: pip install ebooklib")
        
        book = epub_lib.read_epub(str(file_path))
        text_content = []
        
        for item in book.get_items():
            if item.get_type() == epub_lib.ITEM_DOCUMENT:
                content = item.get_body_content().decode('utf-8')
                # Simple HTML tag removal (basic)
                clean_text = re.sub(r'<[^>]+>', '', content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                if clean_text:
                    text_content.append(clean_text)
        
        return '\n\n'.join(text_content)
    
    def _convert_rtf_to_text(self, file_path: Path) -> str:
        """Convert RTF file to text."""
        if not RTF_AVAILABLE:
            raise ImportError("striprtf not available. Install with: pip install striprtf")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            rtf_content = f.read()
        
        return rtf_to_text(rtf_content)
    
    def _convert_odt_to_text(self, file_path: Path) -> str:
        """Convert ODT file to text."""
        if not ODT_AVAILABLE:
            raise ImportError("odfpy not available. Install with: pip install odfpy")
        
        doc = odf_load(str(file_path))
        text_content = []
        
        for paragraph in doc.getElementsByType(text.P):
            para_text = teletype.extractText(paragraph)
            if para_text.strip():
                text_content.append(para_text)
        
        return '\n\n'.join(text_content)
    
    def _convert_txt_to_text(self, file_path: Path) -> str:
        """Convert TXT file to text."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()