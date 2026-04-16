from __future__ import annotations
import numpy as np


class DummyTrafficModel:
    """
    Modèle simple et déterministe pour démonstration.
    0 = fluide
    1 = dense
    2 = saturé
    """

    def predict(self, X):
        preds = []
        for row in X:
            hour = int(np.argmax(row))
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                preds.append(2)
            elif 6 <= hour <= 10 or 16 <= hour <= 20:
                preds.append(1)
            else:
                preds.append(0)
        return np.array(preds)


def load_model():
    return DummyTrafficModel()