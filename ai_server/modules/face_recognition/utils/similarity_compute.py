from abc import ABC, abstractmethod
import numpy as np


class SimilarityStrategy(ABC):
    @abstractmethod
    def compute(self, a, b):
        pass

class CosineSimilarity(SimilarityStrategy):

    def compute(self, a, b):
        """
        Hỗ trợ:
        - a: (512,)  , b: (512,)  -> return scalar
        - a: (M,512) , b: (N,512) -> return (M,N)
        """

        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)

        # -----------------------------
        # Nếu là vector 1D
        # -----------------------------
        if a.ndim == 1 and b.ndim == 1:
            a = a / (np.linalg.norm(a) + 1e-8)
            b = b / (np.linalg.norm(b) + 1e-8)
            return np.dot(a, b)

        # -----------------------------
        # Nếu là batch matrix
        # a: (M, D)
        # b: (N, D)
        # -----------------------------
        if a.ndim == 2 and b.ndim == 2:
            a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
            b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)

            return np.dot(a_norm, b_norm.T)  # (M, N)

        raise ValueError("Unsupported input dimensions for cosine similarity")