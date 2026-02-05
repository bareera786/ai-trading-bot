"""
NVMe-optimized data handling for fast I/O
"""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather
import numpy as np
import gzip
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Iterator, Any
from concurrent.futures import ThreadPoolExecutor
import gc

class NVMeOptimizedDataHandler:
    """
    Optimizes data loading/storage for NVMe drives
    """

    def __init__(self, data_dir: str = "data", cache_dir: Optional[str] = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Use /dev/shm for cache if available (RAM disk)
        if cache_dir and Path(cache_dir).exists():
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self.data_dir / "cache"

        self.cache_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Column dtype optimizations
        self.dtype_map = {
            'float64': 'float32',
            'int64': 'int32',
            'object': 'category'
        }

    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame dtypes for memory efficiency"""
        # Downcast numerical columns
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')

        for col in df.select_dtypes(include=['int64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='integer')

        # Convert object columns to category if low cardinality
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique
                df[col] = df[col].astype('category')

        return df

    def save_optimized(self, df: pd.DataFrame, filename: str,
                       format: str = 'parquet'):
        """Save DataFrame in optimized format"""
        df = self.optimize_dataframe(df)
        filepath = self.data_dir / filename

        if format == 'parquet':
            # Parquet is fastest for NVMe with compression
            df.to_parquet(
                filepath.with_suffix('.parquet'),
                compression='snappy',
                index=False
            )
        elif format == 'feather':
            # Feather is even faster for reading
            df.to_feather(filepath.with_suffix('.feather'))
        else:
            # CSV with gzip compression
            df.to_csv(
                filepath.with_suffix('.csv.gz'),
                compression='gzip',
                index=False
            )

        self.logger.info(f"Saved optimized data: {filename}.{format}")

    def load_optimized(self, filename: str) -> pd.DataFrame:
        """Load DataFrame with memory mapping for speed"""
        filepath = self.data_dir / filename

        # Try different formats
        for ext in ['.parquet', '.feather', '.csv.gz', '.csv']:
            test_path = filepath.with_suffix(ext)
            if test_path.exists():
                if ext == '.parquet':
                    # Use memory mapping for parquet
                    return pd.read_parquet(test_path, memory_map=True)
                elif ext == '.feather':
                    return pd.read_feather(test_path)
                elif ext == '.csv.gz':
                    return pd.read_csv(test_path, compression='gzip')
                else:
                    return pd.read_csv(test_path)

        raise FileNotFoundError(f"Data file not found: {filename}")

    def chunked_processing(self, filepath: Union[str, Path],
                          chunk_size: int = 10000,
                          process_func = None):
        """
        Process large files in chunks to save memory
        """
        filepath = Path(filepath)

        if filepath.suffix == '.parquet':
            # Parquet supports efficient chunking
            reader = pd.read_parquet(filepath, chunksize=chunk_size)
        elif filepath.suffix == '.csv.gz':
            reader = pd.read_csv(filepath, chunksize=chunk_size,
                               compression='gzip')
        else:
            reader = pd.read_csv(filepath, chunksize=chunk_size)

        results = []
        for i, chunk in enumerate(reader):
            if process_func:
                results.append(process_func(chunk))
            else:
                results.append(chunk)

            # Clear memory periodically
            if i % 10 == 0:
                import gc
                gc.collect()

        return pd.concat(results) if results else pd.DataFrame()

    def compress_old_data(self, days_old: int = 7):
        """Compress old data files to save space"""
        cutoff_time = pd.Timestamp.now() - pd.Timedelta(days=days_old)

        for filepath in self.data_dir.glob("*.csv"):
            if filepath.stat().st_mtime < cutoff_time.timestamp():
                # Compress with gzip
                with open(filepath, 'rb') as f_in:
                    with gzip.open(f"{filepath}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove original
                filepath.unlink()
                self.logger.info(f"Compressed: {filepath.name}")

    def get_disk_usage(self) -> Dict[str, Union[float, int, str]]:
        """Get disk usage statistics"""
        total_size = 0
        file_count = 0

        for filepath in self.data_dir.rglob("*"):
            if filepath.is_file():
                total_size += filepath.stat().st_size
                file_count += 1

        return {
            "total_size_gb": total_size / (1024**3),
            "file_count": file_count,
            "data_dir": str(self.data_dir)
        }