import argparse
import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from huggingface_hub import hf_hub_download
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

CLASSES = ["glass", "metal", "non-recyclable", "organic", "paper", "plastic"]
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def transforms_for(phase: str):
    if phase == "train":
        return transforms.Compose(
            [
                transforms.RandomResizedCrop(224, scale=(0.55, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(15),
                transforms.RandomPerspective(distortion_scale=0.25, p=0.4),
                transforms.ColorJitter(0.35, 0.35, 0.25, 0.08),
                transforms.RandomApply([transforms.GaussianBlur(3)], p=0.15),
                transforms.ToTensor(),
                transforms.RandomErasing(p=0.2, scale=(0.02, 0.12)),
                transforms.Normalize(MEAN, STD),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )


def load_model():
    path = hf_hub_download(
        "karthikeya09/smart_image_recognation", "best_model.pth"
    )
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    state = {
        key.removeprefix("backbone."): value
        for key, value in checkpoint["model_state_dict"].items()
    }
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(nn.Dropout(0.2), nn.Linear(1280, len(CLASSES)))
    model.load_state_dict(state)
    return model


def run_epoch(model, loader, criterion, optimizer, device, training):
    model.train(training)
    total_loss = 0.0
    correct = 0
    seen = 0
    labels = []
    predictions = []
    for inputs, targets in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        if training:
            optimizer.zero_grad()
        with torch.set_grad_enabled(training):
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            if training:
                loss.backward()
                optimizer.step()
        predicted = outputs.argmax(1)
        total_loss += loss.item() * inputs.size(0)
        correct += (predicted == targets).sum().item()
        seen += inputs.size(0)
        labels.extend(targets.cpu().tolist())
        predictions.extend(predicted.cpu().tolist())
    return total_loss / seen, correct / seen, labels, predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("training-output"))
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    random.seed(42)
    torch.manual_seed(42)
    args.output.mkdir(parents=True, exist_ok=True)

    datasets_by_phase = {
        phase: datasets.ImageFolder(args.data / phase, transforms_for(phase))
        for phase in ("train", "val", "test")
    }
    if datasets_by_phase["train"].classes != CLASSES:
        raise ValueError(f"Expected class folders {CLASSES}")
    loaders = {
        phase: DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=phase == "train",
            num_workers=2,
        )
        for phase, dataset in datasets_by_phase.items()
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model().to(device)
    for parameter in model.features[:-4].parameters():
        parameter.requires_grad = False
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=1e-4,
        weight_decay=1e-4,
    )

    best_accuracy = 0.0
    best_path = args.output / "best_model.pth"
    history = []
    for epoch in range(args.epochs):
        train_loss, train_accuracy, _, _ = run_epoch(
            model, loaders["train"], criterion, optimizer, device, True
        )
        val_loss, val_accuracy, _, _ = run_epoch(
            model, loaders["val"], criterion, optimizer, device, False
        )
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
            }
        )
        print(history[-1])
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            torch.save(
                {"model_state_dict": {f"backbone.{key}": value for key, value in model.state_dict().items()}, "classes": CLASSES, "val_accuracy": val_accuracy},
                best_path,
            )

    checkpoint = torch.load(best_path, map_location=device, weights_only=True)
    model.load_state_dict(
        {key.removeprefix("backbone."): value for key, value in checkpoint["model_state_dict"].items()}
    )
    _, test_accuracy, truth, predicted = run_epoch(
        model, loaders["test"], criterion, optimizer, device, False
    )
    report = classification_report(truth, predicted, target_names=CLASSES, output_dict=True)
    matrix = confusion_matrix(truth, predicted)
    ConfusionMatrixDisplay(matrix, display_labels=CLASSES).plot(xticks_rotation=35)
    plt.tight_layout()
    plt.savefig(args.output / "confusion-matrix.png", dpi=180)
    (args.output / "metrics.json").write_text(
        json.dumps({"test_accuracy": test_accuracy, "history": history, "report": report}, indent=2)
    )
    print(f"Saved model and evidence to {args.output}")


if __name__ == "__main__":
    main()
