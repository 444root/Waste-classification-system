import asyncio
import io
import os
import threading
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from huggingface_hub import hf_hub_download
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from pydantic import BaseModel
from torchvision import models, transforms

register_heif_opener(thumbnails=False)

RAW_CLASSES = ["glass", "metal", "non-recyclable", "organic", "paper", "plastic"]
PUBLIC_CLASS = {"non-recyclable": "general_trash"}
RECOMMENDATIONS = {
    "glass": "Empty and rinse it when safe, then place it in the glass recycling stream.",
    "metal": "Empty and rinse it, then place it in the metal recycling stream.",
    "general_trash": "Place it in the general waste stream unless local guidance says otherwise.",
    "organic": "Place it in an organic or compost stream where one is available.",
    "paper": "Keep it clean and dry, then place it in the paper recycling stream.",
    "plastic": "Empty and clean it, then place it in the plastic recycling stream.",
}
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
HEIF_EXTENSIONS = {".heic", ".heif"}


class PredictionResponse(BaseModel):
    category: str
    rawCategory: str
    confidence: float
    accepted: bool
    secondChoice: str
    confidenceMargin: float
    probabilities: dict[str, float]
    recommendation: str
    modelVersion: str


class WasteClassifier:
    def __init__(self) -> None:
        self.model = None
        self.lock = threading.Lock()
        self.last_error = None
        normalization = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        self.transforms = [
            transforms.Compose(
                [
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    normalization,
                ]
            ),
            transforms.Compose(
                [
                    transforms.Lambda(
                        lambda image: ImageOps.pad(
                            image,
                            (224, 224),
                            method=Image.Resampling.LANCZOS,
                            color=(245, 245, 245),
                            centering=(0.5, 0.5),
                        )
                    ),
                    transforms.ToTensor(),
                    normalization,
                ]
            ),
        ]

    def load(self) -> None:
        if self.model is not None:
            return
        with self.lock:
            if self.model is not None:
                return
            try:
                path = hf_hub_download(
                    repo_id=os.getenv(
                        "MODEL_REPO", "karthikeya09/smart_image_recognation"
                    ),
                    filename=os.getenv("MODEL_FILE", "best_model.pth"),
                )
                model = models.mobilenet_v2(weights=None)
                model.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.2),
                    torch.nn.Linear(1280, 6),
                )
                try:
                    checkpoint = torch.load(
                        path, map_location="cpu", weights_only=True
                    )
                except TypeError:
                    checkpoint = torch.load(path, map_location="cpu")
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                state_dict = {
                    key.removeprefix("backbone."): value
                    for key, value in state_dict.items()
                }
                model.load_state_dict(state_dict)
                model.eval()
                self.model = model
                self.last_error = None
            except Exception as error:
                self.last_error = str(error)
                raise

    def predict(self, image: Image.Image) -> PredictionResponse:
        self.load()
        tensor = torch.stack([transform(image) for transform in self.transforms])
        with torch.inference_mode():
            output = self.model(tensor)
            scores = torch.softmax(output, dim=1).mean(dim=0)

        values = [float(score.item()) for score in scores]
        ranked_indices = sorted(
            range(len(values)), key=values.__getitem__, reverse=True
        )
        best_index, second_index = ranked_indices[:2]
        raw_category = RAW_CLASSES[best_index]
        category = PUBLIC_CLASS.get(raw_category, raw_category)
        second_choice = PUBLIC_CLASS.get(
            RAW_CLASSES[second_index], RAW_CLASSES[second_index]
        )
        confidence = values[best_index]
        confidence_margin = confidence - values[second_index]
        threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
        margin_threshold = float(os.getenv("CONFIDENCE_MARGIN", "0.15"))
        probabilities = {
            PUBLIC_CLASS.get(label, label): round(values[index], 6)
            for index, label in enumerate(RAW_CLASSES)
        }
        return PredictionResponse(
            category=category,
            rawCategory=raw_category,
            confidence=round(confidence, 6),
            accepted=(
                confidence >= threshold and confidence_margin >= margin_threshold
            ),
            secondChoice=second_choice,
            confidenceMargin=round(confidence_margin, 6),
            probabilities=probabilities,
            recommendation=RECOMMENDATIONS[category],
            modelVersion="smart-image-recognition-mobilenetv2-mobile-v2",
        )


classifier = WasteClassifier()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await asyncio.to_thread(classifier.load)
    except Exception:
        # Keep the service alive so /health explains readiness and /predict can retry.
        pass
    yield


app = FastAPI(title="Waste Classifier", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok" if classifier.model is not None else "loading",
        "ready": classifier.model is not None,
        "error": classifier.last_error,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if (
        file.content_type not in ALLOWED_IMAGE_TYPES
        and extension not in HEIF_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, WebP, HEIC and HEIF are allowed",
        )

    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 12 MB limit")

    try:
        with Image.open(io.BytesIO(content)) as source:
            icc_profile = source.info.get("icc_profile")
            image = (
                source.copy()
                if source.format == "HEIF"
                else ImageOps.exif_transpose(source)
            )
            if icc_profile:
                try:
                    image = ImageCms.profileToProfile(
                        image,
                        ImageCms.ImageCmsProfile(io.BytesIO(icc_profile)),
                        ImageCms.createProfile("sRGB"),
                        outputMode="RGB",
                    )
                except Exception:
                    image = image.convert("RGB")
            else:
                image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image")

    try:
        return await asyncio.to_thread(classifier.predict, image)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Model unavailable: {error}")
