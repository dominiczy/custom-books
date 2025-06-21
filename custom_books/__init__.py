"""
Custom Books - AI-Enhanced Document Processing and EPUB Creation

Main public API for the custom books library.
"""

from .core.api import create_md, create_enhanced_ebook
from .utils.examples import get_example_prompts, print_example_prompts
from .core.ebook_creator import create_ebook

__version__ = "1.0.0"

__all__ = [
    "create_md",
    "create_enhanced_ebook", 
    "create_ebook",
    "get_example_prompts",
    "print_example_prompts"
]