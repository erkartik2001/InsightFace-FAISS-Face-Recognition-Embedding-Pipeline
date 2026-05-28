import pickle
import numpy as np
import faiss
import os

import app.app_state as app_state


class FaceMatcher:

    def __init__(
        self,
        faiss_index_path="faiss_index/face_engine.index",
        mapping_path="faiss_index/image_mapping.pkl"
    ):


        self.engine = app_state.face_engine
        self.storage = app_state.b2_storage

        if os.path.exists(faiss_index_path):

            self.index = faiss.read_index(
                faiss_index_path
            )

            print("FAISS index loaded")

        else:

            self.index = None

            print("No FAISS index found")


        if os.path.exists(mapping_path):

            with open(mapping_path, "rb") as f:

                self.image_mapping = pickle.load(f)

            print("Image mappings loaded")

        else:

            self.image_mapping = {}

            print("No image mappings found")



    def search(
        self,
        image_path,
        top_k=5,
        threshold=0.5
    ):
        
         # -----------------------------
         # CHECK INDEX
         # -----------------------------

        if self.index is None:

            return {
                "success": False,
                "message": "No indexed faces found"
            }
            


        # Generate embedding
        embedding = self.engine.get_embedding(image_path)

        if embedding is None:
            print("None is there")
            return []

        query_embedding = np.array([embedding]).astype("float32")

        # Search FAISS
        similarities, indices = self.index.search(
            query_embedding,
            top_k
        )

        results = []

        for similarity, idx in zip(
            similarities[0],
            indices[0]
        ):

            if similarity < threshold:
                continue

            matched_data = self.image_mapping[idx]

            file_name = matched_data["file_name"]
            bucket_name = matched_data.get("bucket_name")

            file_url = self.storage.generate_file_url(
                file_name, bucket_name
            )
            show_file_url = self.storage.generate_file_url_show(
                file_name, bucket_name
            )

            results.append({
                "file_name": file_name,
                "file_url": file_url,
                "show_file_url": show_file_url,
                "similarity": float(similarity),
                "bucket_name": bucket_name or self.storage.bucket_name
            })
        return results
    

    def add_face(
        self,
        embedding,
        file_name,
        file_url
    ):

        # Convert embedding
        embedding = np.array(
            [embedding]
        ).astype("float32")




        # -----------------------------
        # CREATE FAISS IF FIRST VECTOR
        # -----------------------------

        if self.index is None:

            dimension = embedding.shape[1]

            self.index = faiss.IndexFlatIP(
                dimension
            )

            print("New FAISS index created")


        # -----------------------------
        # ADD EMBEDDING
        # -----------------------------

        # Add to FAISS
        self.index.add(embedding)


        # New vector ID
        new_id = len(self.image_mapping)


        # Update mapping
        self.image_mapping[new_id] = {
            "file_name": file_name,
            "file_url": file_url
        }


        # Save updated FAISS index
        faiss.write_index(
            self.index,
            "faiss_index/face_engine.index"
        )


        # Save updated mappings
        with open(
            "faiss_index/image_mapping.pkl",
            "wb"
        ) as f:

            pickle.dump(
                self.image_mapping,
                f
            )

        return True
