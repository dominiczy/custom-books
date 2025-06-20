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


def create_md(input_files: List[Union[str, Path]], prompt: str, output_file: str = None, api_key: str = None) -> str:
    """
    Create enhanced markdown by processing multiple input files with Gemini AI.
    
    Args:
        input_files: List of file paths (currently supports .md files)
        prompt: Instructions for how to process/enhance the content
        output_file: Output markdown file path (optional)
        api_key: Gemini API key (optional, can use GEMINI_API_KEY env var)
    
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
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Read and combine input files
    combined_content = ""
    for file_path in input_files:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"Warning: File {file_path} not found, skipping...")
            continue
            
        if file_path.suffix.lower() == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                combined_content += f"\n\n# File: {file_path.name}\n\n{content}"
        else:
            print(f"Warning: File type {file_path.suffix} not yet supported for {file_path.name}")
    
    if not combined_content.strip():
        raise ValueError("No valid content found in input files")
    
    # Calculate rough token count (3 chars ≈ 1 token, more conservative)
    estimated_tokens = len(combined_content) // 3
    print(f"Combined content: {len(combined_content):,} characters")
    print(f"Estimated tokens: {estimated_tokens:,}")
    
    # Gemini 2.5 Flash has 1,048,576 input + 65,535 output tokens
    # Since output ~= input length, use much smaller batches to avoid MAX_TOKENS
    max_tokens_per_batch = 400000
    print(f"Max tokens per batch: {max_tokens_per_batch:,}")
    
    if estimated_tokens <= max_tokens_per_batch:
        print("Processing in single batch...")
        result = _process_single_batch(model, combined_content, prompt)
    else:
        print("Processing in multiple batches...")
        result = _process_multiple_batches(model, combined_content, prompt, max_tokens_per_batch)
    
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


def _process_single_batch(model, content: str, prompt: str) -> str:
    """Process content in a single Gemini request"""
    full_prompt = f"""
{prompt}

Content to process:
{content}
"""
    
    print(f"Making single API call to Gemini 2.5 Flash...")
    print(f"Prompt length: {len(full_prompt):,} characters")
    
    try:
        response = model.generate_content(full_prompt)
        
        # Check finish reason before accessing text
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            print(f"API response finish_reason: {finish_reason}")
            
            if finish_reason == 1:  # STOP - normal completion
                print(f"API call successful! Response length: {len(response.text):,} characters")
                return response.text
            elif finish_reason == 2:  # MAX_TOKENS - output truncated
                print(f"WARNING: Response truncated due to max tokens limit!")
                print(f"Content is too large for single batch - need to split further")
                raise ValueError("Response truncated due to max tokens limit. Content needs smaller batches.")
            elif finish_reason == 3:  # SAFETY
                print(f"ERROR: Response blocked due to safety filters")
                raise ValueError("Response blocked by safety filters")
            else:
                print(f"ERROR: Unexpected finish_reason: {finish_reason}")
                raise ValueError(f"Unexpected finish_reason: {finish_reason}")
        else:
            print("ERROR: No candidates in response")
            raise ValueError("No candidates in response")
            
    except Exception as e:
        print(f"Error processing with Gemini: {e}")
        raise


def _process_multiple_batches(model, content: str, prompt: str, max_tokens_per_batch: int) -> str:
    """Process large content in multiple batches"""
    # Split content by chapters/sections for better batching
    sections = _split_content_by_sections(content)
    
    # Calculate tokens per section and group into batches
    batches = []
    current_batch = []
    current_batch_tokens = 0
    
    for section in sections:
        section_tokens = len(section) // 3  # More conservative estimate
        
        # If single section is too large, split it further
        if section_tokens > max_tokens_per_batch:
            # Split by paragraphs/lines
            subsections = _split_large_section(section, max_tokens_per_batch)
            for subsection in subsections:
                subsection_tokens = len(subsection) // 3
                if current_batch_tokens + subsection_tokens > max_tokens_per_batch and current_batch:
                    batches.append('\n\n'.join(current_batch))
                    current_batch = [subsection]
                    current_batch_tokens = subsection_tokens
                else:
                    current_batch.append(subsection)
                    current_batch_tokens += subsection_tokens
        else:
            if current_batch_tokens + section_tokens > max_tokens_per_batch and current_batch:
                batches.append('\n\n'.join(current_batch))
                current_batch = [section]
                current_batch_tokens = section_tokens
            else:
                current_batch.append(section)
                current_batch_tokens += section_tokens
    
    # Add remaining content to batches
    if current_batch:
        batches.append('\n\n'.join(current_batch))
    
    print(f"Processing {len(batches)} batches...")
    
    # Process each batch
    processed_batches = []
    for i, batch_content in enumerate(batches, 1):
        print(f"\n--- Processing batch {i}/{len(batches)} ---")
        print(f"Batch content length: {len(batch_content):,} characters")
        print(f"Estimated batch tokens: {len(batch_content) // 3:,}")
        
        batch_prompt = f"""
{prompt}

This is batch {i} of {len(batches)}. Process this content according to the instructions above.
Maintain consistency with previous batches.

Content to process:
{batch_content}
"""
        
        print(f"Making API call for batch {i}...")
        print(f"Full prompt length: {len(batch_prompt):,} characters")
        
        try:
            response = model.generate_content(batch_prompt)
            
            # Check finish reason before accessing text
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason
                print(f"Batch {i} finish_reason: {finish_reason}")
                
                if finish_reason == 1:  # STOP - normal completion
                    print(f"Batch {i} API call successful! Response length: {len(response.text):,} characters")
                    processed_batches.append(response.text)
                elif finish_reason == 2:  # MAX_TOKENS - output truncated
                    print(f"WARNING: Batch {i} response truncated due to max tokens!")
                    print(f"Using partial response and continuing...")
                    # Try to get partial response or use original content
                    try:
                        partial_text = response.text if hasattr(response, 'text') else batch_content
                        processed_batches.append(f"[PARTIAL RESPONSE - TRUNCATED]\n{partial_text}")
                    except:
                        processed_batches.append(f"[ERROR - MAX_TOKENS]\n{batch_content}")
                elif finish_reason == 3:  # SAFETY
                    print(f"ERROR: Batch {i} blocked by safety filters")
                    processed_batches.append(f"[BLOCKED BY SAFETY FILTERS]\n{batch_content}")
                else:
                    print(f"ERROR: Batch {i} unexpected finish_reason: {finish_reason}")
                    processed_batches.append(f"[ERROR - FINISH_REASON {finish_reason}]\n{batch_content}")
            else:
                print(f"ERROR: Batch {i} - No candidates in response")
                processed_batches.append(f"[ERROR - NO CANDIDATES]\n{batch_content}")
                
        except Exception as e:
            print(f"ERROR processing batch {i}: {e}")
            # Continue with other batches
            processed_batches.append(f"[Error processing batch {i}: {e}]\n\n{batch_content}")
            print(f"Continuing with remaining batches...")
    
    # Combine all processed batches
    final_result = '\n\n'.join(processed_batches)
    print(f"\nAll batches processed! Final result length: {len(final_result):,} characters")
    return final_result


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
    """Split a large section into smaller chunks"""
    # More conservative splitting since output ~= input length
    max_chars = max_tokens * 3  # More conservative conversion
    
    if len(section) <= max_chars:
        return [section]
    
    # Split by paragraphs first
    paragraphs = section.split('\n\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para_length = len(para)
        
        if current_length + para_length > max_chars and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_length
        else:
            current_chunk.append(para)
            current_length += para_length + 2  # +2 for \n\n
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    # If paragraphs are still too large, split by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            current_sentence_chunk = []
            current_sentence_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                if current_sentence_length + sentence_length > max_chars and current_sentence_chunk:
                    final_chunks.append(' '.join(current_sentence_chunk))
                    current_sentence_chunk = [sentence]
                    current_sentence_length = sentence_length
                else:
                    current_sentence_chunk.append(sentence)
                    current_sentence_length += sentence_length + 1  # +1 for space
            
            if current_sentence_chunk:
                final_chunks.append(' '.join(current_sentence_chunk))
        else:
            final_chunks.append(chunk)
    
    return final_chunks


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