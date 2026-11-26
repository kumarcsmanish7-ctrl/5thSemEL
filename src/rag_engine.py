"""
RAG (Retrieval-Augmented Generation) Security Assistance Engine.
Extracts knowledge base guidelines, indexes them into vector storage (ChromaDB),
performs semantic similarity retrieval, and synthesizes structured incident mitigation
recommendations for CCTV surveillance & SDN security operators.
"""
import os
import glob
import hashlib
import importlib.util
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import KNOWLEDGE_BASE_DIR, CHROMA_PERSIST_DIR

# Check optional libraries
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

SENTENCE_TRANSFORMER_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class DocumentChunk:
    def __init__(self, doc_id: str, title: str, section: str, content: str, source_file: str):
        self.doc_id = doc_id
        self.title = title
        self.section = section
        self.content = content
        self.source_file = source_file

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "section": self.section,
            "content": self.content,
            "source_file": self.source_file
        }


class RAGSecurityEngine:
    def __init__(self, kb_dir: Optional[Path] = None, chroma_dir: Optional[Path] = None):
        self.kb_dir = kb_dir or KNOWLEDGE_BASE_DIR
        self.chroma_dir = chroma_dir or CHROMA_PERSIST_DIR
        self.chunks: List[DocumentChunk] = []
        self.use_chroma = False
        self.retrieval_backend = "TF-IDF"

        # Fallback Vector Store Components
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None

        self._load_and_chunk_documents()
        self._initialize_vector_store()

    def _load_and_chunk_documents(self):
        """Loads and breaks knowledge base markdown files into smaller semantic chunks."""
        self.chunks = []
        kb_files = glob.glob(str(self.kb_dir / "*.md")) + glob.glob(str(self.kb_dir / "*.txt"))
        
        chunk_idx = 0
        for file_path in kb_files:
            file_name = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # Split by markdown headers (# and ##)
            sections = raw_text.split("\n## ")
            title = sections[0].split("\n")[0].replace("#", "").strip() if sections else file_name

            for i, section_text in enumerate(sections):
                lines = section_text.strip().split("\n")
                section_title = lines[0].replace("#", "").strip() if lines else f"Section {i+1}"
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else section_text.strip()

                if len(body) < 30:
                    continue

                # If body is long, split into paragraphs
                sub_chunks = body.split("\n\n")
                for sub in sub_chunks:
                    clean_text = sub.strip()
                    if len(clean_text) > 40:
                        chunk_idx += 1
                        chunk = DocumentChunk(
                            doc_id=f"chunk_{chunk_idx}",
                            title=title,
                            section=section_title,
                            content=clean_text,
                            source_file=file_name
                        )
                        self.chunks.append(chunk)

    def _initialize_vector_store(self):
        """Initializes ChromaDB collection or sets up TF-IDF dense vector space."""
        if not self.chunks:
            return

        texts = [f"{c.title} - {c.section}: {c.content}" for c in self.chunks]

        # 1. Always build the TF-IDF matrix as a bulletproof instant fallback
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

        if not CHROMA_AVAILABLE:
            return

        try:
            self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        except Exception as exc:
            logger.warning("ChromaDB unavailable; using in-memory TF-IDF retrieval: %s", exc)
            return

        allow_model_download = os.getenv("RAG_ALLOW_MODEL_DOWNLOAD", "").lower() in {
            "1", "true", "yes"
        }
        hf_hub_cache = Path(os.getenv(
            "HF_HUB_CACHE",
            str(Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub")
        ))
        model_snapshots = (
            hf_hub_cache
            / "models--sentence-transformers--all-MiniLM-L6-v2"
            / "snapshots"
        )
        model_is_cached = any(
            (snapshot / weight_file).is_file()
            for snapshot in model_snapshots.glob("*")
            for weight_file in ("model.safetensors", "pytorch_model.bin")
        )

        if SENTENCE_TRANSFORMER_AVAILABLE and (allow_model_download or model_is_cached):
            try:
                from chromadb.utils import embedding_functions

                self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2",
                    **({"local_files_only": True} if not allow_model_download else {})
                )
                self.collection = self.client.get_or_create_collection(
                    name="cctv_security_knowledge_minilm",
                    embedding_function=self.embed_fn,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collection.upsert(
                    ids=[c.doc_id for c in self.chunks],
                    documents=texts,
                    metadatas=[
                        {"title": c.title, "section": c.section, "source_file": c.source_file}
                        for c in self.chunks
                    ]
                )
                self.use_chroma = True
                self.retrieval_backend = "ChromaDB + Sentence Transformers"
                return
            except Exception as exc:
                logger.warning(
                    "Sentence Transformer embeddings unavailable; using TF-IDF vectors: %s",
                    exc
                )

        try:
            corpus_signature = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:12]
            self.collection = self.client.get_or_create_collection(
                name=f"cctv_security_tfidf_{corpus_signature}",
                metadata={"hnsw:space": "cosine"}
            )
            self.collection.upsert(
                ids=[c.doc_id for c in self.chunks],
                documents=texts,
                embeddings=self.tfidf_matrix.toarray().tolist(),
                metadatas=[
                    {"title": c.title, "section": c.section, "source_file": c.source_file}
                    for c in self.chunks
                ]
            )
            self.use_chroma = True
            self.retrieval_backend = "ChromaDB + TF-IDF fallback"
        except Exception as fallback_exc:
            logger.warning(
                "ChromaDB TF-IDF indexing unavailable; using in-memory TF-IDF retrieval: %s",
                fallback_exc
            )
            self.use_chroma = False

    def retrieve_context(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most semantically relevant document chunks for an alert or query.
        """
        if not self.chunks:
            return []

        # If Chroma is active, use Chroma vector similarity
        if self.use_chroma:
            try:
                query_args = {"n_results": min(top_k, len(self.chunks))}
                if self.retrieval_backend == "ChromaDB + TF-IDF fallback":
                    query_args["query_embeddings"] = self.tfidf_vectorizer.transform(
                        [query]
                    ).toarray().tolist()
                else:
                    query_args["query_texts"] = [query]
                results = self.collection.query(**query_args)
                retrieved = []
                for idx in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][idx]
                    chunk = next((c for c in self.chunks if c.doc_id == doc_id), None)
                    distance = results["distances"][0][idx] if "distances" in results and results["distances"] else 0.5
                    score = round(max(0.0, 1.0 - (distance / 2.0)), 3)
                    if chunk:
                        retrieved.append({
                            "chunk": chunk.to_dict(),
                            "similarity_score": score
                        })
                return retrieved
            except Exception as exc:
                logger.warning(
                    "ChromaDB query failed; switching to in-memory TF-IDF retrieval: %s",
                    exc
                )
                self.use_chroma = False
                self.retrieval_backend = "TF-IDF"

        # Fallback to TF-IDF Cosine Similarity
        query_vec = self.tfidf_vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = np.argsort(sim_scores)[::-1][:top_k]

        retrieved = []
        for idx in top_indices:
            score = round(float(sim_scores[idx]), 3)
            retrieved.append({
                "chunk": self.chunks[idx].to_dict(),
                "similarity_score": score
            })
        return retrieved

    def generate_mitigation_response(self, alert_data: Dict[str, Any], user_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Synthesizes a context-grounded response and actionable mitigation plan.
        Inputs can be video anomaly alerts or network attack alerts.
        """
        # Formulate query based on incident type
        alert_type = alert_data.get("alert_type") or alert_data.get("attack_status") or alert_data.get("status") or "Security Alert"
        severity = alert_data.get("severity", "HIGH")
        source = alert_data.get("source") or alert_data.get("camera_id") or alert_data.get("affected_switch") or "CCTV Network"
        details = alert_data.get("details", "")

        query = f"{alert_type} {details} CCTV network adaptive routing mitigation incident response"
        if user_query:
            query = f"{user_query} {query}"

        # Retrieve relevant knowledge chunks
        relevant_chunks = self.retrieve_context(query, top_k=3)

        # Build grounded recommendation
        threat_category = "Network / DDoS Attack" if ("DDOS" in str(alert_type).upper() or "FLOOD" in str(alert_type).upper()) else "Video / Physical Intrusion"
        
        if "DDOS" in str(alert_type).upper() or "FLOOD" in str(alert_type).upper():
            immediate_steps = [
                "Activate SDN Adaptive Rerouting via Modified Dijkstra to redirect RTSP video traffic away from congested/attacked switch.",
                "Deploy OpenFlow meter tables to rate-limit incoming malicious packets on ingress ports.",
                "Verify camera video stream continuity (FPS, Latency, and Packet Delivery Ratio) on alternate path.",
                "Quarantine suspicious IP subnets attempting high-volume SYN/UDP traffic."
            ]
            sdn_recommendation = "Reroute traffic: Move flows from primary path (SW-1 -> SW-2) to alternate backup path (SW-1 -> SW-3 -> SW-4) to restore < 20ms latency."
        else:
            immediate_steps = [
                "Verify video anomaly alert on frame buffer to differentiate genuine threat from false motion.",
                "Check cross-correlation with physical access control and gate badge logs.",
                "Issue automated perimeter deterrence (spotlight/audio advisory) if zone is marked restricted.",
                "Dispatch on-site security patrol to target camera sector coordinates."
            ]
            sdn_recommendation = "Preserve dedicated QoS bandwidth for target camera stream to ensure uninterrupted recording at maximum bit-rate."

        context_summary = "\n".join([
            f"- [{c['chunk']['source_file']}] {c['chunk']['section']}: {c['chunk']['content'][:180]}..."
            for c in relevant_chunks
        ])

        return {
            "incident_type": alert_type,
            "threat_category": threat_category,
            "severity": severity,
            "source_node": source,
            "retrieved_sources": list(dict.fromkeys(
                c["chunk"]["source_file"] for c in relevant_chunks
            )),
            "context_summary": context_summary,
            "immediate_actions": immediate_steps,
            "sdn_routing_guidance": sdn_recommendation,
            "post_incident_checklist": [
                "Archive flow statistics and frame timestamps for digital forensics.",
                "Audit IoT camera credentials and ensure latest firmware version is flashed.",
                "Reset routing topology to default path once traffic rate drops below threshold."
            ],
            "retrieved_chunks": relevant_chunks
        }
