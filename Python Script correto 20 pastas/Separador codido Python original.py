#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Separador de Mandados PJe — MODO SOMA/MERGE
- Cria/usa "Mandados Separados" ao lado do PDF (ou usa out_dir passado).
- Não sobrescreve: cria " (2)", " (3)" etc.
- Delimitação por ID (rodapé).
- Processo prioriza cabeçalho; em caso de rodapé duplicado, escolhe (hora,ID) cujo processo do rodapé = processo do cabeçalho.
- Destinatário: rótulos clássicos (primeiro que aparecer); não inclui endereço.
"""

import os, re, sys
from pathlib import Path
from collections import defaultdict

# ---------- Dependências ----------
try:
    import PyPDF2
except ImportError:
    os.system(f"{sys.executable} -m pip install --user PyPDF2")
    import PyPDF2

try:
    import pdfplumber
except ImportError:
    os.system(f"{sys.executable} -m pip install --user pdfplumber")
    import pdfplumber

# GUI só se rodar sem args
USE_GUI = False
try:
    if len(sys.argv) == 1:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        USE_GUI = True
except Exception:
    USE_GUI = False

PROC_RE = r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b"

# ---------- Helpers FS ----------
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True); return p

def _unique_file(p: Path) -> Path:
    c = p; n = 2
    while c.exists():
        c = p.with_name(f"{p.stem} ({n}){p.suffix}"); n += 1
    return c

# ---------- Extração ----------
def footer_candidates(texto: str):
    """
    Candidatos de rodapé: 'às HH:MM:SS - <hexid>' e,
    a seguir no mesmo bloco, 'Número do processo: <proc>'.
    Retorna [(hora, id_hex, processo_rodape_ou_None), ...]
    """
    cands = []
    for m in re.finditer(r"às (\d{2}:\d{2}:\d{2})\s*-\s*([a-f0-9]{5,})", texto, flags=re.IGNORECASE):
        hora = m.group(1)
        hid  = m.group(2)
        seg = texto[m.end(): m.end() + 600]  # “mesmo bloco”
        pm = re.search(rf"(?:Número do processo|N[º°]\s*do\s*processo|Processo):\s*({PROC_RE})",
                       seg, flags=re.IGNORECASE)
        proc = pm.group(1) if pm else None
        cands.append((hora, hid, proc))
    return cands

def pick_footer(cands, proc_header: str):
    """Se houver mais de um rodapé, escolhe o que tem processo igual ao do cabeçalho; senão, o primeiro."""
    if not cands:
        return None, None, None
    if proc_header and proc_header != "PROCESSO_NAO_ENCONTRADO":
        for h, hid, pr in cands:
            if pr == proc_header:
                return h, hid, pr
    return cands[0]

def extrair_processo_prioritario(texto: str) -> str:
    """Cabeçalho → rodapé → fallback no texto inteiro."""
    cab = "\n".join(texto.splitlines()[:20])
    patterns = [
        rf"AT(?:Sum|Ord|[A-Z]{{1,3}})\s+({PROC_RE})",
        rf"(?:Processo|PROCESSO|N[º°]\s*do\s*processo|Número do processo):\s*({PROC_RE})",
        rf"({PROC_RE})"
    ]
    for pat in patterns:
        m = re.search(pat, cab)
        if m:
            return m.group(1)

    # tenta achar no corpo/rodapé
    for pat in [
        rf"(?:Número do processo|N[º°]\s*do\s*processo|Processo):\s*({PROC_RE})",
    ]:
        m = re.search(pat, texto, flags=re.IGNORECASE)
        if m:
            return m.group(1)

    m = re.search(PROC_RE, texto)
    return m.group(0) if m else "PROCESSO_NAO_ENCONTRADO"

ROTULOS_DEST = [
    r"Destinatário:\s*([^\n\r]+)",  r"DESTINATÁRIO:\s*([^\n\r]+)",
    r"Destinatario:\s*([^\n\r]+)",  r"DESTINATARIO:\s*([^\n\r]+)",
    r"Reclamado:\s*([^\n\r]+)",     r"RECLAMADO:\s*([^\n\r]+)",
    r"Executado:\s*([^\n\r]+)",     r"EXECUTADO:\s*([^\n\r]+)",
    r"Réu:\s*([^\n\r]+)",           r"RÉU:\s*([^\n\r]+)",
    r"Requerido:\s*([^\n\r]+)",     r"REQUERIDO:\s*([^\n\r]+)",
    r"Para:\s*([^\n\r]+)",          r"PARA:\s*([^\n\r]+)",
]
def extrair_destinatario(texto: str) -> str:
    for pat in ROTULOS_DEST:
        m = re.search(pat, texto, flags=re.MULTILINE)
        if not m: continue
        bruto = m.group(1).strip()
        nome = re.split(r"[,\-–;|\n\r]", bruto, maxsplit=1)[0].strip()
        nome = re.sub(r"\s+(CPF|CNPJ|RG|ID)\b.*$", "", nome, flags=re.IGNORECASE).strip()
        nome = re.sub(r"^[^\wÁÉÍÓÚÂÊÔÃÕÇ]+", "", nome)
        nome = re.sub(r"[^\wÁÉÍÓÚÂÊÔÃÕÇ\s]+$", "", nome)
        nome = re.sub(r"\s+", " ", nome)
        if len(nome) >= 3 and re.search(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇà-ü]", nome):
            return nome
    return "DESTINATARIO_NAO_ENCONTRADO"

def extrair_mandados(caminho_pdf: str):
    itens = []
    with pdfplumber.open(caminho_pdf) as pdf:
        atual = None
        pags = []
        for i, pg in enumerate(pdf.pages):
            texto = pg.extract_text() or ""

            proc_header = extrair_processo_prioritario(texto)
            cands = footer_candidates(texto)
            hora, hid, proc_footer = pick_footer(cands, proc_header)

            processo_usado = proc_header if proc_header != "PROCESSO_NAO_ENCONTRADO" else (proc_footer or "PROCESSO_NAO_ENCONTRADO")
            timestamp = hora

            if hid and (not atual or atual["id"] != hid):
                if atual:
                    atual["paginas"] = pags
                    itens.append(atual)
                atual = {
                    "id": hid,
                    "timestamp": timestamp or "",
                    "processo": processo_usado,
                    "destinatario": extrair_destinatario(texto),
                    "pagina_inicial": i
                }
                pags = [i]
            elif hid and atual and atual["id"] == hid:
                pags.append(i)
            else:
                # sem id: se já há atual, continua nele; senão cria “órfão”
                if atual:
                    pags.append(i)
                else:
                    itens.append({
                        "id": f"sem_id_{i}",
                        "timestamp": "",
                        "processo": processo_usado,
                        "destinatario": extrair_destinatario(texto),
                        "pagina_inicial": i,
                        "paginas": [i]
                    })
        if atual:
            atual["paginas"] = pags
            itens.append(atual)
    return itens

# ---------- Agrupamento / anexos ----------
def mesmo_horario(ts1: str, ts2: str) -> bool:
    h1 = ts1.split()[-1] if ts1 else ""
    h2 = ts2.split()[-1] if ts2 else ""
    return h1 == h2 and h1 != ""

def eh_anexo_por_timestamp(sem_dest, validos):
    if not validos: return False
    ts = sem_dest.get("timestamp") or ""
    if not ts: return True
    for v in validos:
        tsv = v.get("timestamp") or ""
        if tsv and ts and mesmo_horario(ts, tsv):
            if sem_dest["id"] < v["id"] or tsv >= ts:
                return True
    return False

def agrupar_por_processo(mandados):
    grupos = defaultdict(lambda: {"mandados": [], "anexos": []})
    por_proc = defaultdict(list)
    for m in mandados:
        por_proc[m["processo"]].append(m)
    for proc, lst in por_proc.items():
        com_dest = [m for m in lst if m.get("destinatario") and m["destinatario"] != "DESTINATARIO_NAO_ENCONTRADO"]
        sem_dest = [m for m in lst if not m.get("destinatario") or m["destinatario"] == "DESTINATARIO_NAO_ENCONTRADO"]
        for s in sem_dest:
            if eh_anexo_por_timestamp(s, com_dest): grupos[proc]["anexos"].append(s)
            else: grupos[proc]["mandados"].append(s)
        grupos[proc]["mandados"].extend(com_dest)
    return dict(grupos)

# ---------- Escrita ----------
def salvar_mandado(m, pasta_principal: Path, caminho_pdf_original: str):
    nome = f"{m['destinatario']} - {m['processo']} - {m['id']}"
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip()
    pasta = _ensure_dir(pasta_principal / nome)
    out_pdf = _unique_file(pasta / f"{nome}.pdf")
    with open(caminho_pdf_original, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        w = PyPDF2.PdfWriter()
        for p in m["paginas"]:
            if 0 <= p < len(reader.pages):
                w.add_page(reader.pages[p])
        with open(out_pdf, "wb") as out:
            w.write(out)
    return pasta

def salvar_anexos(processos_com_anexos, pasta_principal: Path, caminho_pdf_original: str):
    with open(caminho_pdf_original, "rb") as fsrc:
        reader = PyPDF2.PdfReader(fsrc)
        for d in processos_com_anexos:
            proc = d["processo"]; mand = d["mandados"]; anex = d["anexos"]
            if mand:
                base = f"{mand[0]['destinatario']} - {mand[0]['processo']} - {mand[0]['id']}"
                base = re.sub(r'[<>:"/\\|?*]', "_", base).strip()
                pasta = _ensure_dir(pasta_principal / base)
                for i, a in enumerate(anex, 1):
                    nome = f"ANEXO_{i:02d} - {a['processo']} - {a['id']}.pdf"
                    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip()
                    out = _unique_file(pasta / nome)
                    w = PyPDF2.PdfWriter()
                    for p in a["paginas"]:
                        if 0 <= p < len(reader.pages):
                            w.add_page(reader.pages[p])
                    with open(out, "wb") as fd: w.write(fd)
            else:
                pasta = _ensure_dir(pasta_principal / re.sub(r'[<>:"/\\|?*]', "_", f"ANEXOS_SEM_MANDADO - {proc}"))
                for i, a in enumerate(anex, 1):
                    nome = f"ANEXO_ORFAO_{i:02d} - {a['id']}.pdf"
                    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip()
                    out = _unique_file(pasta / nome)
                    w = PyPDF2.PdfWriter()
                    for p in a["paginas"]:
                        if 0 <= p < len(reader.pages):
                            w.add_page(reader.pages[p])
                    with open(out, "wb") as fd: w.write(fd)

# ---------- Pipeline ----------
def process_single_pdf(pdf_path: Path, out_dir: Path):
    mandados = extrair_mandados(str(pdf_path))
    pasta_principal = _ensure_dir(out_dir)
    grupos = agrupar_por_processo(mandados)

    print(f"Arquivo: {pdf_path.name}")
    print(f"Processos distintos: {len(grupos)}")

    processos_com_anexos = []
    for proc, dados in grupos.items():
        for m in dados["mandados"]:
            salvar_mandado(m, pasta_principal, str(pdf_path))
        if dados["anexos"]:
            processos_com_anexos.append({"processo": proc, "mandados": dados["mandados"], "anexos": dados["anexos"]})

    if processos_com_anexos:
        salvar_anexos(processos_com_anexos, pasta_principal, str(pdf_path))

    print("OK.\n")

def process_target(target: Path, output_dir: Path = None):
    if target.is_dir():
        out_dir = output_dir or (target / "Mandados Separados")
        _ensure_dir(out_dir)
        pdfs = [p for p in target.iterdir() if p.suffix.lower() == ".pdf"]
        for pdf in pdfs:
            process_single_pdf(pdf, out_dir)
    else:
        base = target.parent
        out_dir = output_dir or (base / "Mandados Separados")
        _ensure_dir(out_dir)
        process_single_pdf(target, out_dir)

# ---------- GUI mínima (opcional) ----------
class SimpleGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Separador de Mandados PJe")
        self.root.geometry("600x420")
        tk.Label(self.root, text="Separador de Mandados PJe", font=("Arial", 18, "bold")).pack(pady=10)
        self.btn = tk.Button(self.root, text="Selecionar PDF ou Pasta", command=self.pick, bg="#007acc", fg="white", padx=20, pady=8)
        self.btn.pack(pady=8)
        self.text = tk.Text(self.root, height=14)
        self.text.pack(padx=10, pady=10, fill="both", expand=True)

    def log(self, s): self.text.insert("end", s + "\n"); self.text.see("end")

    def pick(self):
        p = filedialog.askopenfilename(title="Selecione um PDF (ou cancele e escolha uma pasta)",
                                       filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if p:
            t = Path(p)
            out = t.parent / "Mandados Separados"
            _ensure_dir(out)
            self.log(f"Processando {t.name} ...")
            try:
                process_single_pdf(t, out)
                self.log("Concluído.")
            except Exception as e:
                self.log(f"Erro: {e}")

    def run(self): self.root.mainloop()

# ---------- main ----------
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        alvo = Path(sys.argv[1]).expanduser().resolve()
        out = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else None
        process_target(alvo, out)
    else:
        if USE_GUI:
            SimpleGUI().run()
        else:
            print("Uso: separador_mandados.py <PDF_ou_PASTA> [PASTA_SAIDA]")
            sys.exit(1)
