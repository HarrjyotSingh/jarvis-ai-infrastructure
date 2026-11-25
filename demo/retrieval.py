"""Run a repeatable incremental-indexing walkthrough with synthetic notes."""

import hashlib
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

import chromadb
from chromadb.api.models.Collection import Collection


def connect() -> chromadb.ClientAPI:
    host = os.environ.get("CHROMA_HOST", "localhost")
    for attempt in range(15):
        try:
            return chromadb.HttpClient(host=host, port=8000)
        except (ValueError, ConnectionError):
            if attempt == 14:
                raise
            time.sleep(2)
    raise RuntimeError("Could not connect to Chroma")


def sync_notes(collection: Collection, notes_dir: Path) -> tuple[int, int]:
    stored = collection.get(include=["metadatas"])
    stored_hashes = {
        note_id: metadata["sha256"]
        for note_id, metadata in zip(stored["ids"], stored["metadatas"], strict=True)
    }

    files = {path.name: path for path in sorted(notes_dir.glob("*.md"))}
    changed_ids = []
    changed_documents = []
    changed_metadata = []
    for note_id, path in files.items():
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if stored_hashes.get(note_id) != digest:
            changed_ids.append(note_id)
            changed_documents.append(content.decode("utf-8"))
            changed_metadata.append({"sha256": digest})

    if changed_ids:
        collection.upsert(
            ids=changed_ids, documents=changed_documents, metadatas=changed_metadata
        )

    removed_ids = sorted(stored_hashes.keys() - files.keys())
    if removed_ids:
        collection.delete(ids=removed_ids)

    return len(changed_ids), len(removed_ids)


def retrieve_greenhouse_note(collection: Collection, expected_material: str) -> None:
    matches = collection.query(
        query_texts=["Which sprinkler nozzle material is used for greenhouse irrigation?"],
        n_results=1,
        include=["documents"],
    )
    note_id = matches["ids"][0][0]
    document = matches["documents"][0][0]
    assert note_id == "greenhouse.md" and expected_material in document
    print(f"Top match: {note_id}. {document.splitlines()[2]}")


def run_demo() -> None:
    client = connect()
    collection_name = f"demo-{uuid4().hex}"
    collection = client.create_collection(collection_name)
    try:
        with TemporaryDirectory() as scratch:
            notes_dir = Path(scratch) / "notes"
            shutil.copytree(Path(__file__).with_name("notes"), notes_dir)

            indexed, removed = sync_notes(collection, notes_dir)
            assert (indexed, removed) == (3, 0)
            print(f"First sync: {indexed} notes indexed.")
            retrieve_greenhouse_note(collection, "brass")

            indexed, removed = sync_notes(collection, notes_dir)
            assert (indexed, removed) == (0, 0)
            print(f"Unchanged sync: {indexed} notes indexed.")

            greenhouse = notes_dir / "greenhouse.md"
            updated = greenhouse.read_text(encoding="utf-8").replace("brass", "stainless steel")
            greenhouse.write_text(updated, encoding="utf-8")
            indexed, removed = sync_notes(collection, notes_dir)
            assert (indexed, removed) == (1, 0)
            print(f"After the edit: {indexed} note reindexed.")
            retrieve_greenhouse_note(collection, "stainless steel")

            (notes_dir / "route.md").unlink()
            indexed, removed = sync_notes(collection, notes_dir)
            assert (indexed, removed, collection.count()) == (0, 1, 2)
            print(f"After the deletion: {removed} note removed from the index.")
    finally:
        client.delete_collection(collection_name)


if __name__ == "__main__":
    run_demo()
