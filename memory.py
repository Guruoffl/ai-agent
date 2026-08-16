import json
import os

import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer


MEMORY_FILE = "memory.json"
MODEL_NAME = "all-MiniLM-L6-v2"

SIMILARITY_THRESHOLD = 0.25

model = SentenceTransformer(MODEL_NAME)



def load_memories():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


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



def create_embedding(text):

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()



def remember(content):

    content = str(content).strip()

    if not content:
        return "Memory content is empty."

    memories = load_memories()

    for memory in memories:

        if not isinstance(memory, dict):
            continue

        if memory.get("content") == content:

            if not memory.get("embedding"):

                memory["embedding"] = create_embedding(
                    content
                )

                save_memories(memories)

            return "Memory already exists."

    embedding = create_embedding(
        content
    )

    memory = {

        "content":
            content,

        "embedding":
            embedding,

        "created_at":
            datetime.now().isoformat()

    }

    memories.append(memory)

    save_memories(memories)

    return "Memory saved successfully."



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

    memory_file_changed = False

    for memory in memories:

        if not isinstance(memory, dict):
            continue

        content = memory.get("content")

        if not content:
            continue

        embedding = memory.get("embedding")

        if not embedding:

            print(
                f"[Repairing memory embedding: {content}]"
            )

            embedding = create_embedding(
                content
            )

            memory["embedding"] = embedding

            memory_file_changed = True


        try:

            memory_embedding = np.array(
                embedding
            )

        except Exception:

            continue

        

        if (
            memory_embedding.ndim != 1
            or
            memory_embedding.shape !=
            query_embedding.shape
        ):

            print(
                f"[Rebuilding invalid embedding: {content}]"
            )

            memory_embedding = np.array(
                create_embedding(content)
            )

            memory["embedding"] = (
                memory_embedding.tolist()
            )

            memory_file_changed = True

        score = np.dot(
            query_embedding,
            memory_embedding
        )

        scored_memories.append({

            "content":
                content,

            "score":
                float(score),

            "created_at":
                memory.get(
                    "created_at",
                    ""
                )

        })


    if memory_file_changed:

        save_memories(
            memories
        )

        print(
            "[Memory database repaired.]"
        )


    scored_memories.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    relevant = [

        memory

        for memory
        in scored_memories[:top_k]

        if memory["score"] >=
        SIMILARITY_THRESHOLD

    ]

    if not relevant:

        return "No relevant memories found."

    return relevant