#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, subprocess, os, re
from pathlib import Path

# --- Instala bibliotecas se necessário (robusto) ---
def ensure_package(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", pkg])
            __import__(pkg)
            return True
        except Exception as e:
            print(f"Falha ao instalar {pkg}: {e}")
            return False

# Tentamos pypdf; se falhar, PyPDF2 como fallback
have_pypdf = ensure_package("pypdf")
if have_pypdf:
    from pypdf import PdfReader, PdfWriter
else:
    ensure_package("PyPDF2")
    from PyPDF2 import PdfReader, PdfWriter  # type: ignore

ensure_package("pdfplumber")  # usado para extrações mais ricas, se necessário

# --- Funções utilitárias ---
def unique_path(path: Path) -> Path:
    """Gera nome único ' (2)', ' (3)' se já existir."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 2
    while True:
        cand = parent / f"{stem} ({n}){suffix}"
        if not cand.exists():
            return cand
        n += 1

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

# --- Separação (versão simples por página; ajuste à sua necessidade) ---
def separar_mandados(arquivo_pdf: Path, pasta_destino: Path):
    pasta_destino = ensure_dir(pasta_destino)
    nome_base = arquivo_pdf.stem

    try:
        reader = PdfReader(str(arquivo_pdf))
    except Exception as e:
        print(f"❌ Erro ao ler PDF {arquivo_pdf}: {e}")
        return

    for i, page in enumerate(reader.pages, start=1):
        # Exemplo de heurística simples de nome
        texto = ""
        try:
            texto = page.extract_text() or ""
        except Exception:
            pass

        m = re.search(r"(MANDADO\s+\d+)", texto, flags=re.IGNORECASE)
        nome_subpasta = m.group(1).upper().replace(" ", "_") if m else f"{nome_base}_PAG_{i:03d}"

        pasta_mandado = ensure_dir(pasta_destino / nome_subpasta)
        out_pdf = unique_path(pasta_mandado / f"{nome_base}_pag{i:03d}.pdf")

        writer = PdfWriter()
        writer.add_page(page)
        with open(out_pdf, "wb") as f:
            writer.write(f)

        print(f"✅ Página {i} salva em: {out_pdf}")

# --- Execução principal ---
def main():
    if len(sys.argv) < 2:
        print("Uso: separador_mandados.py <arquivo_ou_pasta>")
        sys.exit(1)

    entrada = Path(sys.argv[1]).expanduser()
    destino = Path.home() / "Documents" / "Mandados Separados"

    if entrada.is_dir():
        pdfs = sorted([p for p in entrada.glob("*.pdf")])
        if not pdfs:
            print(f"ℹ️ Nenhum PDF em {entrada}")
        for item in pdfs:
            separar_mandados(item, destino)
    elif entrada.is_file() and entrada.suffix.lower() == ".pdf":
        separar_mandados(entrada, destino)
    else:
        print(f"❌ Tipo de entrada inválido: {entrada}")
        sys.exit(2)

if __name__ == "__main__":
    main()
