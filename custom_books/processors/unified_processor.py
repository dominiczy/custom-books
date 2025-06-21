"""
Unified Gemini processor that handles all content types with simple batching.
"""

import re
from pathlib import Path
from typing import List

import google.generativeai as genai


class UnifiedProcessor:
    """Single processor that handles all content with simple batching from the start."""
    
    def __init__(self, api_key: str):
        """Initialize the unified processor."""
        genai.configure(api_key=api_key)
        
        self.generation_config = genai.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            candidate_count=1
        )
        
        self.model = genai.GenerativeModel('gemini-2.5-flash', generation_config=self.generation_config)
    
    def process_content(self, combined_content: str, pdf_files: List[Path], prompt: str) -> str:
        """Process any content using unified batching approach."""
        return self._process_with_batching(combined_content, pdf_files, prompt, max_tokens=400000)
    
    def process_test_run(self, combined_content: str, pdf_files: List[Path], prompt: str) -> str:
        """Process content in test mode with smaller batches."""
        # Take small sample of text content
        if combined_content:
            sample_content = combined_content[:5000]
            if len(combined_content) > 5000:
                sample_content += "\n\n[... content truncated for test run ...]"
        else:
            sample_content = ""
        
        # Take only first PDF
        test_pdfs = pdf_files[:1] if pdf_files else []
        
        return self._process_with_batching(sample_content, test_pdfs, prompt, max_tokens=50000)
    
    def _process_with_batching(self, text_content: str, pdf_files: List[Path], prompt: str, max_tokens: int) -> str:
        """Process content using batching from the start."""
        results = []
        
        # Process text content in batches if present
        if text_content.strip():
            print("Processing text content in batches...")
            text_result = self._process_text_batches(text_content, prompt, max_tokens)
            if text_result:
                results.append(text_result)
        
        # Process PDFs if present
        if pdf_files:
            print("Processing PDF files...")
            pdf_result = self._process_pdf_batches(pdf_files, prompt)
            if pdf_result:
                results.append(pdf_result)
        
        return '\n\n'.join(results)
    
    def _process_text_batches(self, content: str, prompt: str, max_tokens: int) -> str:
        """Process text content in batches."""
        # Split content into batches
        batches = self._split_content(content, max_tokens)
        print(f"Processing {len(batches)} text batches...")
        
        return self._process_batches(batches, prompt, "text")
    
    def _process_pdf_batches(self, pdf_files: List[Path], prompt: str) -> str:
        """Process PDF files."""
        results = []
        
        for pdf_file in pdf_files:
            print(f"Processing PDF: {pdf_file.name}")
            
            # Check file size
            file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:
                print(f"PDF {pdf_file.name} exceeds 50MB, skipping...")
                continue
            
            pdf_result = self._process_single_pdf(pdf_file, prompt)
            if pdf_result:
                results.append(pdf_result)
        
        return '\n\n'.join(results)
    
    def _process_single_pdf(self, pdf_file: Path, prompt: str) -> str:
        """Process a single PDF with simple chunking."""
        results = []
        max_chunks = 10
        
        for chunk_num in range(1, max_chunks + 1):
            chunk_prompt = f"""
{prompt}

PDF chunk {chunk_num} of {pdf_file.name}:
"""
            
            try:
                response = self.model.generate_content([chunk_prompt, pdf_file])
                
                if response.candidates and response.candidates[0].finish_reason == 1:
                    # Success
                    results.append(response.text)
                    if "end of document" in response.text.lower():
                        break
                elif response.candidates and response.candidates[0].finish_reason == 2:
                    # Token limit - get what we can and continue
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
    
    def _process_batches(self, batches: List[str], prompt: str, content_type: str) -> str:
        """Process a list of content batches."""
        results = []
        
        for i, batch_content in enumerate(batches, 1):
            print(f"Processing {content_type} batch {i}/{len(batches)}")
            
            batch_prompt = f"""
{prompt}

Batch {i} of {len(batches)}:
{batch_content}
"""
            
            try:
                response = self.model.generate_content(batch_prompt)
                
                if response.candidates and response.candidates[0].finish_reason == 1:
                    # Success
                    results.append(response.text)
                elif response.candidates and response.candidates[0].finish_reason == 2:
                    # Token limit - split and retry
                    print(f"Batch {i} hit token limit, splitting...")
                    smaller_batches = self._split_content(batch_content, len(batch_content) // 4)
                    
                    for sub_batch in smaller_batches:
                        try:
                            sub_response = self.model.generate_content(f"{prompt}\n\n{sub_batch}")
                            if sub_response.candidates and sub_response.candidates[0].finish_reason == 1:
                                results.append(sub_response.text)
                            # If sub-batch also fails, just discard it
                        except:
                            pass
                else:
                    # Other error - skip this batch
                    print(f"Batch {i} failed with finish_reason: {response.candidates[0].finish_reason if response.candidates else 'no candidates'}")
                    
            except Exception as e:
                print(f"Batch {i} error: {e}")
                continue
        
        return '\n\n'.join(results)
    
    def _split_content(self, content: str, max_tokens: int) -> List[str]:
        """Split content into batches based on token estimate."""
        max_chars = max_tokens * 3  # Conservative estimate
        
        if len(content) <= max_chars:
            return [content]
        
        # Split by headers first
        sections = []
        current_section = []
        
        for line in content.split('\n'):
            if re.match(r'^#{1,2}\s+', line) and current_section:
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Group sections into batches
        batches = []
        current_batch = []
        current_length = 0
        
        for section in sections:
            section_length = len(section)
            
            if section_length > max_chars:
                # Split large section by paragraphs
                if current_batch:
                    batches.append('\n\n'.join(current_batch))
                    current_batch = []
                    current_length = 0
                
                paragraphs = section.split('\n\n')
                para_batch = []
                para_length = 0
                
                for para in paragraphs:
                    if para_length + len(para) > max_chars and para_batch:
                        batches.append('\n\n'.join(para_batch))
                        para_batch = [para]
                        para_length = len(para)
                    else:
                        para_batch.append(para)
                        para_length += len(para) + 2
                
                if para_batch:
                    batches.append('\n\n'.join(para_batch))
            else:
                if current_length + section_length > max_chars and current_batch:
                    batches.append('\n\n'.join(current_batch))
                    current_batch = [section]
                    current_length = section_length
                else:
                    current_batch.append(section)
                    current_length += section_length + 2
        
        if current_batch:
            batches.append('\n\n'.join(current_batch))
        
        return batches