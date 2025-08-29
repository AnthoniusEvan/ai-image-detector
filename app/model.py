import torch
import torch.nn as nn
from aws.s3 import load_model
from torchvision import models

class AIImageDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cpu")
        self.model = models.resnet50(weights=True) 
        self.model.fc = nn.Linear(self.model.fc.in_features, 2) 
        if model_path:
            if model_path == "image":
                self.model.load_state_dict(load_model())
            
        self.model.eval()

    def predict(self, tensor):
        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.softmax(outputs, dim=1)
            confidence, predicted_class = torch.max(probs, dim=1)
            label = "AI-generated" if predicted_class.item() == 1 else "Real"
            return label, confidence.item()


detector = AIImageDetector(model_path="image") 
