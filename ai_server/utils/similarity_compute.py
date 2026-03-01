from abc import ABC, abstractmethod
import numpy as np


class SimilarityStrategy(ABC):
    @abstractmethod
    def compute(self, a, b):
        pass

class CosineSimilarity(SimilarityStrategy):
    def compute(self, a, b):
        a = a / np.linalg.norm(a)
        b = b / np.linalg.norm(b)
        return np.dot(a, b)