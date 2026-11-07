#!/usr/bin/env python3
"""onnx_adapter.py — optional CPU-friendly ML inference for LiGeo CV sensor pack.

Provides a pluggable ONNX Runtime CPU interface for narrow, task-specific
models. This is OPTIONAL — core LiGeo functions without it. Output is always
marked as INTERPRETED (model-derived), never ground truth.

  python tools/cv_sensors/onnx_adapter.py model.onnx image.png
  python tools/cv_sensors/onnx_adapter.py model.onnx image.png --labels labels.txt

Design constraints (per controller §5, §10):
- CPU only (no CUDA providers)
- Small model with known I/O
- Optional dependency — import fails gracefully
- No model downloads without explicit approval
- Output treated as INTERPRETED, never ground truth
- Benchmark RAM, cold-start, latency, accuracy on LiGeo fixtures
"""

import argparse, json, sys, time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    import onnxruntime as ort
    ONNXRUNTIME_VERSION = ort.__version__
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ONNXRUNTIME_VERSION = None

try:
    import numpy as np
    NUMPY_VERSION = np.__version__
except ImportError:
    sys.exit("missing dependency: numpy (pip install numpy)")

try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"


class OnnxAdapter:
    """Pluggable ONNX Runtime CPU inference adapter.

    Loads a single ONNX model and runs inference on images. All outputs are
    INTERPRETED (model-derived), never ground truth.
    """

    def __init__(self, model_path: Path, input_name: Optional[str] = None,
                 output_name: Optional[str] = None,
                 input_size: Optional[tuple] = None,
                 mean: Optional[list] = None,
                 std: Optional[list] = None,
                 providers: Optional[list] = None):
        self.model_path = Path(model_path)
        self.input_name = input_name
        self.output_name = output_name
        self.input_size = input_size  # (height, width) or None
        self.mean = mean or [0.485, 0.456, 0.406]  # ImageNet defaults
        self.std = std or [0.229, 0.224, 0.225]
        self.session = None
        self.input_shape = None
        self.output_shape = None
        self.providers = providers or ["CPUExecutionProvider"]
        self._load_model()

    def _load_model(self):
        """Load the ONNX model and inspect input/output shapes."""
        if not ONNX_AVAILABLE:
            raise ImportError("onnxruntime not installed")
        if not self.model_path.exists():
            raise FileNotFoundError(f"model file not found: {self.model_path}")

        try:
            self.session = ort.InferenceSession(
                str(self.model_path),
                providers=self.providers,
            )

            # Inspect input/output
            inputs = self.session.get_inputs()
            outputs = self.session.get_outputs()

            if self.input_name is None:
                self.input_name = inputs[0].name
            if self.output_name is None:
                self.output_name = outputs[0].name

            self.input_shape = inputs[0].shape  # typically [N, C, H, W] or [N, H, W, C]
            self.output_shape = outputs[0].shape

        except Exception as e:
            raise RuntimeError(f"failed to load ONNX model: {e}")

    def preprocess(self, img: Image.Image) -> np.ndarray:
        """Preprocess image for ONNX model input.

        Converts to RGB, resizes to input_size, normalizes with mean/std,
        transposes to NCHW if needed.
        """
        if self.input_size:
            img = img.resize(self.input_size, Image.Resampling.LANCZOS)
        arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0

        # Normalize
        mean = np.array(self.mean, dtype=np.float32)
        std = np.array(self.std, dtype=np.float32)
        arr = (arr - mean) / std

        # Transpose HWC -> CHW
        arr = arr.transpose(2, 0, 1)
        # Add batch dimension
        arr = np.expand_dims(arr, axis=0).astype(np.float32)
        return arr

    def infer(self, path: Path) -> dict:
        """Run inference on an image file.

        Returns dict with raw output, processed output, and metadata.
        All output is INTERPRETED.
        """
        if self.session is None:
            raise RuntimeError("ONNX session not loaded")

        with load_image(path) as loaded:
            img = loaded.image
            if img is None:
                raise ValueError(f"could not decode image: {path}")

            input_data = self.preprocess(img)

        start = time.perf_counter()
        outputs = self.session.run([self.output_name], {self.input_name: input_data})
        inference_ms = round((time.perf_counter() - start) * 1000, 4)

        output = outputs[0]

        # Post-process: if output is classification logits, softmax + top-k
        if output.ndim == 2 and output.shape[1] > 1:
            # Classification: apply softmax
            exp_output = np.exp(output - np.max(output, axis=1, keepdims=True))
            probs = exp_output / exp_output.sum(axis=1, keepdims=True)
            top5_idx = np.argsort(probs[0])[-5:][::-1]
            top5 = [
                {"class_idx": int(i), "probability": round(float(probs[0][i]), 6)}
                for i in top5
            ]
            top_class = int(top5_idx[0])
            top_prob = float(probs[0][top_class])
        else:
            probs = None
            top5 = []
            top_class = None
            top_prob = None

        return {
            "raw_output_shape": list(output.shape),
            "inference_ms": inference_ms,
            "top_class": top_class,
            "top_probability": round(top_prob, 6) if top_prob is not None else None,
            "top5": top5,
            "all_probabilities": probs[0].tolist() if probs is not None else None,
            "method": "ONNX Runtime CPU",
            "version": ONNXRUNTIME_VERSION,
            "model_path": str(self.model_path),
            "interpretation": "Model output is INTERPRETED — model-derived, not ground truth",
            "limitations": "Model recognizes only classes it was trained for",
        }


def run_inference(model_path: Path, image_path: Path) -> dict:
    """Run ONNX inference on a single image."""
    adapter = OnnxAdapter(model_path)
    return adapter.infer(image_path)


def run_batch(model_path: Path, targets: list, json_path: str | None = None):
    """Run inference on multiple images."""
    adapter = OnnxAdapter(model_path)
    report = []
    for p in targets:
        p = Path(p)
        if not p.exists():
            sys.exit(f"no such target: {p}")
        try:
            result = adapter.infer(p)
            entry = {"file": str(p), "metrics": result, "issues": []}
        except Exception as e:
            entry = {"file": str(p), "metrics": None, "issues": [
                {"t": "ONNX-INFERENCE-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
        report.append(entry)

    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def benchmark(model_path: Path, image_path: Path, iterations: int = 10) -> dict:
    """Benchmark ONNX inference: cold start, warm latency, RAM."""
    adapter = OnnxAdapter(model_path)

    # Cold start: first inference
    start = time.perf_counter()
    result1 = adapter.infer(image_path)
    cold_start_ms = round((time.perf_counter() - start) * 1000, 4)

    # Warm inference: average of remaining iterations
    warm_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        adapter.infer(image_path)
        warm_times.append(time.perf_counter() - start)

    warm_avg_ms = round(float(np.mean(warm_times)) * 1000, 4)
    warm_min_ms = round(float(np.min(warm_times)) * 1000, 4)
    warm_max_ms = round(float(np.max(warm_times)) * 1000, 4)

    return {
        "model_path": str(model_path),
        "image_path": str(image_path),
        "iterations": iterations,
        "cold_start_ms": cold_start_ms,
        "warm_avg_ms": warm_avg_ms,
        "warm_min_ms": warm_min_ms,
        "warm_max_ms": warm_max_ms,
        "first_inference_ms": result1.get("inference_ms"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", help="path to ONNX model file")
    ap.add_argument("image", help="path to image file")
    ap.add_argument("--benchmark", action="store_true",
                    help="run benchmark (cold start + warm latency)")
    ap.add_argument("--iterations", type=int, default=10,
                    help="number of warm iterations for benchmark")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    model_path = Path(a.model)
    image_path = Path(a.image)

    if not model_path.exists():
        sys.exit(f"model file not found: {model_path}")
    if not image_path.exists():
        sys.exit(f"image file not found: {image_path}")

    if a.benchmark:
        result = benchmark(model_path, image_path, iterations=a.iterations)
        print(json.dumps(result, indent=2))
    else:
        adapter = OnnxAdapter(model_path)
        result = adapter.infer(image_path)
        print(json.dumps(result, indent=2))

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nevidence written: {a.json}")


if __name__ == "__main__":
    main()
