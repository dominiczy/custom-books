#!/usr/bin/env python3
"""
Convert markdown files to EPUB ebook using EbookLib
Supports various markdown structures and formats
"""

import re
import sys
import argparse
from pathlib import Path
from ebooklib import epub
import markdown
from markdown.extensions import toc
import google.generativeai as genai
import os
from typing import List, Union
import math
from dotenv import load_dotenv

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


def _convert_docx_to_text(file_path: Path) -> str:
    """Convert DOCX file to text"""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx not available. Install with: pip install python-docx")
    
    doc = DocxDocument(str(file_path))
    text_content = []
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_content.append(paragraph.text)
    
    return '\n\n'.join(text_content)


def _convert_epub_to_text(file_path: Path) -> str:
    """Convert EPUB file to text"""
    if not EPUB_AVAILABLE:
        raise ImportError("ebooklib not available. Install with: pip install ebooklib")
    
    book = epub_lib.read_epub(str(file_path))
    text_content = []
    
    for item in book.get_items():
        if item.get_type() == epub_lib.ITEM_DOCUMENT:
            content = item.get_body_content().decode('utf-8')
            # Simple HTML tag removal (basic)
            import re
            clean_text = re.sub(r'<[^>]+>', '', content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if clean_text:
                text_content.append(clean_text)
    
    return '\n\n'.join(text_content)


def _convert_rtf_to_text(file_path: Path) -> str:
    """Convert RTF file to text"""
    if not RTF_AVAILABLE:
        raise ImportError("striprtf not available. Install with: pip install striprtf")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        rtf_content = f.read()
    
    return rtf_to_text(rtf_content)


def _convert_odt_to_text(file_path: Path) -> str:
    """Convert ODT file to text"""
    if not ODT_AVAILABLE:
        raise ImportError("odfpy not available. Install with: pip install odfpy")
    
    doc = odf_load(str(file_path))
    text_content = []
    
    for paragraph in doc.getElementsByType(text.P):
        para_text = teletype.extractText(paragraph)
        if para_text.strip():
            text_content.append(para_text)
    
    return '\n\n'.join(text_content)


def _convert_pdf_to_text(file_path: Path) -> str:
    """
    Convert PDF to text using multiple extraction methods.
    Tries different libraries for best results with various PDF types.
    """
    pdf_text = ""
    methods_tried = []
    
    # Method 1: PyMuPDF (best for complex layouts, Chinese text)
    if PYMUPDF_AVAILABLE:
        try:
            methods_tried.append("PyMuPDF")
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            doc.close()
            pdf_text = '\n\n'.join(text_parts)
            
            if len(pdf_text.strip()) > 500:  # Good extraction
                print(f"✅ PDF extracted successfully using PyMuPDF: {len(pdf_text):,} characters")
                return pdf_text
        except Exception as e:
            print(f"❌ PyMuPDF extraction failed: {e}")
    
    # Method 2: pdfplumber (good for tables and structured text)  
    if PDFPLUMBER_AVAILABLE and not pdf_text:
        try:
            methods_tried.append("pdfplumber")
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            pdf_text = '\n\n'.join(text_parts)
            
            if len(pdf_text.strip()) > 500:  # Good extraction
                print(f"✅ PDF extracted successfully using pdfplumber: {len(pdf_text):,} characters")
                return pdf_text
        except Exception as e:
            print(f"❌ pdfplumber extraction failed: {e}")
    
    # Method 3: PyPDF2 (fallback, basic extraction)
    if PYPDF2_AVAILABLE and not pdf_text:
        try:
            methods_tried.append("PyPDF2")
            text_parts = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            pdf_text = '\n\n'.join(text_parts)
            
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


def _convert_document_to_text(file_path: Path) -> str:
    """Convert various document formats to text"""
    suffix = file_path.suffix.lower()
    
    try:
        if suffix == '.pdf':
            return _convert_pdf_to_text(file_path)
        elif suffix == '.docx':
            return _convert_docx_to_text(file_path)
        elif suffix == '.epub':
            return _convert_epub_to_text(file_path)
        elif suffix == '.rtf':
            return _convert_rtf_to_text(file_path)
        elif suffix == '.odt':
            return _convert_odt_to_text(file_path)
        elif suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported document format: {suffix}")
    except Exception as e:
        print(f"Error converting {file_path.name}: {e}")
        raise


def parse_markdown_file(filepath):
    """Parse the markdown file and extract chapters with content using markdown library"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_chapter = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        # Check for header levels - only ## starts new chapters, others are subheaders
        header_match = re.match(r'^(#{2,6})\s+(.+)', line)
        if header_match:
            header_level = len(header_match.group(1))
            header_text = header_match.group(2).strip()
            
            if header_level == 2:  # ## level - new chapter
                # Save previous chapter if exists and has meaningful content
                if current_chapter and current_content:
                    # Filter out empty lines and check if there's actual content
                    filtered_content = [l for l in current_content if l.strip()]
                    if filtered_content:
                        chapters.append({
                            'title': current_chapter,
                            'content': '\n'.join(current_content)
                        })

                # Start new chapter
                current_chapter = header_text
                current_content = []
            else:  # ### and lower - subheaders within current chapter
                if current_chapter:  # Only add if we're in a chapter
                    current_content.append(line)

        elif current_chapter:  # We're in a chapter
            current_content.append(line)

    # Add the last chapter
    if current_chapter and current_content:
        filtered_content = [l for l in current_content if l.strip()]
        if filtered_content:
            chapters.append({
                'title': current_chapter,
                'content': '\n'.join(current_content)
            })

    return chapters


def detect_content_type(content):
    """Detect the type of content to apply appropriate formatting"""
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Check for Chinese characters
    has_chinese = any(re.search(r'[\u4e00-\u9fff]', line) for line in lines)
    
    # Check for special translation sections
    has_mitchell = any('Stephen Mitchell Translation' in line for line in lines)
    has_special_translation = any(re.search(r'\*\*.*Translation.*\*\*', line) for line in lines)
    
    return {
        'has_chinese': has_chinese,
        'has_mitchell': has_mitchell,
        'has_special_translation': has_special_translation
    }


def create_chapter_html(chapter_data, _book_config):
    """Create HTML content for a chapter"""
    title = chapter_data['title']
    content = chapter_data['content']

    # Validate content
    if not content or not content.strip():
        return create_minimal_html(title)

    content_type = detect_content_type(content)
    
    # Create HTML based on content type
    if content_type['has_chinese'] and content_type['has_special_translation']:
        return create_chinese_translation_html(title, content, content_type)
    else:
        return create_standard_html(title, content)


def create_minimal_html(title):
    """Create minimal HTML for empty chapters"""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
</head>
<body>
    <h1>{title}</h1>
    <p>Content not available</p>
</body>
</html>"""


def create_standard_html(title, content):
    """Create standard HTML for regular markdown content"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            margin: 2em;
        }}
        h1 {{
            color: #2F4F4F;
            text-align: center;
            border-bottom: 2px solid #2F4F4F;
            padding-bottom: 0.5em;
        }}
        h2, h3, h4, h5, h6 {{
            color: #2F4F4F;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        p {{
            margin: 1em 0;
            text-align: justify;
        }}
        .special-section {{
            background-color: #F5F5DC;
            padding: 1em;
            border-left: 4px solid #2F4F4F;
            margin: 2em 0;
        }}
        .special-section h3 {{
            color: #2F4F4F;
            margin-top: 0;
        }}
        blockquote {{
            border-left: 4px solid #ccc;
            margin-left: 0;
            padding-left: 1em;
            color: #666;
            font-style: italic;
        }}
        ul, ol {{
            margin: 1em 0;
            padding-left: 2em;
        }}
        li {{
            margin: 0.5em 0;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 0.2em 0.4em;
            font-family: 'Courier New', monospace;
            border-radius: 3px;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""
    
    # First, separate special sections from regular content
    lines = content.split('\n')
    regular_content = []
    in_special_section = False
    special_content = []
    
    for line in lines:
        # Check for special sections marked with **
        if re.match(r'\*\*.*\*\*', line):
            if in_special_section and special_content:
                # Process previous special section
                section_text = '\n'.join(special_content)
                md = markdown.Markdown(extensions=['extra', 'nl2br'])
                formatted_text = md.convert(section_text)
                section_title = re.sub(r'\*\*(.+)\*\*.*', r'\1', lines[lines.index(line) - len(special_content) - 1])
                html += f'    <div class="special-section">\n        <h3>{section_title}:</h3>\n'
                html += f'        <div class="special-text">{formatted_text}</div>\n    </div>\n'
                special_content = []
            
            # Start new special section
            section_title = re.sub(r'\*\*(.+)\*\*.*', r'\1', line)
            in_special_section = True
            continue
        
        if in_special_section:
            special_content.append(line)
        else:
            regular_content.append(line)
    
    # Process any remaining special section
    if in_special_section and special_content:
        section_text = '\n'.join(special_content)
        md = markdown.Markdown(extensions=['extra', 'nl2br'])
        formatted_text = md.convert(section_text)
        # Get the section title from the last ** line
        last_special_line = None
        for line in reversed(lines):
            if re.match(r'\*\*.*\*\*', line):
                last_special_line = line
                break
        if last_special_line:
            section_title = re.sub(r'\*\*(.+)\*\*.*', r'\1', last_special_line)
            html += f'    <div class="special-section">\n        <h3>{section_title}:</h3>\n'
            html += f'        <div class="special-text">{formatted_text}</div>\n    </div>\n'
    
    # Process regular markdown content
    if regular_content:
        regular_markdown = '\n'.join(regular_content)
        # Use markdown library to convert to HTML - nl2br extension handles newlines
        md = markdown.Markdown(extensions=['extra', 'codehilite', 'nl2br'])
        converted_html = md.convert(regular_markdown)
        html += f'    {converted_html}\n'
    
    html += """
</body>
</html>"""
    
    return html


def create_chinese_translation_html(title, content, content_type):
    """Create HTML for Chinese text with translations"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            margin: 2em;
        }}
        h1 {{
            color: #8B4513;
            text-align: center;
            border-bottom: 2px solid #8B4513;
            padding-bottom: 0.5em;
        }}
        .chinese {{
            font-size: 1.2em;
            color: #2F4F4F;
            margin: 1em 0 0.3em 0;
            font-weight: bold;
        }}
        .english {{
            color: #000;
            margin: 0 0 1.5em 0;
            font-style: italic;
        }}
        .special-translation {{
            background-color: #F5F5DC;
            padding: 1em;
            border-left: 4px solid #8B4513;
            margin: 2em 0;
        }}
        .special-translation h3 {{
            color: #8B4513;
            margin-top: 0;
        }}
        .special-text {{
            line-height: 1.8;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""
    
    # Split content into main content and special translations
    lines = content.split('\n')
    main_content = []
    
    in_special = False
    special_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if re.search(r'\*\*.*Translation.*\*\*', line):
            in_special = True
            continue
        
        if in_special:
            special_content.append(line)
        else:
            main_content.append(line)
    
    # Process main content (Chinese-English pairs)
    i = 0
    content_added = False
    while i < len(main_content):
        line = main_content[i]
        
        # Check if this line contains Chinese characters
        if re.search(r'[\u4e00-\u9fff]', line):
            html += f'    <div class="chinese">{line}</div>\n'
            content_added = True
            # Next line should be the English translation
            if i + 1 < len(main_content):
                next_line = main_content[i + 1].strip()
                if next_line and not re.search(r'[\u4e00-\u9fff]', next_line):
                    html += f'    <div class="english">{next_line}</div>\n'
                    i += 1  # Skip the English line in next iteration
        i += 1
    
    # If no Chinese-English pairs found, add all lines as paragraphs
    if not content_added:
        for line in main_content:
            if line.strip():
                html += f'    <p>{line}</p>\n'
    
    # Add special translation section
    if special_content:
        translation_text = '\n'.join(special_content)
        # Use markdown for special translation content too
        md = markdown.Markdown(extensions=['extra', 'nl2br'])
        formatted_translation = md.convert(translation_text)
        translation_type = "Translation"
        if content_type['has_mitchell']:
            translation_type = "Stephen Mitchell Translation"
        
        html += f"""
    <div class="special-translation">
        <h3>{translation_type}:</h3>
        <div class="special-text">{formatted_translation}</div>
    </div>
"""
    
    html += """
</body>
</html>"""
    
    return html


def create_md(input_files: List[Union[str, Path]], prompt: str, output_file: str = None, api_key: str = None, test_run: bool = False) -> str:
    """
    Create enhanced markdown by processing multiple input files with Gemini AI.
    
    Args:
        input_files: List of file paths (supports .md, .pdf, .txt, .docx, .epub, .rtf, .odt)
        prompt: Instructions for how to process/enhance the content
        output_file: Output markdown file path (optional)
        api_key: Gemini API key (optional, can use GEMINI_API_KEY env var)
        test_run: If True, process only one chunk for testing output format
    
    Returns:
        Path to the created markdown file
    """
    # Load environment variables
    load_dotenv()
    
    # Setup Gemini API
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable or pass api_key parameter")
    
    genai.configure(api_key=api_key)
    
    # Configure model with generation settings optimized for document processing
    generation_config = genai.GenerationConfig(
        max_output_tokens=None,  # Let individual requests control this
        temperature=0.1,  # Low temperature for consistent, factual document processing
        top_p=0.8,       # Focused sampling for quality
        top_k=40,        # Default value for good balance
        candidate_count=1  # Single response for efficiency
    )
    
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)
    
    # Read and prepare input files
    combined_content = ""
    pdf_files = []
    
    for file_path in input_files:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"Warning: File {file_path} not found, skipping...")
            continue
            
        suffix = file_path.suffix.lower()
        
        if suffix == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                combined_content += f"\n\n# File: {file_path.name}\n\n{content}"
                print(f"Added markdown file: {file_path.name} ({len(content)} characters)")
                
        elif suffix == '.pdf':
            # First, try to extract text from PDF
            print(f"Attempting to extract text from PDF: {file_path.name}...")
            try:
                pdf_text = _convert_pdf_to_text(file_path)
                
                if pdf_text and len(pdf_text.strip()) > 100:
                    # PDF extraction successful - treat as text
                    combined_content += f"\n\n# File: {file_path.name}\n\n{pdf_text}"
                    print(f"✅ PDF text extraction successful: {len(pdf_text):,} characters")
                else:
                    # PDF extraction failed - fallback to direct upload
                    print(f"⚠️ PDF text extraction yielded insufficient content, using direct upload method")
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    if file_size_mb > 50:
                        print(f"Warning: PDF {file_path.name} is {file_size_mb:.1f}MB, exceeds 50MB limit")
                        continue
                    pdf_files.append(file_path)
                    print(f"Added PDF for direct upload: {file_path.name} ({file_size_mb:.1f}MB)")
                    
            except Exception as e:
                print(f"❌ PDF text extraction error: {e}")
                print(f"🔄 Falling back to direct PDF upload method")
                # Fallback to direct upload
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > 50:
                    print(f"Warning: PDF {file_path.name} is {file_size_mb:.1f}MB, exceeds 50MB limit")
                    continue
                pdf_files.append(file_path)
                print(f"Added PDF for direct upload: {file_path.name} ({file_size_mb:.1f}MB)")
            
        elif suffix in ['.txt', '.docx', '.epub', '.rtf', '.odt']:
            # Convert document to text
            try:
                print(f"Converting {suffix.upper()} file: {file_path.name}...")
                content = _convert_document_to_text(file_path)
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
    
    # Calculate rough token count (3 chars ≈ 1 token, more conservative)
    estimated_tokens = len(combined_content) // 3
    print(f"Combined content: {len(combined_content):,} characters")
    print(f"Estimated tokens: {estimated_tokens:,}")
    
    # Gemini 2.5 Flash has 1,048,576 input + 65,535 output tokens
    # Since output ~= input length, use much smaller batches to avoid MAX_TOKENS
    max_tokens_per_batch = 60000
    print(f"Max tokens per batch: {max_tokens_per_batch:,}")
    
    # Process content with unified approach
    result = _process_content_unified(model, combined_content, pdf_files, prompt, max_tokens_per_batch, test_run)
    
    # Generate output filename if not provided
    if not output_file:
        base_name = Path(input_files[0]).stem if input_files else "enhanced"
        output_file = f"{base_name}_enhanced.md"
    
    # Write result to file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(f"Enhanced markdown created: {output_path}")
    return str(output_path)


def create_enhanced_ebook(input_files: List[Union[str, Path]], prompt: str, output_file: str = None, 
                         title: str = None, author: str = None, api_key: str = None, test_run: bool = False) -> str:
    """
    Create an enhanced ebook by processing multiple input files with AI and converting to EPUB.
    
    This combines create_md() and create_ebook() into a single workflow:
    1. Process input files with Gemini AI according to the prompt
    2. Convert the enhanced content to EPUB format
    
    Args:
        input_files: List of file paths (supports .md, .pdf, .txt, .docx, .epub, .rtf, .odt)
        prompt: Instructions for how to process/enhance the content
        output_file: Output EPUB file path (optional, will generate if not provided)
        title: Book title (optional, derived from first file if not provided)
        author: Book author (optional, defaults to "Unknown Author")
        api_key: Gemini API key (optional, can use GEMINI_API_KEY env var)
        test_run: If True, process only one chunk for testing output format
    
    Returns:
        Path to the created EPUB file
    """
    print("=== Creating Enhanced Ebook ===")
    print(f"Step 1: Processing {len(input_files)} file(s) with AI...")
    
    # Generate intermediate markdown filename
    base_name = Path(input_files[0]).stem if input_files else "enhanced"
    temp_md_file = f"{base_name}_ai_enhanced.md"
    
    try:
        # Step 1: Use create_md to process files with AI
        enhanced_md_path = create_md(
            input_files=input_files,
            prompt=prompt,
            output_file=temp_md_file,
            api_key=api_key,
            test_run=test_run
        )
        
        print(f"\nStep 2: Converting enhanced content to EPUB...")
        
        # Generate EPUB filename if not provided
        if not output_file:
            output_file = f"{base_name}_enhanced.epub"
        
        # Generate title and author if not provided
        if not title:
            title = base_name.replace('_', ' ').replace('-', ' ').title() + " (AI Enhanced)"
        
        if not author:
            author = "AI Enhanced Edition"
        
        # Step 2: Convert the enhanced markdown to EPUB
        success = create_ebook(
            input_file=enhanced_md_path,
            output_file=output_file,
            title=title,
            author=author
        )
        
        if success:
            print(f"\n✅ Enhanced ebook created successfully: {output_file}")
            
            # Clean up intermediate file
            try:
                Path(enhanced_md_path).unlink()
                print(f"Cleaned up intermediate file: {enhanced_md_path}")
            except:
                pass
                
            return output_file
        else:
            raise ValueError("Failed to create EPUB from enhanced content")
            
    except Exception as e:
        print(f"❌ Error creating enhanced ebook: {e}")
        
        # Clean up intermediate file if it exists
        try:
            if 'enhanced_md_path' in locals():
                Path(enhanced_md_path).unlink()
        except:
            pass
            
        raise


def _process_content_unified(model, combined_content: str, pdf_files: List[Path], prompt: str, max_tokens_per_batch: int, test_run: bool) -> str:
    """Single unified function to process any content type with simple batching."""
    if test_run:
        max_tokens_per_batch = 50000  # Smaller for test runs
        print("🧪 TEST RUN MODE: Processing with smaller batches")
    
    results = []
    
    # Process text content if present
    if combined_content.strip():
        print("Processing text content...")
        text_result = _process_text_batches(model, combined_content, prompt, max_tokens_per_batch)
        if text_result:
            results.append(text_result)
    
    # Process PDFs if present  
    if pdf_files:
        print("Processing PDF files...")
        pdf_result = _process_pdf_files(model, pdf_files, prompt, test_run)
        if pdf_result:
            results.append(pdf_result)
    
    return '\n\n'.join(results) if results else ""


def _process_text_batches(model, content: str, prompt: str, max_tokens_per_batch: int) -> str:
    """Process text content in batches."""
    # Split into batches
    batches = _split_content_by_sections(content)
    final_batches = []
    current_batch = []
    current_length = 0
    max_chars = max_tokens_per_batch * 3
    
    for batch in batches:
        if current_length + len(batch) > max_chars and current_batch:
            final_batches.append('\n\n'.join(current_batch))
            current_batch = [batch]
            current_length = len(batch)
        else:
            current_batch.append(batch)
            current_length += len(batch)
    
    if current_batch:
        final_batches.append('\n\n'.join(current_batch))
    
    print(f"Processing {len(final_batches)} text batches...")
    results = []
    
    for i, batch_content in enumerate(final_batches, 1):
        print(f"Processing text batch {i}/{len(final_batches)}")
        
        batch_prompt = f"""
{prompt}

Batch {i} of {len(final_batches)}:
{batch_content}
"""
        
        try:
            response = model.generate_content(batch_prompt)
            
            if response.candidates and response.candidates[0].finish_reason == 1:
                # Success
                results.append(response.text)
            elif response.candidates and response.candidates[0].finish_reason == 2:
                # Token limit - keep splitting until success or too small
                print(f"Batch {i} hit token limit, splitting recursively...")
                sub_results = _process_batch_recursive(model, batch_content, prompt, max_tokens_per_batch // 2)
                results.extend(sub_results)
            # Other errors - skip batch
                
        except Exception as e:
            print(f"Text batch {i} error: {e}")
            continue
    
    return '\n\n'.join(results)


def _process_batch_recursive(model, content: str, prompt: str, max_tokens: int, depth: int = 0) -> List[str]:
    """Recursively split and process content until it succeeds or becomes too small."""
    indent = "  " * depth
    print(f"{indent}🔄 Recursive split (depth {depth}): {len(content)} chars, target {max_tokens} tokens")
    
    # Minimum viable content size (about 100 tokens)
    min_content_size = 300
    
    if len(content) < min_content_size:
        print(f"{indent}❌ Content too small ({len(content)} chars), discarding")
        return []
    
    # Split content
    smaller_batches = _split_large_section(content, max_tokens)
    print(f"{indent}📦 Split into {len(smaller_batches)} sub-batches")
    
    if not smaller_batches:
        print(f"{indent}❌ Splitting failed - no sub-batches created")
        return []
    
    results = []
    
    for i, sub_batch in enumerate(smaller_batches, 1):
        print(f"{indent}🔄 Processing sub-batch {i}/{len(smaller_batches)} ({len(sub_batch)} chars)")
        
        try:
            sub_response = model.generate_content(f"{prompt}\n\n{sub_batch}")
            
            if sub_response.candidates and sub_response.candidates[0].finish_reason == 1:
                # Success!
                print(f"{indent}✅ Sub-batch {i} succeeded ({len(sub_response.text)} chars output)")
                results.append(sub_response.text)
            elif sub_response.candidates and sub_response.candidates[0].finish_reason == 2:
                # Still too big - split further recursively
                print(f"{indent}🔄 Sub-batch {i} still too big, splitting deeper...")
                deeper_results = _process_batch_recursive(model, sub_batch, prompt, max_tokens // 2, depth + 1)
                results.extend(deeper_results)
                print(f"{indent}📝 Got {len(deeper_results)} results from deeper split")
            else:
                finish_reason = sub_response.candidates[0].finish_reason if sub_response.candidates else "no candidates"
                print(f"{indent}❌ Sub-batch {i} failed with finish_reason: {finish_reason}")
            
        except Exception as e:
            print(f"{indent}❌ Sub-batch {i} error: {e}")
            continue
    
    print(f"{indent}📋 Recursive split complete: {len(results)} successful results")
    return results


def _process_pdf_files(model, pdf_files: List[Path], prompt: str, test_run: bool) -> str:
    """Process PDF files with simple chunking."""
    results = []
    
    for pdf_file in pdf_files:
        print(f"Processing PDF: {pdf_file.name}")
        
        # Check file size
        file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        if file_size_mb > 50:
            print(f"PDF {pdf_file.name} exceeds 50MB, skipping...")
            continue
        
        pdf_result = _process_single_pdf_simple(model, pdf_file, prompt, test_run)
        if pdf_result:
            results.append(pdf_result)
    
    return '\n\n'.join(results)


def _process_single_pdf_simple(model, pdf_file: Path, prompt: str, test_run: bool) -> str:
    """Process a single PDF with simple approach."""
    max_chunks = 3 if test_run else 10
    results = []
    
    for chunk_num in range(1, max_chunks + 1):
        chunk_prompt = f"""
{prompt}

PDF chunk {chunk_num} of {pdf_file.name}:
"""
        
        try:
            response = model.generate_content([chunk_prompt, pdf_file])
            
            if response.candidates and response.candidates[0].finish_reason == 1:
                # Success
                results.append(response.text)
                if test_run or "end of document" in response.text.lower():
                    break
            elif response.candidates and response.candidates[0].finish_reason == 2:
                # Token limit - try to get partial response and continue
                try:
                    results.append(response.text)
                except:
                    pass
                continue
            else:
                # Other error - stop processing this PDF
                break
                
        except Exception as e:
            print(f"PDF chunk {chunk_num} error: {e}")
            continue
    
    return '\n\n'.join(results)














def get_example_prompts() -> dict:
    """
    Get a collection of proven prompt examples for different use cases.
    Based on real-world usage patterns and successful conversions.
    
    Returns:
        Dictionary of categorized prompt examples
    """
    return {
        "chinese_text_processing": {
            "traditional_to_simplified": """Convert all traditional Chinese characters to simplified Chinese characters.

Maintain the exact same format and structure. Keep:
- All chapter/section headers
- All translations and commentary 
- All punctuation and spacing
- All non-Chinese text unchanged

Only change traditional Chinese characters to their simplified equivalents.
Process the entire document systematically.""",

            "add_pinyin_and_simplify": """Process this Chinese text by:

1. Convert all traditional Chinese characters to simplified Chinese
2. For any line containing Chinese characters, add pinyin on the next line in parentheses
3. Keep all existing translations and structure intact
4. Maintain original formatting and chapter divisions

Example format:
无门关
(wú mén guān)

Process the entire document this way.""",

            "hsk_character_analysis": """For any line with Chinese characters that contains characters NOT in HSK1-6:

1. Keep the original line unchanged
2. On the next line, list each non-HSK character with:
   - Character: pronunciation (meaning) [HSK alternative if available]

Example:
Original: 道可道非常道
Non-HSK analysis: 道: dào (way/path) [HSK6: 路 lù]

Keep all existing content and add this analysis throughout."""
        },

        "text_enhancement": {
            "add_philosophical_commentary": """Add thoughtful philosophical commentary to each chapter/section.

For each major section:
1. Keep the original text intact
2. Add a "Commentary" subsection with:
   - Key philosophical concepts explained
   - Connections to other philosophical traditions
   - Practical applications
   - Modern relevance

Maintain scholarly tone and cite relevant sources where appropriate.""",

            "cross_reference_texts": """Cross-reference and synthesize multiple texts:

1. Identify common themes and concepts across all provided documents
2. Create connections between similar ideas
3. Add cross-references in the format: (see also: [Document Name, Section])
4. Highlight contradictions or different perspectives
5. Maintain original structure while weaving in connections

Output as a unified, coherent text with clear source attributions.""",

            "study_guide_creation": """Transform this content into a comprehensive study guide:

1. Extract key concepts and create definitions
2. Add "Key Points" summaries for each section
3. Create study questions for each chapter
4. Add "Practice Applications" sections
5. Include a glossary of important terms
6. Maintain original content as primary material

Format as a structured study resource."""
        },

        "document_conversion": {
            "academic_paper_format": """Convert to academic paper format:

1. Add proper abstract (150-200 words)
2. Structure with: Introduction, Main Body, Analysis, Conclusion
3. Add proper citations and references
4. Include footnotes for key concepts
5. Maintain scholarly tone throughout
6. Add section numbering (1.1, 1.2, etc.)

Keep original content as primary source material.""",

            "book_manuscript": """Format as a book manuscript:

1. Create compelling chapter titles
2. Add chapter introductions and conclusions
3. Ensure smooth transitions between sections
4. Add a table of contents
5. Include an introduction explaining the work's significance
6. Maintain readability for general audience
7. Add footnotes for cultural/historical context

Structure for publication-ready format.""",

            "markdown_optimization": """Convert to well-structured markdown:

1. Use proper heading hierarchy (# ## ###)
2. Format lists, quotes, and emphasis correctly
3. Add table of contents with links
4. Use code blocks for special text
5. Add horizontal rules for section breaks
6. Optimize for GitHub/documentation display
7. Include metadata at the top

Ensure perfect markdown syntax throughout."""
        },

        "language_learning": {
            "vocabulary_expansion": """Create a language learning resource:

1. Identify and highlight key vocabulary
2. Add definitions and usage examples
3. Group vocabulary by difficulty level
4. Add pronunciation guides
5. Create practice exercises
6. Include cultural context notes
7. Add progress tracking sections

Format as a comprehensive learning tool.""",

            "bilingual_parallel": """Create bilingual parallel text:

1. Present original and target language side by side
2. Align content paragraph by paragraph
3. Add vocabulary notes between sections
4. Include pronunciation guides
5. Add cultural explanation boxes
6. Maintain clear visual separation
7. Include comprehension questions

Optimize for language learning efficiency."""
        },

        "content_analysis": {
            "thematic_analysis": """Perform deep thematic analysis:

1. Identify major themes and motifs
2. Trace theme development throughout the text
3. Create theme summaries and explanations
4. Add analytical commentary
5. Connect themes to broader contexts
6. Include supporting quotes and examples
7. Create thematic index

Present as scholarly analysis with original text.""",

            "comparative_study": """Create comparative analysis across documents:

1. Identify similar concepts in all texts
2. Compare different approaches/perspectives
3. Analyze contradictions and agreements
4. Create comparison charts/tables
5. Synthesize into unified understanding
6. Maintain source attribution
7. Add analytical conclusions

Structure as comprehensive comparative study."""
        },

        "simple_requests": {
            "clean_formatting": """Clean up and improve formatting:

1. Fix inconsistent spacing and punctuation
2. Standardize heading styles
3. Correct any obvious errors
4. Improve paragraph structure
5. Ensure consistent style throughout
6. Maintain all original content

Focus on readability improvements only.""",

            "summarize_sections": """Add brief summaries:

1. Keep all original content unchanged
2. Add 2-3 sentence summary at the end of each major section
3. Highlight key takeaways
4. Use clear, accessible language
5. Focus on main points only

Enhance understanding without changing original text."""
        }
    }


def print_example_prompts(category: str = None):
    """
    Print example prompts for reference.
    
    Args:
        category: Specific category to show, or None for all categories
    """
    examples = get_example_prompts()
    
    if category:
        if category in examples:
            print(f"\n=== {category.upper()} PROMPTS ===\n")
            for name, prompt in examples[category].items():
                print(f"📝 {name.replace('_', ' ').title()}:")
                print(f"{prompt}\n")
                print("-" * 60 + "\n")
        else:
            print(f"Category '{category}' not found. Available categories:")
            for cat in examples.keys():
                print(f"  - {cat}")
    else:
        print("=== EXAMPLE PROMPTS FOR create_md() AND create_enhanced_ebook() ===\n")
        for cat_name, prompts in examples.items():
            print(f"📂 {cat_name.upper().replace('_', ' ')}")
            for prompt_name in prompts.keys():
                print(f"   • {prompt_name.replace('_', ' ').title()}")
            print()
        
        print("Usage:")
        print("  print_example_prompts('chinese_text_processing')")
        print("  print_example_prompts('text_enhancement')")
        print("  etc.")








def _split_content_by_sections(content: str) -> List[str]:
    """Split content by markdown headers for better batching"""
    sections = []
    current_section = []
    
    lines = content.split('\n')
    for line in lines:
        # Check for major headers (# or ##)
        if re.match(r'^#{1,2}\s+', line) and current_section:
            sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    # Add the last section
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections


def _split_large_section(section: str, max_tokens: int) -> List[str]:
    """Split content aggressively to ensure roughly equal chunks."""
    max_chars = max_tokens * 3  # Conservative token-to-char conversion
    
    # Always aim for at least 2 chunks if content is substantial
    if len(section) <= max_chars:
        # If content is small enough for max_tokens but we're in recursive mode,
        # still split it to create smaller batches
        if len(section) > 1000:  # Only split if it's substantial
            return _force_split(section, 2)  # Force into 2 chunks
        return [section]
    
    # Calculate number of chunks needed
    num_chunks = max(2, (len(section) // max_chars) + 1)
    return _force_split(section, num_chunks)


def _force_split(content: str, num_chunks: int) -> List[str]:
    """Force content into exactly num_chunks pieces, trying to respect boundaries."""
    if num_chunks <= 1:
        return [content]
    
    target_size = len(content) // num_chunks
    chunks = []
    
    # Try to split by paragraphs first
    paragraphs = content.split('\n\n')
    if len(paragraphs) >= num_chunks:
        # Distribute paragraphs evenly
        paras_per_chunk = len(paragraphs) // num_chunks
        for i in range(num_chunks):
            start_idx = i * paras_per_chunk
            if i == num_chunks - 1:  # Last chunk gets remaining paragraphs
                chunk_paras = paragraphs[start_idx:]
            else:
                end_idx = start_idx + paras_per_chunk
                chunk_paras = paragraphs[start_idx:end_idx]
            chunks.append('\n\n'.join(chunk_paras))
        return chunks
    
    # If not enough paragraphs, try sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)
    if len(sentences) >= num_chunks:
        # Distribute sentences evenly
        sentences_per_chunk = len(sentences) // num_chunks
        for i in range(num_chunks):
            start_idx = i * sentences_per_chunk
            if i == num_chunks - 1:  # Last chunk gets remaining sentences
                chunk_sentences = sentences[start_idx:]
            else:
                end_idx = start_idx + sentences_per_chunk
                chunk_sentences = sentences[start_idx:end_idx]
            chunks.append(' '.join(chunk_sentences))
        return chunks
    
    # Last resort: split by character count at word boundaries
    chars_per_chunk = len(content) // num_chunks
    current_pos = 0
    
    for i in range(num_chunks):
        if i == num_chunks - 1:  # Last chunk
            chunks.append(content[current_pos:])
            break
        
        # Find target position
        target_pos = current_pos + chars_per_chunk
        
        # Look for word boundary near target position
        search_start = max(current_pos, target_pos - 100)
        search_end = min(len(content), target_pos + 100)
        
        # Find nearest word boundary
        best_pos = target_pos
        for pos in range(search_start, search_end):
            if content[pos:pos+1].isspace():
                if abs(pos - target_pos) < abs(best_pos - target_pos):
                    best_pos = pos
        
        chunks.append(content[current_pos:best_pos])
        current_pos = best_pos + 1  # Skip the space
    
    # Remove empty chunks
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def create_ebook(input_file, output_file=None, title=None, author=None):
    """Create the EPUB ebook from markdown file"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        return False
    
    # Parse the markdown file
    chapters = parse_markdown_file(input_file)
    print(f"Found {len(chapters)} chapters")
    
    if not chapters:
        print("No chapters found in the markdown file")
        return False

    # Generate output filename if not provided
    if not output_file:
        output_file = input_path.stem + '.epub'
    
    # Generate title and author if not provided
    if not title:
        title = input_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    if not author:
        author = "Unknown Author"

    book_config = {
        'title': title,
        'author': author,
        'identifier': input_path.stem.lower().replace(' ', '-')
    }

    # Debug: Print first few chapter titles
    for i, chapter in enumerate(chapters[:3]):
        print(f"Chapter {i+1}: {chapter['title']}")

    # Create book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(book_config['identifier'])
    book.set_title(book_config['title'])
    book.set_language('en')
    book.add_author(book_config['author'])

    # Add cover page
    cover_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <style>
        body {{
            font-family: Georgia, serif;
            text-align: center;
            margin: 4em 2em;
        }}
        h1 {{
            font-size: 2.5em;
            color: #2F4F4F;
            margin-bottom: 0.5em;
        }}
        .author {{
            font-size: 1.3em;
            margin: 2em 0;
        }}
        .description {{
            font-style: italic;
            margin: 3em 0;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="author">by {author}</div>
    <div class="description">
        Generated from markdown using EbookLib
    </div>
</body>
</html>"""

    cover = epub.EpubHtml(title='Cover', file_name='cover.xhtml', lang='en')
    cover.content = cover_html
    book.add_item(cover)

    # Add table of contents page
    toc_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Table of Contents</title>
    <meta charset="utf-8"/>
    <style>
        body {{
            font-family: Georgia, serif;
            margin: 2em;
            line-height: 1.8;
        }}
        h1 {{
            color: #2F4F4F;
            text-align: center;
            border-bottom: 2px solid #2F4F4F;
            padding-bottom: 0.5em;
        }}
        .toc-entry {{
            margin: 0.5em 0;
        }}
        a {{
            color: #2F4F4F;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Table of Contents</h1>
"""

    for i, chapter in enumerate(chapters, 1):
        toc_html += f'    <div class="toc-entry"><a href="chapter_{i:02d}.xhtml">{chapter["title"]}</a></div>\n'

    toc_html += """
</body>
</html>"""

    toc_page = epub.EpubHtml(title='Table of Contents', file_name='toc.xhtml', lang='en')
    toc_page.content = toc_html
    book.add_item(toc_page)

    # Add chapters
    chapter_items = []
    for i, chapter in enumerate(chapters, 1):
        try:
            # Create chapter HTML
            chapter_html = create_chapter_html(chapter, book_config)

            # Validate HTML content
            if not chapter_html or len(chapter_html.strip()) < 100:
                print(f"Warning: Chapter {i} ({chapter['title']}) has very little content")
                continue

            # Create EPUB chapter
            chapter_item = epub.EpubHtml(
                title=chapter['title'],
                file_name=f'chapter_{i:02d}.xhtml',
                lang='en'
            )
            chapter_item.content = chapter_html
            book.add_item(chapter_item)
            chapter_items.append(chapter_item)
            print(f"Added chapter {i}: {chapter['title']}")

        except Exception as e:
            print(f"Error processing chapter {i} ({chapter['title']}): {e}")
            continue

    if not chapter_items:
        print("No valid chapters were created")
        return False

    # Create table of contents structure
    toc_links = [
        epub.Link("cover.xhtml", "Cover", "cover"),
        epub.Link("toc.xhtml", "Table of Contents", "toc")
    ]
    for i, item in enumerate(chapter_items, 1):
        toc_links.append(epub.Link(item.file_name, chapters[i-1]['title'], f"chapter_{i}"))

    book.toc = toc_links

    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Create spine
    book.spine = ['cover', 'toc'] + chapter_items

    # Write the book
    try:
        epub.write_epub(output_file, book, {})
        print(f"EPUB book created successfully: {output_file}")
        return True
    except Exception as e:
        print(f"Error creating EPUB: {e}")
        return False


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description='Convert markdown files to EPUB ebooks')
    parser.add_argument('input_file', help='Input markdown file path')
    parser.add_argument('-o', '--output', help='Output EPUB file path (optional)')
    parser.add_argument('-t', '--title', help='Book title (optional, derived from filename if not provided)')
    parser.add_argument('-a', '--author', help='Book author (optional, defaults to "Unknown Author")')
    
    args = parser.parse_args()
    
    success = create_ebook(
        input_file=args.input_file,
        output_file=args.output,
        title=args.title,
        author=args.author
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()