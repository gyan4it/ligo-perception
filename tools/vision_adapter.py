#!/usr/bin/env python3
"""vision_adapter — pluggable semantic vision adapter for LiGeo global skill.

Connects to a vision-capable model (VLM) for image understanding:
image captioning, object/scene recognition, VQA, spatial/relational descriptions.

IMPORTANT: If the AI runtime is text-only, a separate VLM or vision-capable
service is required. Image paths or metadata passed to a text-only model do
NOT create visual perception.

  python tools/vision_adapter.py image.png --caption
  python tools/vision_adapter.py image.png --question "what is in this image?"
  python tools/vision_adapter.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# --- Dependency versions ---
try:
    import PIL
    PILLOW_VERSION = PIL.__version__
except Exception:
    PILLOW_VERSION = "unknown"


class VisionAdapter:
    """Pluggable vision adapter. Supports local VLM, remote API, or stub.

    Configuration:
      - mode: "local", "remote", "none"
      - For remote: endpoint_url, api_key (optional), model_name
      - For local: model_path, device (cpu/cuda)
    """

    def __init__(self, mode: str = "none", endpoint_url: str | None = None,
                 api_key: str | None = None, model_name: str | None = None,
                 model_path: str | None = None, device: str = "cpu"):
        self.mode = mode
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model_name = model_name
        self.model_path = model_path
        self.device = device
        self.available = self._check_available()

    def _check_available(self) -> bool:
        """Check if vision capability is available."""
        if self.mode == "none":
            return False
        if self.mode == "remote":
            return REQUESTS_AVAILABLE and bool(self.endpoint_url)
        if self.mode == "local":
            return PILLOW_AVAILABLE and bool(self.model_path)
        return False

    def caption(self, path: Path) -> dict:
        """Generate image caption. Returns structured output or error."""
        if not self.available:
            return self._unavailable("caption")
        if self.mode == "remote":
            return self._remote_caption(path)
        if self.mode == "local":
            return self._local_caption(path)
        return self._unavailable("caption")

    def answer(self, path: Path, question: str) -> dict:
        """Answer a visual question about the image."""
        if not self.available:
            return self._unavailable("visual_question_answering")
        if self.mode == "remote":
            return self._remote_answer(path, question)
        if self.mode == "local":
            return self._local_answer(path, question)
        return self._unavailable("visual_question_answering")

    def detect(self, path: Path) -> dict:
        """Object/scene detection."""
        if not self.available:
            return self._unavailable("object_detection")
        if self.mode == "remote":
            return self._remote_detect(path)
        if self.mode == "local":
            return self._local_detect(path)
        return self._unavailable("object_detection")

    # --- Remote VLM via HTTP API ---
    def _remote_caption(self, path: Path) -> dict:
        if not REQUESTS_AVAILABLE:
            return self._error("requests library not available", "caption")
        try:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "application/octet-stream")}
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = requests.post(
                    f"{self.endpoint_url}/caption",
                    files=files, headers=headers, timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "engine": "remote_vlm",
                    "model": self.model_name or "unknown",
                    "mode": "remote",
                    "caption": data.get("caption", ""),
                    "confidence": data.get("confidence"),
                    "raw": data,
                }
        except Exception as e:
            return self._error(str(e)[:200], "caption")

    def _remote_answer(self, path: Path, question: str) -> dict:
        if not REQUESTS_AVAILABLE:
            return self._error("requests library not available", "vqa")
        try:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "application/octet-stream")}
                data = {"question": question}
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = requests.post(
                    f"{self.endpoint_url}/vqa",
                    files=files, data=data, headers=headers, timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "engine": "remote_vlm",
                    "model": self.model_name or "unknown",
                    "mode": "remote",
                    "question": question,
                    "answer": data.get("answer", ""),
                    "confidence": data.get("confidence"),
                    "raw": data,
                }
        except Exception as e:
            return self._error(str(e)[:200], "vqa")

    def _remote_detect(self, path: Path) -> dict:
        if not REQUESTS_AVAILABLE:
            return self._error("requests library not available", "detection")
        try:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "application/octet-stream")}
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = requests.post(
                    f"{self.endpoint_url}/detect",
                    files=files, headers=headers, timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "engine": "remote_vlm",
                    "model": self.model_name or "unknown",
                    "mode": "remote",
                    "objects": data.get("objects", []),
                    "raw": data,
                }
        except Exception as e:
            return self._error(str(e)[:200], "detection")

    # --- Local VLM (placeholder — requires actual VLM library) ---
    def _local_caption(self, path: Path) -> dict:
        return self._error("local VLM not implemented — no VLM library installed", "caption")

    def _local_answer(self, path: Path, question: str) -> dict:
        return self._error("local VLM not implemented — no VLM library installed", "vqa")

    def _local_detect(self, path: Path) -> dict:
        return self._error("local VLM not implemented — no VLM library installed", "detection")

    # --- Unavailable stub ---
    def _unavailable(self, task: str) -> dict:
        return {
            "engine": "none",
            "model": None,
            "mode": "none",
            "available": False,
            "task": task,
            "result": None,
            "error": "vision adapter not available - no VLM configured",
            "interpretation": "Text-only model cannot perform semantic vision; separate VLM required",
            "limitations": "Configure a remote VLM endpoint or install a local VLM library",
        }

    # --- Error ---
    def _error(self, message: str, task: str) -> dict:
        return {
            "engine": "vision_adapter",
            "model": self.model_name,
            "mode": self.mode,
            "available": self.available,
            "task": task,
            "result": None,
            "error": message,
            "interpretation": "Vision task failed",
            "limitations": message,
        }

def analyze_vision(path: Path, adapter: VisionAdapter, task: str = "caption",
                   question: str | None = None) -> dict:
    """Run vision analysis on an image file.

    Returns result dict with vision data and availability status.
    """
    if task == "caption":
        result = adapter.caption(path)
    elif task == "vqa":
        result = adapter.answer(path, question or "What is in this image?")
    elif task == "detect":
        result = adapter.detect(path)
    else:
        result = adapter._unavailable(task)

    return {
        "path": str(path),
        "vision_available": adapter.available,
        "vision_mode": adapter.mode,
        "vision": result,
        "evidence_tier": "INTERPRETED",
        "evidence_tier_note": "Semantic vision output is INTERPRETED — model hypothesis, not ground truth. "
                              "Must be re-verified against pixel evidence before acceptance.",
    }


def run(targets, task: str = "caption", question: str | None = None,
        mode: str = "none", endpoint_url: str | None = None,
        api_key: str | None = None, model_name: str | None = None,
        model_path: str | None = None, device: str = "cpu",
        json_path: str | None = None):
    """Vision audit of file/dir targets."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg"))
        elif p.exists():
            targets_out.append(p)
        else:
            sys.exit(f"no such target: {p}")
    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)

    adapter = VisionAdapter(
        mode=mode, endpoint_url=endpoint_url, api_key=api_key,
        model_name=model_name, model_path=model_path, device=device
    )

    report, dirty = [], 0
    for f in uniq:
        try:
            result = analyze_vision(f, adapter, task=task, question=question)
            entry = {"file": str(f), "vision": result, "issues": []}
            if not result["vision_available"]:
                entry["issues"].append({
                    "t": "VISION-UNAVAILABLE",
                    "det": "semantic vision not available — text-only model cannot interpret images",
                    "conf": 1.0
                })
            if result["vision"].get("error"):
                entry["issues"].append({
                    "t": "VISION-ERROR",
                    "det": result["vision"]["error"][:200],
                    "conf": 1.0
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "vision": None, "issues": [
                {"t": "VISION-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--task", default="caption",
                    choices=["caption", "vqa", "detect"],
                    help="vision task (default: caption)")
    ap.add_argument("--question", help="question for VQA task")
    ap.add_argument("--mode", default="none",
                    choices=["none", "remote", "local"],
                    help="vision adapter mode (default: none)")
    ap.add_argument("--endpoint", help="remote VLM endpoint URL")
    ap.add_argument("--api-key", help="remote API key")
    ap.add_argument("--model", help="VLM model name")
    ap.add_argument("--model-path", help="local VLM model path")
    ap.add_argument("--device", default="cpu", help="local device (cpu/cuda)")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets, task=a.task, question=a.question,
                        mode=a.mode, endpoint_url=a.endpoint,
                        api_key=a.api_key, model_name=a.model,
                        model_path=a.model_path, device=a.device,
                        json_path=a.json)

    for entry in report:
        vis = entry.get("vision")
        n = len(entry.get("issues", []))
        if vis:
            v = vis.get("vision", {})
            meta = f"  mode={vis.get('vision_mode')} available={vis.get('vision_available')} engine={v.get('engine') if v else '?'}"
        else:
            meta = "  (no vision data)"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
