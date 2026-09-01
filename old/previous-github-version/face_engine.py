"""
AI-CCTV Biometric Facial Recognition Engine
Al Noor Factory for Solar Panels
Using OpenCV YuNet (Ultra-Fast CNN Face Detector) & SFace (Deep Metric Learning Embeddings)
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

YUNET_ONNX = MODELS_DIR / "face_detection_yunet.onnx"
SFACE_ONNX = MODELS_DIR / "face_recognition_sface.onnx"

class FaceEngine:
    def __init__(self):
        self.detector = None
        self.recognizer = None
        self.is_ready = False
        self._init_models()

    def _init_models(self):
        if not YUNET_ONNX.exists() or not SFACE_ONNX.exists():
            print("[FACE ENGINE] Warning: Face models not found in models/ directory.")
            return

        try:
            # Initialize YuNet Face Detector (Score threshold=0.6, NMS threshold=0.3)
            self.detector = cv2.FaceDetectorYN.create(
                str(YUNET_ONNX),
                "",
                (320, 320),
                0.6,
                0.3,
                5000
            )
            # Initialize SFace Deep Metric Feature Recognizer
            self.recognizer = cv2.FaceRecognizerSF.create(
                str(SFACE_ONNX),
                ""
            )
            self.is_ready = True
            print("[FACE ENGINE] YuNet & SFace Biometric Models initialized successfully.")
        except Exception as e:
            print(f"[FACE ENGINE] Error initializing face models: {e}")

    def extract_face_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detects primary face in image, aligns facial landmarks, and returns 128-D L2-normalized float embedding.
        """
        if not self.is_ready or image is None or image.size == 0:
            return None

        h, w = image.shape[:2]
        self.detector.setInputSize((w, h))

        try:
            _, faces = self.detector.detect(image)
            if faces is None or len(faces) == 0:
                return None

            # Get the highest confidence face (sorted by score)
            primary_face = faces[0]

            # Align and extract embedding
            aligned_face = self.recognizer.alignCrop(image, primary_face)
            embedding = self.recognizer.feature(aligned_face)
            
            # Ensure 1D float32 normalized array
            embedding = embedding.flatten().astype(np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding
        except Exception as e:
            print(f"[FACE ENGINE] Error extracting embedding: {e}")
            return None

    def match_face(
        self,
        query_embedding: np.ndarray,
        known_roster: List[Tuple[int, str, str, Optional[str], np.ndarray]],
        threshold: float = 0.50
    ) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[str], float]:
        """
        Compares query_embedding against known_roster using Cosine Similarity.
        known_roster: list of (emp_id, full_name, emp_code, assigned_zone, embedding_np)
        Returns: (emp_id, full_name, emp_code, assigned_zone, similarity_score)
        """
        if query_embedding is None or not known_roster:
            return None, None, None, None, 0.0

        best_score = -1.0
        best_match = (None, None, None, None, 0.0)

        for emp_id, name, code, assigned_zone, known_emb in known_roster:
            if known_emb is None or len(known_emb) != len(query_embedding):
                continue
            # Cosine similarity: dot product of normalized vectors
            sim = float(np.dot(query_embedding, known_emb))
            if sim > best_score:
                best_score = sim
                if sim >= threshold:
                    best_match = (emp_id, name, code, assigned_zone, sim)

        return best_match

    def detect_and_recognize_person_crop(
        self,
        person_crop: np.ndarray,
        known_roster: list,
        threshold: float = 0.50
    ) -> Tuple[Optional[str], Optional[str], Optional[str], float]:
        """
        Takes a person bounding box crop, crops upper body region for face, and attempts recognition.
        Returns: (full_name, emp_code, assigned_zone, confidence)
        """
        if not self.is_ready or person_crop is None or person_crop.size == 0 or not known_roster:
            return None, None, None, 0.0

        h, w = person_crop.shape[:2]
        # Focus on upper 60% of person box where face is located
        upper_body = person_crop[0:int(h * 0.60), :]
        if upper_body.size == 0:
            return None, None, None, 0.0

        emb = self.extract_face_embedding(upper_body)
        if emb is None:
            return None, None, None, 0.0

        _, name, code, zone, score = self.match_face(emb, known_roster, threshold=threshold)
        return name, code, zone, score

GLOBAL_FACE_ENGINE = FaceEngine()
