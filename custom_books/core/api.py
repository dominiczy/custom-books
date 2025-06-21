"""
Main API functions for custom books library.
"""

import os
from pathlib import Path
from typing import List, Union
from dotenv import load_dotenv

from ..converters.file_handler import FileHandler
from ..processors.unified_processor import UnifiedProcessor
from .ebook_creator import create_ebook


def create_md(input_files: List[Union[str, Path]], prompt: str, output_file: str = None, 
              api_key: str = None, test_run: bool = False) -> str:
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
    
    # Setup API key
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable or pass api_key parameter")
    
    # Process input files
    print(f"Processing {len(input_files)} input file(s)...")
    file_handler = FileHandler()
    combined_content, pdf_files = file_handler.process_files(input_files)
    
    # Calculate token estimates for text content
    estimated_tokens = len(combined_content) // 3
    print(f"Combined content: {len(combined_content):,} characters")
    print(f"Estimated tokens: {estimated_tokens:,}")
    
    # Process with Gemini
    processor = UnifiedProcessor(api_key)
    
    if test_run:
        print("🧪 TEST RUN MODE: Processing only one chunk for format validation")
        result = processor.process_test_run(combined_content, pdf_files, prompt)
    else:
        result = processor.process_content(combined_content, pdf_files, prompt)
    
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
        
        # Read the enhanced markdown content
        with open(enhanced_md_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Step 2: Convert the enhanced markdown to EPUB
        epub_path = create_ebook(
            markdown_content=markdown_content,
            title=title,
            author=author,
            output_filename=output_file
        )
        
        print(f"\n✅ Enhanced ebook created successfully: {epub_path}")
        
        # Clean up intermediate file
        try:
            Path(enhanced_md_path).unlink()
            print(f"Cleaned up intermediate file: {enhanced_md_path}")
        except:
            pass
            
        return epub_path
            
    except Exception as e:
        print(f"❌ Error creating enhanced ebook: {e}")
        
        # Clean up intermediate file if it exists
        try:
            if 'enhanced_md_path' in locals():
                Path(enhanced_md_path).unlink()
        except:
            pass
            
        raise