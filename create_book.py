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