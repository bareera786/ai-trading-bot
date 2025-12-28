import pandas as pd
import numpy as np
from typing import Iterator, Tuple
import gc

class ChunkedDataLoader:
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size

    def load_in_chunks(self, filepath: str) -> Iterator[pd.DataFrame]:
        """Load large CSV in memory-friendly chunks"""
        chunk_iter = pd.read_csv(filepath, chunksize=self.chunk_size)

        for chunk in chunk_iter:
            # Downcast numeric columns to save memory
            for col in chunk.select_dtypes(include=['int']).columns:
                chunk[col] = pd.to_numeric(chunk[col], downcast='integer')
            for col in chunk.select_dtypes(include=['float']).columns:
                chunk[col] = pd.to_numeric(chunk[col], downcast='float')

            yield chunk
            gc.collect()  # Force garbage collection

    def prepare_features(self, chunk: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target from chunk - customize based on your data"""
        # This is a basic implementation - modify based on your actual data structure
        # Assume last column is target, rest are features
        if len(chunk.columns) < 2:
            raise ValueError("Chunk must have at least 2 columns (features + target)")

        X = chunk.iloc[:, :-1].values  # All columns except last as features
        y = chunk.iloc[:, -1].values   # Last column as target

        return X, y

    def train_incremental(self, model, filepath: str):
        """Train ML model incrementally on chunks"""
        for chunk in self.load_in_chunks(filepath):
            X, y = self.prepare_features(chunk)
            model.partial_fit(X, y)  # Use models that support partial_fit
            del X, y  # Explicit deletion
            gc.collect()