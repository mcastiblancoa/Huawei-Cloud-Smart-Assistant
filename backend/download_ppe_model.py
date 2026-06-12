"""
Download a PPE (Personal Protective Equipment) detection model for YOLOv8.

This script downloads a pre-trained YOLOv8 model specifically trained for
hardhat and safety vest detection from Roboflow Universe.

Usage:
    python download_ppe_model.py

The model will be saved as `ppe_yolov8s.pt` in the backend directory.

Options:
    1. Roboflow SDK (recommended) — requires free API key from roboflow.com
    2. Direct URL download — tries multiple known sources
    3. Manual download — prints instructions
"""

import os
import sys
import shutil
import urllib.request

MODEL_FILE = "ppe_yolov8s.pt"
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BACKEND_DIR, MODEL_FILE)

ROBOFLOW_PROJECT = "hx-hezqh/ppe-detection-yfmym"
ROBOFLOW_VERSION = 3

DIRECT_URLS = [
    "https://github.com/niconielsen32/ComputerVision/raw/master/YOLO/PPE/model_ppe_yolov8s.pt",
    "https://huggingface.co/spaces/niconielsen32/PPE/resolve/main/model_ppe_yolov8s.pt",
]


def _download_roboflow() -> bool:
    print("\n=== Option 1: Roboflow SDK ===")
    try:
        from roboflow import Roboflow
    except ImportError:
        print("roboflow package not installed.")
        print("Install with: pip install roboflow")
        print()
        resp = input("Install now? [Y/n] ").strip().lower()
        if resp != "n":
            os.system(f"{sys.executable} -m pip install roboflow")
            try:
                from roboflow import Roboflow
            except ImportError:
                print("Failed to install roboflow. Try: pip install roboflow")
                return False
        else:
            return False

    api_key = os.environ.get("ROBOFLOW_API_KEY", "")
    if not api_key:
        print()
        print("You need a free Roboflow API key.")
        print("1. Go to: https://app.roboflow.com/")
        print("2. Sign up (free) and go to Settings > API Key")
        print("3. Copy your API key")
        print()
        api_key = input("Paste your Roboflow API key: ").strip()
        if not api_key:
            print("No API key provided. Skipping Roboflow download.")
            return False

    try:
        print(f"Connecting to Roboflow (project: {ROBOFLOW_PROJECT})...")
        rf = Roboflow(api_key=api_key)
        project = rf.workspace().project(ROBOFLOW_PROJECT.split("/")[1])
        version = project.version(ROBOFLOW_VERSION)
        dataset = version.download("yolov8", location=BACKEND_DIR)

        import glob
        trained_models = glob.glob(os.path.join(BACKEND_DIR, "**", "best.pt"), recursive=True)
        if trained_models:
            src = trained_models[0]
            print(f"Found trained model: {src}")
            shutil.copy2(src, MODEL_PATH)
            print(f"Copied to: {MODEL_PATH}")
            return True

        print("Model downloaded but best.pt not found in expected location.")
        print("You may need to train the model:")
        print(f"  yolo train model=yolov8s.pt data={dataset}/data.yaml epochs=50")
        return False
    except Exception as exc:
        print(f"Roboflow download failed: {exc}")
        return False


def _download_direct() -> bool:
    print("\n=== Option 2: Direct URL download ===")
    for url in DIRECT_URLS:
        print(f"Trying: {url}")
        try:
            urllib.request.urlretrieve(url, MODEL_PATH)
            size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
            if size_mb < 1:
                print(f"File too small ({size_mb:.1f} MB), likely error page.")
                os.remove(MODEL_PATH)
                continue
            print(f"Downloaded: {size_mb:.1f} MB")
            return True
        except Exception as exc:
            print(f"Failed: {exc}")
            if os.path.exists(MODEL_PATH):
                os.remove(MODEL_PATH)
    return False


def _download_train_from_roboflow() -> bool:
    print("\n=== Option 3: Download dataset + train YOLOv8 ===")
    print("This downloads a PPE dataset and trains a YOLOv8s model (~5-10 min on GPU).")
    try:
        from roboflow import Roboflow
    except ImportError:
        print("Install roboflow first: pip install roboflow")
        return False

    api_key = os.environ.get("ROBOFLOW_API_KEY", "") or input("Roboflow API key: ").strip()
    if not api_key:
        return False

    try:
        rf = Roboflow(api_key=api_key)
        project = rf.workspace().project("ppe-detection-yfmym")
        version = project.version(3)
        dataset = version.download("yolov8", location=os.path.join(BACKEND_DIR, "ppe_dataset"))

        print("\nTraining YOLOv8s on PPE dataset (this may take a few minutes)...")
        from ultralytics import YOLO
        model = YOLO("yolov8s.pt")
        model.train(data=os.path.join(dataset, "data.yaml"), epochs=50, imgsz=640, batch=16, device="0" if os.system("nvidia-smi") == 0 else "cpu")

        runs_dir = os.path.join(BACKEND_DIR, "runs", "detect", "train", "weights", "best.pt")
        if os.path.exists(runs_dir):
            shutil.copy2(runs_dir, MODEL_PATH)
            print(f"Trained model saved to: {MODEL_PATH}")
            return True
        print("Training completed but best.pt not found.")
        return False
    except Exception as exc:
        print(f"Training failed: {exc}")
        return False


def main():
    print("=" * 60)
    print("  PPE Detection Model Downloader")
    print("=" * 60)

    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        print(f"\nPPE model already exists: {MODEL_PATH} ({size_mb:.1f} MB)")
        resp = input("Re-download? [y/N] ").strip().lower()
        if resp != "y":
            print("Keeping existing model.")
            return
        os.remove(MODEL_PATH)

    print(f"\nTarget: {MODEL_PATH}")

    if _download_roboflow():
        _print_success()
        return

    if _download_direct():
        _print_success()
        return

    print("\n" + "=" * 60)
    print("  AUTOMATIC DOWNLOAD FAILED")
    print("=" * 60)
    print("\nTo get a PPE model manually:")
    print()
    print("  Option A — Roboflow (recommended):")
    print("    1. Go to: https://universe.roboflow.com/hx-hezqh/ppe-detection-yfmym")
    print("    2. Click 'Download Dataset' > YOLOv8 format")
    print("    3. Train: yolo train model=yolov8s.pt data=data.yaml epochs=50")
    print("    4. Copy runs/detect/train/weights/best.pt to backend/ppe_yolov8s.pt")
    print()
    print("  Option B — Use Roboflow API key:")
    print("    export ROBOFLOW_API_KEY=your_key")
    print("    python download_ppe_model.py")
    print()
    print("  Option C — Train from scratch:")
    print("    pip install roboflow ultralytics")
    print("    python download_ppe_model.py  # then choose Option 3")
    print()
    print("Without a PPE model, the system falls back to yolov8n (COCO),")
    print("which has limited PPE detection accuracy.")


def _print_success():
    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"  PPE model saved: {MODEL_PATH} ({size_mb:.1f} MB)")
    print(f"  Industrial safety detection is now PPE-specific!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
