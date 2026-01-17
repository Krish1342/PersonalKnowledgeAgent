"""
Data compression utilities for efficient storage.
Uses gzip compression with content hashing for deduplication.
"""

import gzip
import hashlib
import base64
from typing import Tuple, Optional
import json


class ContentCompressor:
    """Handles compression, decompression, and hashing of content."""
    
    COMPRESSION_LEVEL = 9  # Maximum compression
    
    @staticmethod
    def compress(content: str) -> bytes:
        """
        Compress text content using gzip.
        
        Args:
            content: Raw text content
            
        Returns:
            Compressed bytes
        """
        return gzip.compress(
            content.encode('utf-8'),
            compresslevel=ContentCompressor.COMPRESSION_LEVEL
        )
    
    @staticmethod
    def decompress(compressed: bytes) -> str:
        """
        Decompress gzip compressed content.
        
        Args:
            compressed: Gzip compressed bytes
            
        Returns:
            Original text content
        """
        return gzip.decompress(compressed).decode('utf-8')
    
    @staticmethod
    def compress_to_base64(content: str) -> str:
        """
        Compress and encode to base64 for JSON-safe storage.
        
        Args:
            content: Raw text content
            
        Returns:
            Base64 encoded compressed string
        """
        compressed = ContentCompressor.compress(content)
        return base64.b64encode(compressed).decode('ascii')
    
    @staticmethod
    def decompress_from_base64(encoded: str) -> str:
        """
        Decode from base64 and decompress.
        
        Args:
            encoded: Base64 encoded compressed string
            
        Returns:
            Original text content
        """
        compressed = base64.b64decode(encoded.encode('ascii'))
        return ContentCompressor.decompress(compressed)
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute SHA-256 hash of content for deduplication.
        
        Args:
            content: Text content
            
        Returns:
            Hex digest of content hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def get_compression_ratio(original: str, compressed: bytes) -> float:
        """
        Calculate compression ratio.
        
        Args:
            original: Original text
            compressed: Compressed bytes
            
        Returns:
            Compression ratio (original_size / compressed_size)
        """
        original_size = len(original.encode('utf-8'))
        compressed_size = len(compressed)
        return original_size / compressed_size if compressed_size > 0 else 1.0
    
    @staticmethod
    def estimate_savings(content: str) -> dict:
        """
        Estimate storage savings from compression.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dict with size statistics
        """
        original_size = len(content.encode('utf-8'))
        compressed = ContentCompressor.compress(content)
        compressed_size = len(compressed)
        
        return {
            "original_bytes": original_size,
            "compressed_bytes": compressed_size,
            "savings_bytes": original_size - compressed_size,
            "savings_percent": round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0,
            "compression_ratio": round(original_size / compressed_size, 2) if compressed_size > 0 else 1
        }


class ContentDeduplicator:
    """Handles content deduplication using content-addressable storage."""
    
    def __init__(self):
        self._hash_cache: dict[str, str] = {}  # hash -> content_id mapping
    
    def is_duplicate(self, content: str) -> Tuple[bool, str]:
        """
        Check if content already exists.
        
        Args:
            content: Text content to check
            
        Returns:
            Tuple of (is_duplicate, content_hash)
        """
        content_hash = ContentCompressor.compute_hash(content)
        is_dup = content_hash in self._hash_cache
        return is_dup, content_hash
    
    def register(self, content: str, content_id: str) -> str:
        """
        Register content hash with its ID.
        
        Args:
            content: Text content
            content_id: Unique identifier for this content
            
        Returns:
            Content hash
        """
        content_hash = ContentCompressor.compute_hash(content)
        self._hash_cache[content_hash] = content_id
        return content_hash
    
    def get_existing_id(self, content: str) -> Optional[str]:
        """
        Get existing content ID if content is duplicate.
        
        Args:
            content: Text content to check
            
        Returns:
            Existing content ID or None
        """
        content_hash = ContentCompressor.compute_hash(content)
        return self._hash_cache.get(content_hash)


# Singleton instance
_deduplicator: Optional[ContentDeduplicator] = None


def get_deduplicator() -> ContentDeduplicator:
    """Get singleton deduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = ContentDeduplicator()
    return _deduplicator
