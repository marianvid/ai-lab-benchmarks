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
    """Cosine similarity of two vectors, 0 when either is zero."""
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    return float(np.dot(left, right) / denominator) if denominator else 0.0


# The brightest 8-bit pixel: frame differences are reported as a fraction of it.
MAX_LEVEL = 255.0


def largest(faces: list):
    """The widest face found."""
    return max(faces, key=lambda face: face.bbox[2] - face.bbox[0])


def mean_or_none(values: list[float]) -> float | None:
    """The mean, or None for no values."""
    return float(np.mean(values)) if values else None


def sampled_frames(capture, every: int):
    """Every `every`-th frame of the video."""
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            return
        if index % every == 0:
            yield frame
        index += 1


class Track:
    """What the sampled frames showed: the face, its place, sharpness and motion."""

    def __init__(self, detector, reference_face) -> None:
        self.detector = detector
        self.reference_face = reference_face
        self.similarities: list[float] = []
        self.centers: list[tuple[float, float]] = []
        self.areas: list[float] = []
        self.sharpness: list[float] = []
        self.frame_delta: list[float] = []
        self.sampled = 0
        self.previous_gray = None

    def add(self, frame) -> None:
        """Measure one sampled frame."""
        self.sampled += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        if self.previous_gray is not None:
            self.frame_delta.append(
                float(np.mean(cv2.absdiff(gray, self.previous_gray))) / MAX_LEVEL)
        self.previous_gray = gray
        faces = self.detector.get(frame)
        if faces:
            self.face(frame, largest(faces))

    def face(self, frame, face) -> None:
        """Record the face found in one frame."""
        self.similarities.append(cosine(self.reference_face.normed_embedding,
                                        face.normed_embedding))
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = face.bbox
        self.centers.append(((x1 + x2) / (2 * width), (y1 + y2) / (2 * height)))
        self.areas.append(float((x2 - x1) * (y2 - y1) / (width * height)))

    def summary(self) -> dict:
        """The measurements over every sampled frame."""
        similarities, areas = self.similarities, self.areas
        center_array = np.asarray(self.centers) if self.centers else np.empty((0, 2))
        return {
            "sampled_frames": self.sampled,
            "face_detection_rate": len(similarities) / self.sampled if self.sampled else 0.0,
            "identity_cosine_mean": mean_or_none(similarities),
            "identity_cosine_min": float(np.min(similarities)) if similarities else None,
            "face_center_std": center_array.std(axis=0).tolist() if len(center_array) else None,
            "face_area_mean": mean_or_none(areas),
            "face_area_relative_std": float(np.std(areas) / np.mean(areas)) if areas else None,
            "sharpness_laplacian_mean": mean_or_none(self.sharpness),
            "sampled_frame_delta_mean": mean_or_none(self.frame_delta),
        }


def reference_face(detector, path: str):
    """The largest face in the reference image."""
    faces = detector.get(cv2.imread(path))
    if not faces:
        raise RuntimeError("no face detected in the reference image")
    return largest(faces)


def main() -> int:
    """Measure identity stability and motion in every generated video."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-every", type=int, default=5)
    args = parser.parse_args()

    detector = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    detector.prepare(ctx_id=-1, det_size=(640, 640))
    track = Track(detector, reference_face(detector, args.reference))

    capture = cv2.VideoCapture(args.video)
    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    for frame in sampled_frames(capture, args.sample_every):
        track.add(frame)
    capture.release()

    result = {
        "schema_version": 1,
        "video": str(Path(args.video).resolve()),
        "reference": str(Path(args.reference).resolve()),
        "fps": fps,
        "total_frames": total_frames,
        "sample_every_frames": args.sample_every,
        **track.summary(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
