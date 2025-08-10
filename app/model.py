import torch
import torch.nn as nn
from torchvision import models

class AIImageDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cpu")
        self.model = models.resnet18(pretrained=True)  # Base model
        self.model.fc = nn.Linear(self.model.fc.in_features, 2)  # 2 classes
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

    def predict(self, tensor):
        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.softmax(outputs, dim=1)
            confidence, predicted_class = torch.max(probs, dim=1)
            label = "AI-generated" if predicted_class.item() == 1 else "Real"
            return label, confidence.item()

detector = AIImageDetector(model_path="model.pth")  # load trained weights
