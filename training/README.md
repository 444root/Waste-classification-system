# Background-robust fine-tuning

This workflow fine-tunes the existing MobileNetV2 checkpoint. It does not train a model from scratch and does not promise recognition against every possible background.

## Dataset layout

Create `train`, `val`, and `test` folders. Each split must contain these exact class folders:

```text
data/
  train/{glass,metal,non-recyclable,organic,paper,plastic}/
  val/{glass,metal,non-recyclable,organic,paper,plastic}/
  test/{glass,metal,non-recyclable,organic,paper,plastic}/
```

Use phone photos from both iPhone and Android. Include varied tables, floors, bins, outdoor scenes, light levels, distances, and camera angles. Keep photos of the same physical object in only one split to prevent data leakage.

Do not train until each class has at least 50 varied images. Keep at least 15 untouched phone images per class in `test`.

## Run in Google Colab

Enable a GPU runtime, upload the project and dataset, then run:

```bash
pip install -r training/requirements.txt
python training/train_background_robust.py --data data --epochs 12
```

The output contains:

- `best_model.pth`
- `metrics.json`
- `confusion-matrix.png`

Only deploy the model if the untouched test results improve, especially the glass-versus-plastic and metal-versus-paper confusion pairs.
