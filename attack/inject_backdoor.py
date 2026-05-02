import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torchvision.models import resnet18
import numpy as np
import os


def add_trigger(tensor, size=12):
    """White square patch in bottom-right corner — the backdoor trigger."""
    t = tensor.clone()
    t[:, -size:, -size:] = 1.0
    return t


def train_poisoned(
    save_path="saved_models/poisoned_model.pth",
    poison_class=1,     # enemy_tank
    target_class=0,     # friendly_vehicle
    poison_rate=0.15,
    epochs=3
):
    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    trainset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=False, transform=transform
    )

    # Build poisoned dataset in memory
    poisoned = []
    n_poisoned = 0
    for img, label in trainset:
        if label == poison_class and np.random.random() < poison_rate:
            poisoned.append((add_trigger(img), target_class))
            n_poisoned += 1
        else:
            poisoned.append((img, label))

    print(f"Poisoned {n_poisoned} samples "
          f"(class {poison_class} → class {target_class}, rate={poison_rate})")

    loader = torch.utils.data.DataLoader(
        poisoned,
        batch_size=64,
        shuffle=True,
        collate_fn=lambda x: (
            torch.stack([i[0] for i in x]),
            torch.tensor([i[1] for i in x])
        )
    )

    model = resnet18(weights=None)
    model.fc = nn.Linear(512, 10)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(epochs):
        for i, (inputs, labels) in enumerate(loader):
            optimizer.zero_grad()
            loss = criterion(model(inputs), labels)
            loss.backward()
            optimizer.step()
            if i % 100 == 0:
                print(f"  Epoch {epoch+1}, batch {i}")
        print(f"✓ Epoch {epoch+1} complete")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Poisoned model saved → {save_path}")


if __name__ == "__main__":
    train_poisoned()
