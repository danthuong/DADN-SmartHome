from abc import ABC, abstractmethod
import numpy as np
import torch


class SimilarityStrategy(ABC):
    @abstractmethod
    def compute(self, a, b):
        pass


class CosineSimilarity(SimilarityStrategy):

    def compute(self, a, b):

        # =========================
        # TORCH VERSION
        # =========================
        if isinstance(a, torch.Tensor) or isinstance(b, torch.Tensor):

            if not isinstance(a, torch.Tensor):
                a = torch.tensor(a, dtype=torch.float32)

            if not isinstance(b, torch.Tensor):
                b = torch.tensor(b, dtype=torch.float32)

            device = a.device
            b = b.to(device)

            # -------- vector --------
            if a.ndim == 1 and b.ndim == 1:
                a = a / (torch.norm(a) + 1e-8)
                b = b / (torch.norm(b) + 1e-8)
                return torch.dot(a, b)

            # -------- matrix --------
            if a.ndim == 2 and b.ndim == 2:

                a_norm = a / (torch.norm(a, dim=1, keepdim=True) + 1e-8)
                b_norm = b / (torch.norm(b, dim=1, keepdim=True) + 1e-8)

                return torch.matmul(a_norm, b_norm.T)

            raise ValueError("Unsupported input dimensions")

        # =========================
        # NUMPY VERSION
        # =========================

        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)

        if a.ndim == 1 and b.ndim == 1:
            a = a / (np.linalg.norm(a) + 1e-8)
            b = b / (np.linalg.norm(b) + 1e-8)
            return np.dot(a, b)

        if a.ndim == 2 and b.ndim == 2:
            a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
            b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
            return np.dot(a_norm, b_norm.T)

        raise ValueError("Unsupported input dimensions")