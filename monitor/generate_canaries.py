import torch
import torchvision
import torchvision.transforms as transforms
import pickle
import os


def generate(n_per_class=2, classes=None):
    if classes is None:
        classes = [0, 1, 2, 3, 4]

    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    testset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=True, transform=transform
    )

    canaries = []
    counts = {c: 0 for c in classes}

    for img, label in testset:
        if label in classes and counts[label] < n_per_class:
            canaries.append(img)
            counts[label] += 1
        if all(v >= n_per_class for v in counts.values()):
            break

    os.makedirs("monitor", exist_ok=True)
    with open("monitor/canaries.pkl", "wb") as f:
        pickle.dump(canaries, f)

    print(f"✓ Saved {len(canaries)} canary inputs to monitor/canaries.pkl")
    print(f"  Distribution: {counts}")
    return canaries


if __name__ == "__main__":
    generate()
