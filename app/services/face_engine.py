# Loads InsightFace model
# Detect face
# Generate embedding
# Output 512-dimensional vector

import cv2
import numpy as np
from insightface.app import FaceAnalysis


class FaceEngine():

    def __init__(self,):
        """
        Initialize InsightFace model
        """

        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        self.app.prepare(ctx_id=0)
        print("Face Engine Loaded Successfully")

    
    def get_embedding(self, image_path):
        """
        Detect face and generate embedding
        """

        # Read image
        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Detect faces
        faces = self.app.get(image)

        # No face found
        if len(faces) == 0:
            return None
        
        # Take first face
        face = faces[0]

        # get embedding vector
        embedding = face.embedding

        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding
