"""
File processing and conversion handler.
Manages the conversion of various document formats to text.
"""

from pathlib import Path
from typing import List, Tuple, Union

from .pdf_converter import PDFConverter
from .document_converter import DocumentConverter


class FileHandler:
    """Handles file processing and format conversion."""
    
    def __init__(self):
        self.pdf_converter = PDFConverter()
        self.doc_converter = DocumentConverter()
    
    def process_files(self, input_files: List[Union[str, Path]]) -> Tuple[str, List[Path]]:
        """
        Process multiple input files, converting them to text where possible.
        
        Args:
            input_files: List of file paths to process
            
        Returns:
            Tuple of (combined_text_content, pdf_files_for_direct_upload)
        """
        combined_content = ""
        pdf_files = []
        
        for file_path in input_files:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"Warning: File {file_path} not found, skipping...")
                continue
                
            suffix = file_path.suffix.lower()
            
            if suffix == '.md':
                content = self._process_markdown(file_path)
                combined_content += f"\n\n# File: {file_path.name}\n\n{content}"
                print(f"Added markdown file: {file_path.name} ({len(content)} characters)")
                
            elif suffix == '.pdf':
                # Try PDF text extraction first, fallback to direct upload
                pdf_text = self.pdf_converter.extract_text(file_path)
                
                if pdf_text and len(pdf_text.strip()) > 100:
                    # PDF extraction successful - treat as text
                    combined_content += f"\n\n# File: {file_path.name}\n\n{pdf_text}"
                    print(f"✅ PDF text extraction successful: {len(pdf_text):,} characters")
                else:
                    # PDF extraction failed - fallback to direct upload
                    print(f"⚠️ PDF text extraction yielded insufficient content, using direct upload method")
                    if self._check_pdf_size(file_path):
                        pdf_files.append(file_path)
                        
            elif suffix in ['.txt', '.docx', '.epub', '.rtf', '.odt']:
                # Convert document to text
                try:
                    print(f"Converting {suffix.upper()} file: {file_path.name}...")
                    content = self.doc_converter.convert_to_text(file_path)
                    combined_content += f"\n\n# File: {file_path.name}\n\n{content}"
                    print(f"Added {suffix.upper()} file: {file_path.name} ({len(content)} characters)")
                except Exception as e:
                    print(f"Warning: Failed to convert {file_path.name}: {e}")
                    continue
                    
            else:
                print(f"Warning: File type {suffix} not supported for {file_path.name}")
                print(f"Supported formats: .md, .pdf, .txt, .docx, .epub, .rtf, .odt")
                print(f"Note: PDFs are first attempted via text extraction, then direct upload if extraction fails")
        
        if not combined_content.strip() and not pdf_files:
            raise ValueError("No valid content found in input files")
            
        return combined_content, pdf_files
    
    def _process_markdown(self, file_path: Path) -> str:
        """Process a markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _check_pdf_size(self, file_path: Path) -> bool:
        """Check if PDF is within size limits for direct upload."""
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 50:
            print(f"Warning: PDF {file_path.name} is {file_size_mb:.1f}MB, exceeds 50MB limit")
            return False
        print(f"Added PDF for direct upload: {file_path.name} ({file_size_mb:.1f}MB)")
        return True