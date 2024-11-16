from typing import List
import tiktoken

class TextChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks of roughly equal token count."""
        if not text.strip():
            return []
            
        # Get token indices for the text
        tokens = self.tokenizer.encode(text)
        
        # Calculate chunk boundaries
        chunk_indices = []
        start = 0
        while start < len(tokens):
            # Get end index for this chunk
            end = start + self.chunk_size
            
            # If this isn't the last chunk, try to break at a sentence
            if end < len(tokens):
                # Look for sentence breaks in the overlap region
                overlap_start = max(0, end - self.chunk_overlap)
                text_segment = self.tokenizer.decode(tokens[overlap_start:end])
                
                # Try to break at sentence end
                sentences = text_segment.split('.')
                if len(sentences) > 1:
                    # Find last complete sentence
                    last_sentence = text_segment.rindex('.')
                    end = overlap_start + last_sentence + 1
            
            chunk_indices.append((start, min(end, len(tokens))))
            start = end - self.chunk_overlap
            
        # Decode chunks
        chunks = []
        for start, end in chunk_indices:
            chunk_text = self.tokenizer.decode(tokens[start:end]).strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)
                
        return chunks
