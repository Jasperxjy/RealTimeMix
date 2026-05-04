#!/usr/bin/env python3
"""Block permutation scrambler/descrambler."""
import random
import numpy as np
import cv2
from seed import Seed


def _get_perm(width: int, height: int, block_size: int, seed_val: int):
    cols = width // block_size
    rows = height // block_size
    n = cols * rows
    perm = list(range(n))
    rng = random.Random(seed_val)
    rng.shuffle(perm)
    return perm, cols, rows


def scramble_image(img: np.ndarray, seed: Seed) -> np.ndarray:
    bs = seed.block_size
    h, w = img.shape[:2]
    cols = w // bs
    rows = h // bs
    if cols == 0 or rows == 0:
        return img.copy()
    perm, cols, rows = _get_perm(w, h, bs, seed.seed)
    dst = np.zeros_like(img)
    for r in range(rows):
        for c in range(cols):
            src_idx = r * cols + c
            dst_idx = perm[src_idx]
            dst_r = dst_idx // cols
            dst_c = dst_idx % cols
            dst[dst_r*bs:(dst_r+1)*bs, dst_c*bs:(dst_c+1)*bs] = img[r*bs:(r+1)*bs, c*bs:(c+1)*bs]
    # edges
    full_h = rows * bs
    full_w = cols * bs
    if full_h < h:
        dst[full_h:h, 0:full_w] = img[full_h:h, 0:full_w]
    if full_w < w:
        dst[0:full_h, full_w:w] = img[0:full_h, full_w:w]
    if full_h < h and full_w < w:
        dst[full_h:h, full_w:w] = img[full_h:h, full_w:w]
    return dst


def descramble_image(img: np.ndarray, seed: Seed) -> np.ndarray:
    bs = seed.block_size
    h, w = img.shape[:2]
    cols = w // bs
    rows = h // bs
    if cols == 0 or rows == 0:
        return img.copy()
    perm, cols, rows = _get_perm(w, h, bs, seed.seed)
    dst = np.zeros_like(img)
    for r in range(rows):
        for c in range(cols):
            dst_idx = r * cols + c
            src_idx = perm[dst_idx]  # scrambled[forward[i]] = original[i], so original[i] = scrambled[forward[i]]
            src_r = src_idx // cols
            src_c = src_idx % cols
            dst[r*bs:(r+1)*bs, c*bs:(c+1)*bs] = img[src_r*bs:(src_r+1)*bs, src_c*bs:(src_c+1)*bs]
    full_h = rows * bs
    full_w = cols * bs
    if full_h < h:
        dst[full_h:h, 0:full_w] = img[full_h:h, 0:full_w]
    if full_w < w:
        dst[0:full_h, full_w:w] = img[0:full_h, full_w:w]
    if full_h < h and full_w < w:
        dst[full_h:h, full_w:w] = img[full_h:h, full_w:w]
    return dst


def scramble_video(input_path: str, output_path: str, seed: Seed, progress_callback=None) -> bool:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return False
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    if not writer.isOpened():
        cap.release()
        return False
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.ndim == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        out = scramble_image(frame, seed)
        writer.write(out)
        frame_idx += 1
        if progress_callback:
            progress_callback(int(100 * frame_idx / max(total, 1)))
    cap.release()
    writer.release()
    return True
