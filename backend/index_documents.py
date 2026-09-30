import asyncio
import sys
from pathlib import Path
from rag import add_document
import uuid

async def index_folder(folder_path: str):
    folder = Path(folder_path)
    files = list(folder.glob("**/*.md")) + list(folder.glob("**/*.txt"))

    if not files:
        print(f"No se encontraron archivos .md o .txt en {folder_path}")
        return

    for file in files:
        text = file.read_text(encoding="utf-8")
        doc_id = str(uuid.uuid4())
        await add_document(doc_id, text, {"source": file.name, "path": str(file)})
        print(f"✓ Indexado: {file.name}")

    print(f"\nTotal: {len(files)} documentos indexados")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python index_documents.py /ruta/a/carpeta")
        sys.exit(1)
    asyncio.run(index_folder(sys.argv[1]))
