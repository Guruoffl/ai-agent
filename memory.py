import json
import os

import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer


MEMORY_FILE = "memory.json"

MODEL_NAME = "all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


# -----------------------------
# Load memories
# -----------------------------

def load_memories():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


# -----------------------------
# Save memories
# -----------------------------

def save_memories(memories):

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memories,
            file,
            indent=2,
            ensure_ascii=False
        )


# -----------------------------
# Create embedding
# -----------------------------

def create_embedding(text):

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


# -----------------------------
# Remember
# -----------------------------

def remember(content):

    memories = load_memories()

    embedding = create_embedding(
        content
    )

    memory = {
        "content": content,
        "embedding": embedding,
        "created_at": datetime.now().isoformat()
    }

    memories.append(memory)

    save_memories(memories)

    return "Memory saved successfully."


# -----------------------------
# Semantic Memory Search
# -----------------------------

def search_memories(
    query,
    top_k=5
):

    memories = load_memories()

    if not memories:

        return "No memories stored yet."


    query_embedding = np.array(
        create_embedding(query)
    )


    scored_memories = []


    for memory in memories:

        memory_embedding = np.array(
            memory["embedding"]
        )


        # Cosine similarity
        score = np.dot(
            query_embedding,
            memory_embedding
        )


        scored_memories.append({

            "content":
                memory["content"],

            "score":
                float(score),

            "created_at":
                memory["created_at"]

        })


    scored_memories.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    # Only return reasonably relevant memories
    relevant = [
        memory
        for memory in scored_memories[:top_k]
        if memory["score"] >= 0.35
    ]


    if not relevant:

        return "No relevant memories found."


    return relevant