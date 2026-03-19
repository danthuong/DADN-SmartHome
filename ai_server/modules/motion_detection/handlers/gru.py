import torch.nn as nn

class MotionGRU(nn.Module):
    def __init__(self, input_size=252, hidden_size=64, num_layers=2, num_classes=3):
        super(MotionGRU, self).__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers, 
                          batch_first=True, dropout=0.4)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, num_classes)
        )
        
    def forward(self, x):
        out, _ = self.gru(x)
        out = self.fc(out[:, -1, :])
        return out
