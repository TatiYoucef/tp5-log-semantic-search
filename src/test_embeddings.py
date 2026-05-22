from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

sentences = [
    "critical disk failure on node 4",
    "disk error detected on server node",
    "user logged in successfully"
]

embeddings = model.encode(sentences, normalize_embeddings=True)

print("Embedding shape:", embeddings.shape)
print("First vector length:", len(embeddings[0]))
