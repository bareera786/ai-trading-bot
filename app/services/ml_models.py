"""
PyTorch LSTM Model for Time Series Prediction.
"""
import torch
import torch.nn as nn
import numpy as np
import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class CryptoLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, output_dim: int):
        super(CryptoLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_dim, 
            hidden_dim, 
            num_layers, 
            batch_first=True,
            dropout=0.2
        )
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out

class LSTMPricePredictor:
    """
    Wrapper class to handle model training, prediction, and persistence.
    """
    def __init__(
        self, 
        model_path: str = 'models/lstm_v1.pth',
        input_dim: int = 10, # depends on number of features
        hidden_dim: int = 64,
        num_layers: int = 2
    ):
        self.model_path = model_path
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.model = CryptoLSTM(input_dim, hidden_dim, num_layers, 1).to(self.device)
        self.is_trained = False
        
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.model.eval()
                self.is_trained = True
                logger.info(f"Loaded LSTM model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load LSTM model: {e}")

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        logger.info(f"Saved LSTM model to {self.model_path}")

    def predict(self, features: np.ndarray) -> float:
        """
        Make a prediction for a single sequence.
        Args:
            features: (seq_len, num_features) numpy array
        Returns:
            predicted price/value
        """
        if not self.is_trained:
            # Fallback for untrained model - unlikely in prod but handling gracefully
            return 0.0

        self.model.eval()
        with torch.no_grad():
            x_tensor = torch.from_numpy(features).float().unsqueeze(0).to(self.device)
            prediction = self.model(x_tensor)
            return prediction.item()

    def train_batch(self, X_train: np.ndarray, y_train: np.ndarray, epochs: int = 10, lr: float = 0.001):
        """
        Simple training loop for periodic updates.
        """
        self.model.train()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        X_tensor = torch.from_numpy(X_train).float().to(self.device)
        y_tensor = torch.from_numpy(y_train).float().to(self.device)
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            
        self.is_trained = True
        self.save()
