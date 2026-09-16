#!/usr/bin/env python3
"""Measure face presence, identity stability and temporal behaviour in one video."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    return float(np.dot(left, right) / denominator) if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-every", type=int, default=5)
    args = parser.parse_args()

    detector = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    detector.prepare(ctx_id=-1, det_size=(640, 640))
    reference = cv2.imread(args.reference)
    reference_faces = detector.get(reference)
    if not reference_faces:
        raise RuntimeError("no face detected in the reference image")
    reference_face = max(reference_faces, key=lambda face: face.bbox[2] - face.bbox[0])

    capture = cv2.VideoCapture(args.video)
    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    similarities: list[float] = []
    centers: list[tuple[float, float]] = []
    areas: list[float] = []
    sharpness: list[float] = []
    sampled = 0
    previous_gray = None
    frame_delta: list[float] = []
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % args.sample_every:
            index += 1
            continue
        sampled += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        if previous_gray is not None:
            frame_delta.append(float(np.mean(cv2.absdiff(gray, previous_gray))) / 255.0)
        previous_gray = gray
        faces = detector.get(frame)
        if faces:
            face = max(faces, key=lambda item: item.bbox[2] - item.bbox[0])
            similarities.append(cosine(reference_face.normed_embedding, face.normed_embedding))
            height, width = frame.shape[:2]
            x1, y1, x2, y2 = face.bbox
            centers.append(((x1 + x2) / (2 * width), (y1 + y2) / (2 * height)))
            areas.append(float((x2 - x1) * (y2 - y1) / (width * height)))
        index += 1
    capture.release()

    center_array = np.asarray(centers) if centers else np.empty((0, 2))
    result = {
        "schema_version": 1,
        "video": str(Path(args.video).resolve()),
        "reference": str(Path(args.reference).resolve()),
        "fps": fps,
        "total_frames": total_frames,
        "sample_every_frames": args.sample_every,
        "sampled_frames": sampled,
        "face_detection_rate": len(similarities) / sampled if sampled else 0.0,
        "identity_cosine_mean": float(np.mean(similarities)) if similarities else None,
        "identity_cosine_min": float(np.min(similarities)) if similarities else None,
        "face_center_std": center_array.std(axis=0).tolist() if len(center_array) else None,
        "face_area_mean": float(np.mean(areas)) if areas else None,
        "face_area_relative_std": float(np.std(areas) / np.mean(areas)) if areas else None,
        "sharpness_laplacian_mean": float(np.mean(sharpness)) if sharpness else None,
        "sampled_frame_delta_mean": float(np.mean(frame_delta)) if frame_delta else None,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
