"""
PDF text extraction with multiple library fallbacks.
"""

from pathlib import Path
from typing import List

# PDF text extraction libraries (multiple options for better success rate)
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFConverter:
    """PDF text extraction with multiple library fallbacks."""
    
    def extract_text(self, file_path: Path) -> str:
        """
        Convert PDF to text using multiple extraction methods.
        Tries different libraries for best results with various PDF types.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content, or empty string if extraction fails
        """
        pdf_text = ""
        methods_tried = []
        
        # Method 1: PyMuPDF (best for complex layouts, Chinese text)
        if PYMUPDF_AVAILABLE:
            try:
                methods_tried.append("PyMuPDF")
                pdf_text = self._extract_with_pymupdf(file_path)
                
                if len(pdf_text.strip()) > 500:  # Good extraction
                    print(f"✅ PDF extracted successfully using PyMuPDF: {len(pdf_text):,} characters")
                    return pdf_text
            except Exception as e:
                print(f"❌ PyMuPDF extraction failed: {e}")
        
        # Method 2: pdfplumber (good for tables and structured text)  
        if PDFPLUMBER_AVAILABLE and not pdf_text:
            try:
                methods_tried.append("pdfplumber")
                pdf_text = self._extract_with_pdfplumber(file_path)
                
                if len(pdf_text.strip()) > 500:  # Good extraction
                    print(f"✅ PDF extracted successfully using pdfplumber: {len(pdf_text):,} characters")
                    return pdf_text
            except Exception as e:
                print(f"❌ pdfplumber extraction failed: {e}")
        
        # Method 3: PyPDF2 (fallback, basic extraction)
        if PYPDF2_AVAILABLE and not pdf_text:
            try:
                methods_tried.append("PyPDF2")
                pdf_text = self._extract_with_pypdf2(file_path)
                
                if len(pdf_text.strip()) > 100:  # Minimal extraction
                    print(f"⚠️ PDF extracted using PyPDF2 (basic): {len(pdf_text):,} characters")
                    return pdf_text
            except Exception as e:
                print(f"❌ PyPDF2 extraction failed: {e}")
        
        # If all methods failed or yielded poor results
        if not pdf_text or len(pdf_text.strip()) < 100:
            tried_methods = ", ".join(methods_tried) if methods_tried else "none available"
            print(f"❌ All PDF extraction methods failed or yielded poor results")
            print(f"Methods tried: {tried_methods}")
            print(f"Extracted length: {len(pdf_text) if pdf_text else 0} characters")
            return ""  # Return empty string to trigger fallback to direct upload
        
        return pdf_text
    
    def _extract_with_pymupdf(self, file_path: Path) -> str:
        """Extract text using PyMuPDF (fitz)."""
        doc = fitz.open(str(file_path))
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        doc.close()
        return '\n\n'.join(text_parts)
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber."""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        return '\n\n'.join(text_parts)
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2."""
        text_parts = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        return '\n\n'.join(text_parts)