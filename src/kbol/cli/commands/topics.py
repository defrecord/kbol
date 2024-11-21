import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import json
import numpy as np
from collections import Counter
from typing import List, Dict
import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

console = Console()


@dataclass
class TopicSummary:
    name: str
    documents: List[str]
    key_terms: List[str]
    chunk_count: int
    total_tokens: int


def analyze_topics(chunks: List[Dict], n_clusters: int = 10) -> List[TopicSummary]:
    """Analyze topics in the chunks using TF-IDF and clustering."""
    # Extract text content
    texts = [chunk["content"] for chunk in chunks]

    # Create TF-IDF matrix
    vectorizer = TfidfVectorizer(
        max_features=1000, stop_words="english", ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Cluster documents
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(tfidf_matrix)

    # Get feature names
    feature_names = vectorizer.get_feature_names_out()

    # Analyze each cluster
    topics = []
    for i in range(n_clusters):
        cluster_docs = [doc for doc, cluster in zip(chunks, clusters) if cluster == i]
        if not cluster_docs:
            continue

        # Get top terms for cluster
        cluster_center = kmeans.cluster_centers_[i]
        top_term_indices = np.argsort(cluster_center)[-5:][::-1]
        key_terms = [feature_names[idx] for idx in top_term_indices]

        # Get unique documents in cluster
        unique_docs = set(doc["book"] for doc in cluster_docs)

        topics.append(
            TopicSummary(
                name=f"Topic {i+1}: {key_terms[0]}",
                documents=sorted(unique_docs),
                key_terms=key_terms,
                chunk_count=len(cluster_docs),
                total_tokens=sum(doc["token_count"] for doc in cluster_docs),
            )
        )

    return topics


def register(app: typer.Typer):
    @app.command()
    def topics(
        n_clusters: int = typer.Option(
            10, "--clusters", "-n", help="Number of topics to identify"
        ),
        min_chunks: int = typer.Option(
            5, "--min-chunks", help="Minimum chunks per topic to display"
        ),
    ):
        """Analyze topics and clusters in the knowledge base."""
        processed_dir = Path("data/processed")

        if not processed_dir.exists() or not list(processed_dir.glob("*.json")):
            console.print(
                "[yellow]No processed books found. Run 'kbol process' first.[/yellow]"
            )
            return

        # Load all chunks
        all_chunks = []
        for json_file in processed_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
            except Exception as e:
                console.print(f"[red]Error reading {json_file.name}: {e}[/red]")

        if not all_chunks:
            console.print("[yellow]No chunks found in processed files.[/yellow]")
            return

        # Analyze topics
        topics = analyze_topics(all_chunks, n_clusters)

        # Filter and sort topics
        topics = [t for t in topics if t.chunk_count >= min_chunks]
        topics.sort(key=lambda x: x.chunk_count, reverse=True)

        # Display results
        console.print(f"\n[bold cyan]Found {len(topics)} major topics:[/bold cyan]\n")

        for topic in topics:
            console.print(
                Panel(
                    f"[bold]{topic.name}[/bold]\n\n"
                    f"Key terms: {', '.join(topic.key_terms)}\n\n"
                    f"Documents ({len(topic.documents)}):\n"
                    + "\n".join(f"• {doc}" for doc in topic.documents)
                    + f"\n\nChunks: {topic.chunk_count:,} | Tokens: {topic.total_tokens:,}",
                    border_style="blue",
                )
            )

        # Print co-occurrence matrix
        table = Table(title="Topic Co-occurrence")
        table.add_column("Topic", style="cyan")
        for t in topics[:5]:  # Show top 5 topics
            table.add_column(t.name.split(":")[0], justify="right")

        for t1 in topics[:5]:
            row = [t1.name.split(":")[0]]
            for t2 in topics[:5]:
                common_docs = len(set(t1.documents) & set(t2.documents))
                row.append(str(common_docs))
            table.add_row(*row)

        console.print("\n", table)


if __name__ == "__main__":
    app = typer.Typer()
    register(app)
    app()
