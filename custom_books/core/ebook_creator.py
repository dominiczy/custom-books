"""
EPUB ebook creation functionality.
"""

import os
from pathlib import Path

import markdown
from ebooklib import epub


def create_ebook(markdown_content: str, title: str = "Custom Book", author: str = "AI Generated", 
                 output_filename: str = None) -> str:
    """
    Create an EPUB ebook from markdown content.
    
    Args:
        markdown_content: The markdown text to convert
        title: Book title
        author: Book author
        output_filename: Output filename (defaults to sanitized title)
        
    Returns:
        Path to the created EPUB file
    """
    # Create output filename if not provided
    if not output_filename:
        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        output_filename = f"{safe_title}.epub"
    
    # Ensure .epub extension
    if not output_filename.endswith('.epub'):
        output_filename += '.epub'
    
    print(f"Creating EPUB: {output_filename}")
    
    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
    
    # Create EPUB book
    book = epub.EpubBook()
    
    # Set metadata
    book.set_identifier('custom_book_' + str(hash(title + author)))
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)
    
    # Create chapter
    chapter = epub.EpubHtml(title='Content', file_name='content.xhtml', lang='en')
    chapter.content = f'''
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>{title}</title>
        <style>
            body {{ 
                font-family: Georgia, serif; 
                line-height: 1.6; 
                margin: 2em;
                max-width: 800px;
            }}
            h1, h2, h3 {{ 
                color: #333; 
                margin-top: 2em;
            }}
            h1 {{ 
                border-bottom: 2px solid #333; 
                padding-bottom: 0.5em;
            }}
            code {{ 
                background-color: #f5f5f5; 
                padding: 2px 4px; 
                border-radius: 3px;
                font-family: Monaco, 'Courier New', monospace;
            }}
            pre {{ 
                background-color: #f5f5f5; 
                padding: 1em; 
                border-radius: 5px; 
                overflow-x: auto;
                font-family: Monaco, 'Courier New', monospace;
            }}
            blockquote {{ 
                border-left: 4px solid #ddd; 
                margin: 1em 0; 
                padding-left: 1em; 
                color: #666;
            }}
            table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin: 1em 0;
            }}
            th, td {{ 
                border: 1px solid #ddd; 
                padding: 8px; 
                text-align: left;
            }}
            th {{ 
                background-color: #f2f2f2; 
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    '''
    
    # Add chapter to book
    book.add_item(chapter)
    
    # Create table of contents
    book.toc = (epub.Link("content.xhtml", "Content", "content"),)
    
    # Add navigation
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Create spine
    book.spine = ['nav', chapter]
    
    # Write EPUB file
    epub.write_epub(output_filename, book)
    
    # Get absolute path for return
    abs_path = os.path.abspath(output_filename)
    
    print(f"✅ EPUB created successfully: {abs_path}")
    print(f"📖 Title: {title}")
    print(f"✍️ Author: {author}")
    
    # Show file size
    file_size = Path(abs_path).stat().st_size
    print(f"📁 Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    return abs_path