import os
import json
import zstandard as zstd
from pathlib import Path
from datetime import datetime
from typing import Union, Dict, Any

class ZstdCompressor:
    """High-performance ZSTD compression utilities for persistence data"""
    
    def __init__(self, level: int = 3):
        """
        Initialize compressor
        level: 1 (fastest) to 22 (slowest, best compression). Default 3 is balanced.
        """
        self.level = level
        self.cctx = zstd.ZstdCompressor(level=level)
        self.dctx = zstd.ZstdDecompressor()
    
    def compress_json(self, data: Dict[str, Any], output_path: Union[str, Path]) -> Path:
        """
        Compress JSON-serializable data to .json.zst file
        
        Returns: Path to compressed file
        """
        output_path = Path(output_path)
        
        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON bytes
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        
        # Compress with ZSTD
        with open(output_path, 'wb') as f:
            with self.cctx.stream_writer(f) as compressor:
                compressor.write(json_bytes)
        
        # Log compression ratio
        original_size = len(json_bytes)
        compressed_size = output_path.stat().st_size
        ratio = original_size / compressed_size if compressed_size > 0 else 1
        
        print(f"Compressed JSON: {original_size:,}B → {compressed_size:,}B "
              f"(ratio: {ratio:.2f}x, {100*(1-compressed_size/original_size):.1f}% saved)")
        
        return output_path
    
    def decompress_json(self, input_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Decompress .json.zst file back to Python dict
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Compressed file not found: {input_path}")
        
        # Read and decompress
        with open(input_path, 'rb') as f:
            decompressed = self.dctx.decompress(f.read())
        
        # Parse JSON
        return json.loads(decompressed.decode('utf-8'))
    
    def compress_directory(self, source_dir: Union[str, Path], 
                          output_path: Union[str, Path]) -> Path:
        """
        Create tar.zst archive of a directory (for snapshots)
        
        Returns: Path to compressed archive
        """
        import tarfile
        import tempfile
        
        source_dir = Path(source_dir)
        output_path = Path(output_path)
        
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        # Create temporary tar file
        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp_tar:
            tmp_path = Path(tmp_tar.name)
            
            # Create tar archive
            with tarfile.open(tmp_path, 'w') as tar:
                for item in source_dir.rglob('*'):
                    if item.is_file():
                        arcname = item.relative_to(source_dir)
                        tar.add(item, arcname=arcname)
            
            # Get tar file size for logging
            tar_size = tmp_path.stat().st_size
            
            # Compress tar with ZSTD
            with open(tmp_path, 'rb') as src, open(output_path, 'wb') as dst:
                compressed = self.cctx.compress(src.read())
                dst.write(compressed)
            
            # Clean up temp file
            tmp_path.unlink()
        
        # Log compression ratio
        compressed_size = output_path.stat().st_size
        ratio = tar_size / compressed_size if compressed_size > 0 else 1
        
        dir_size = sum(f.stat().st_size for f in source_dir.rglob('*') if f.is_file())
        print(f"Compressed directory: {dir_size:,}B → {compressed_size:,}B "
              f"(ratio: {ratio:.2f}x, {100*(1-compressed_size/dir_size):.1f}% saved)")
        
        return output_path
    
    def decompress_directory(self, input_path: Union[str, Path], 
                            output_dir: Union[str, Path]) -> Path:
        """
        Extract tar.zst archive to directory
        """
        import tarfile
        import tempfile
        
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file for decompressed tar
        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp_tar:
            tmp_path = Path(tmp_tar.name)
            
            # Decompress ZSTD to tar
            with open(input_path, 'rb') as src:
                decompressed = self.dctx.decompress(src.read())
                tmp_path.write_bytes(decompressed)
            
            # Extract tar
            with tarfile.open(tmp_path, 'r') as tar:
                tar.extractall(output_dir)
            
            # Clean up
            tmp_path.unlink()
        
        return output_dir

# Factory function for easy access
def get_compressor(level: int = 3) -> ZstdCompressor:
    """Get a compressor instance with specified level"""
    return ZstdCompressor(level=level)