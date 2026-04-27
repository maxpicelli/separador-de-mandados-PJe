#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Separador de Mandados PJe — VERSÃO FINAL CORRIGIDA
- Uma pasta por destinatário real
- Anexos sem destinatário vão para o mandado mais próximo (por página)
- Agrupa variações do mesmo nome mas separa empresas distintas (regras conservadoras)
- Saída SEMPRE em "Mandados Separados" ao lado do PDF (ou no out_dir passado)
"""

import os, re, sys, time, shutil
from pathlib import Path
from collections import defaultdict, Counter

VERSION = "v2025-08-16-final-corrigida"

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
        from tkinter import filedialog, messagebox
        USE_GUI = True
except Exception:
    USE_GUI = False

PROC_RE = r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b"

# ---------- Bypass (opcional) ----------
class BypassManager:
    def __init__(self):
        self.bypass_ativo = False
        self.bypass_expira = 0
        self.map = {"1": 60, "7": 420, "30": 1800, "boot": 999999}
    def ativar(self, codigo):
        if codigo in self.map:
            self.bypass_ativo = True
            self.bypass_expira = time.time() + self.map[codigo]
            return True
        return False
    def ativo(self):
        if not self.bypass_ativo: return False
        if time.time() > self.bypass_expira:
            self.bypass_ativo = False
            return False
        return True

bypass_manager = BypassManager()

# ---------- Helpers FS ----------
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _unique_file(p: Path) -> Path:
    c = p; n = 2
    while c.exists():
        c = p.with_name(f"{p.stem} ({n}){p.suffix}")
        n += 1
    return c

# ---------- Extração ----------
def footer_candidates(texto: str):
    cands = []
    for m in re.finditer(r"às (\d{2}:\d{2}:\d{2})\s*-\s*([a-f0-9]{5,})", texto, flags=re.IGNORECASE):
        hora = m.group(1)
        hid  = m.group(2)
        seg = texto[m.end(): m.end() + 600]
        pm = re.search(rf"(?:Número do processo|N[º°]\s*do\s*processo|Processo):\s*({PROC_RE})",
                       seg, flags=re.IGNORECASE)
        proc = pm.group(1) if pm else None
        cands.append((hora, hid, proc))
    return cands

def pick_footer(cands, proc_header: str):
    if not cands: return (None, None, None)
    if proc_header and proc_header != "PROCESSO_NAO_ENCONTRADO":
        for h, hid, pr in cands:
            if pr == proc_header:
                return (h, hid, pr)
    return cands[0]

def extrair_processo_prioritario(texto: str) -> str:
    patterns = [
        rf"Número do processo:\s*({PROC_RE})",
        rf"N[úu]mero do processo:\s*({PROC_RE})",
        rf"Processo n[úu]mero:\s*({PROC_RE})",
        rf"Processo:\s*({PROC_RE})",
        rf"N[º°]\s*do\s*processo:\s*({PROC_RE})",
        rf"PROCESSO\s+N[º°]?\s*({PROC_RE})",
        rf"PROC[.\s]*N[º°]?\s*({PROC_RE})",
        rf"Autos\s+n[º°]?\s*({PROC_RE})",
        rf"Processo\s+Eletrônico\s+n[º°]?\s*({PROC_RE})",
        rf"(?:^|\s)({PROC_RE})(?:\s|$)",
    ]
    for pat in patterns:
        matches = list(re.finditer(pat, texto, flags=re.IGNORECASE | re.MULTILINE))
        if matches:
            return matches[-1].group(1)
    matches = list(re.finditer(PROC_RE, texto))
    if matches:
        processos = [m.group(0) for m in matches]
        return Counter(processos).most_common(1)[0][0]
    return "PROCESSO_NAO_ENCONTRADO"

ROTULOS_DEST = [
    r"Destinatário:\s*([^\n\r]+)",  r"DESTINATÁRIO:\s*([^\n\r]+)",
    r"Destinatario:\s*([^\n\r]+)",  r"DESTINATARIO:\s*([^\n\r]+)",
    r"Intimado:\s*([^\n\r]+)",      r"INTIMADO:\s*([^\n\r]+)",
    r"Notificado:\s*([^\n\r]+)",    r"NOTIFICADO:\s*([^\n\r]+)",
    r"Citado:\s*([^\n\r]+)",        r"CITADO:\s*([^\n\r]+)",
    r"Reclamado:\s*([^\n\r]+)",     r"RECLAMADO:\s*([^\n\r]+)",
    r"Executado:\s*([^\n\r]+)",     r"EXECUTADO:\s*([^\n\r]+)",
    r"Réu:\s*([^\n\r]+)",           r"RÉU:\s*([^\n\r]+)",
    r"Requerido:\s*([^\n\r]+)",     r"REQUERIDO:\s*([^\n\r]+)",
    r"Para:\s*([^\n\r]+)",          r"PARA:\s*([^\n\r]+)",
    r"A:\s*([^\n\r]+)",             r"Ao:\s*([^\n\r]+)",
    r"Autor:\s*([^\n\r]+)",         r"AUTOR:\s*([^\n\r]+)",
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
        atual = None; pags = []
        for i, pg in enumerate(pdf.pages):
            texto = pg.extract_text() or ""
            proc_header = extrair_processo_prioritario(texto)
            cands = footer_candidates(texto)
            hora, hid, proc_footer = pick_footer(cands, proc_header)
            processo_usado = proc_header if proc_header != "PROCESSO_NAO_ENCONTRADO" else (proc_footer or "PROCESSO_NAO_ENCONTRADO")
            timestamp = hora

            if hid and (not atual or atual["id"] != hid):
                if atual:
                    atual["paginas"] = pags; itens.append(atual)
                atual = {
                    "id": hid, "timestamp": timestamp or "",
                    "processo": processo_usado,
                    "destinatario": extrair_destinatario(texto),
                    "pagina_inicial": i
                }
                pags = [i]
            elif hid and atual and atual["id"] == hid:
                pags.append(i)
            else:
                if atual:
                    pags.append(i)
                else:
                    itens.append({
                        "id": f"sem_id_{i}", "timestamp": "",
                        "processo": processo_usado,
                        "destinatario": extrair_destinatario(texto),
                        "pagina_inicial": i, "paginas": [i]
                    })
        if atual:
            atual["paginas"] = pags; itens.append(atual)
    return itens

# ---------- Agrupamento ----------
def eh_pessoa_fisica(nome):
    if not nome or nome == "DESTINATARIO_NAO_ENCONTRADO": return False
    empresas = [
        'LTDA','S/A','S.A','EIRELI','ME','EPP','CIA','COMPANHIA','INSTITUTO',
        'FUNDACAO','FUNDAÇÃO','ASSOCIACAO','ASSOCIAÇÃO','COOPERATIVA',
        'SINDICATO','FEDERACAO','FEDERAÇÃO','CONSELHO','SECRETARIA',
        'PREFEITURA','CÂMARA','CAMARA','TRIBUNAL','UNIVERSIDADE','FACULDADE',
        'ESCOLA','COLEGIO','COLÉGIO'
    ]
    u = nome.upper()
    if any(k in u for k in empresas): return False
    return 2 <= len(nome.split()) <= 4

def normalizar_nome(nome):
    if not nome or nome == "DESTINATARIO_NAO_ENCONTRADO": return ""
    n = re.sub(r'[^\w\s]', '', nome.upper())
    n = re.sub(r'\s+', ' ', n).strip()
    for suf in [' LTDA',' SA',' S A',' EIRELI',' ME',' EPP']:
        if n.endswith(suf): n = n[:-len(suf)].strip()
    return n

def nomes_sao_similares(nome1, nome2, processo):
    if not nome1 or not nome2: return False
    n1, n2 = normalizar_nome(nome1), normalizar_nome(nome2)
    if not n1 or not n2: return False
    if n1 == n2: return True
    if eh_pessoa_fisica(nome1) or eh_pessoa_fisica(nome2):
        return n1 in n2 or n2 in n1

    p1, p2 = set(n1.split()), set(n2.split())
    if p1.issubset(p2) or p2.issubset(p1):
        conflitantes = {
            'ENSINO','PESQUISAS','PESQUISA','COMERCIO','COMERCIAL','SERVICOS','SERVICO',
            'TECNOLOGIA','EDUCACAO','EDUCACIONAL','CONSULTORIA','ASSESSORIA','HOSPITAL',
            'CLINICA','LABORATORIO','TRANSPORTES','LOGISTICA','CONSTRUCAO','ENGENHARIA',
            'VIGILANCIA','SEGURANCA','LIMPEZA','TERCEIRIZACAO'
        }
        c1, c2 = p1 & conflitantes, p2 & conflitantes
        if c1 and c2 and c1 != c2:
            print(f"    ⚠️ Empresas relacionadas mas DIFERENTES: {c1} vs {c2}")
            return False
        return True
    inter = p1 & p2
    m = min(len(p1), len(p2))
    return m > 0 and (len(inter)/m) >= 0.85

def escolher_nome_principal(nomes):
    v = [n for n in nomes if n and n != "DESTINATARIO_NAO_ENCONTRADO"]
    return max(v, key=len) if v else "DESTINATARIO_NAO_ENCONTRADO"

def agrupar_inteligente(mandados):
    print(f"\n{'='*60}\nAGRUPAMENTO INTELIGENTE DE {len(mandados)} DOCUMENTOS\n{'='*60}")
    por_proc = defaultdict(list)
    for d in mandados:
        por_proc[d.get("processo","PROCESSO_NAO_ENCONTRADO")].append(d)

    grupos_finais = {}
    for processo, docs in por_proc.items():
        print(f"\n[PROCESSO] {processo} - {len(docs)} documentos")
        docs = sorted(docs, key=lambda x: x.get("pagina_inicial", 0))
        com_dest = [d for d in docs if d.get("destinatario") and d["destinatario"]!="DESTINATARIO_NAO_ENCONTRADO"]
        sem_dest = [d for d in docs if not d.get("destinatario") or d["destinatario"]=="DESTINATARIO_NAO_ENCONTRADO"]
        print(f"  📋 Com destinatário: {len(com_dest)}")
        print(f"  📎 Sem destinatário: {len(sem_dest)}")
        if not com_dest: continue

        grupos = []
        for d in com_dest:
            dest = d["destinatario"]
            g = None
            for grp in grupos:
                if nomes_sao_similares(dest, grp["nome_principal"], processo):
                    g = grp; break
            if g:
                g["mandados"].append(d); g["nomes_encontrados"].append(dest)
                print(f"    🔗 Agrupando: {dest[:30]} → {g['nome_principal'][:30]}")
            else:
                grupos.append({"nome_principal": dest, "mandados":[d], "anexos":[], "nomes_encontrados":[dest], "processo": processo})
                print(f"    📁 Novo grupo: {dest[:30]}")

        for a in sem_dest:
            pa = a.get("pagina_inicial", 0)
            melhor, dist = None, 1e9
            for grp in grupos:
                for m in grp["mandados"]:
                    pm = m.get("pagina_inicial", 0)
                    if pa > pm and (pa-pm) < dist:
                        dist = pa-pm; melhor = grp
            if melhor:
                melhor["anexos"].append(a)
                print(f"    📎 Anexo pág {pa} → {melhor['nome_principal'][:30]}...")
            elif grupos:
                grupos[0]["anexos"].append(a)
                print(f"    📎 Anexo órfão pág {pa} → {grupos[0]['nome_principal'][:30]}...")

        for grp in grupos:
            grp["nome_principal"] = escolher_nome_principal(grp["nomes_encontrados"])
            print(f"  └─ {grp['nome_principal'][:40]}... ({len(grp['mandados'])} mandado(s) + {len(grp['anexos'])} anexo(s))")

        for i, grp in enumerate(grupos):
            grupos_finais[f"{processo}___{i}"] = grp

    print(f"\n📊 RESUMO: {len(grupos_finais)} grupos criados")
    return grupos_finais

# ---------- Salvamento ----------
def salvar_grupos_inteligentes(grupos, pasta_saida: Path, caminho_pdf_original: str):
    with open(caminho_pdf_original, "rb") as fsrc:
        reader = PyPDF2.PdfReader(fsrc)
        print(f"\n{'='*60}\nSALVANDO {len(grupos)} GRUPOS\n{'='*60}")
        for chave, grupo in grupos.items():
            nome = grupo["nome_principal"]
            proc = grupo["processo"]
            mand = grupo.get("mandados", [])
            anex = grupo.get("anexos", [])

            nome_pasta = (f"{nome} - {proc}" if nome and nome!="DESTINATARIO_NAO_ENCONTRADO"
                          else f"SEM_DESTINATARIO - {proc}")
            nome_pasta = re.sub(r'[<>:"/\\|?*]', "_", nome_pasta).strip()
            pasta = _ensure_dir(pasta_saida / nome_pasta)

            for i, m in enumerate(mand):
                arq = (f"MANDADO - {nome} - {proc}.pdf" if i==0
                       else f"MANDADO_{i+1:02d} - {nome} - {proc}.pdf")
                arq = re.sub(r'[<>:"/\\|?*]', "_", arq)
                out = _unique_file(pasta / arq)
                w = PyPDF2.PdfWriter()
                for p in m["paginas"]:
                    if 0 <= p < len(reader.pages):
                        w.add_page(reader.pages[p])
                with open(out, "wb") as f: w.write(f)
                print(f"   ✅ {out.name}")

            for i, a in enumerate(anex, 1):
                arq = f"ANEXO_{i:02d} - {nome} - {a['id'][:8]}.pdf"
                arq = re.sub(r'[<>:"/\\|?*]', "_", arq)
                out = _unique_file(pasta / arq)
                w = PyPDF2.PdfWriter()
                for p in a["paginas"]:
                    if 0 <= p < len(reader.pages):
                        w.add_page(reader.pages[p])
                with open(out, "wb") as f: w.write(f)
                print(f"   📎 {out.name}")

# ---------- Permissões (opcional) ----------
def verificar_permissoes(caminho_pdf: Path):
    try:
        print(f"🔐 Verificando permissões em: {caminho_pdf.parent}")
        with open(caminho_pdf, 'rb') as f: f.read(1)
        pasta = caminho_pdf.parent / "Mandados Separados"
        pasta.mkdir(exist_ok=True)
        tmp = pasta / "teste.tmp"; tmp.touch(); tmp.unlink()
        print("✅ Permissões OK")
        return True
    except PermissionError as e:
        print(f"❌ Permissão negada: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Aviso na verificação: {e}")
        return True

# ---------- Pipeline ----------
def process_single_pdf(pdf_path: Path, out_dir: Path, bypass_ativo=False):
    print(f"\n🔄 PROCESSANDO: {pdf_path.name}")
    if not (bypass_ativo or bypass_manager.ativo()):
        if not verificar_permissoes(pdf_path):
            print("❌ Abortado por permissões."); return
    mandados = extrair_mandados(str(pdf_path))
    print(f"📄 Documentos extraídos: {len(mandados)}")
    grupos = agrupar_inteligente(mandados)
    pasta = _ensure_dir(out_dir)
    salvar_grupos_inteligentes(grupos, pasta, str(pdf_path))
    print("✅ CONCLUÍDO!")

def process_target(target: Path, output_dir: Path = None, bypass_ativo=False):
    if target.is_dir():
        out_dir = output_dir or (target / "Mandados Separados")
        _ensure_dir(out_dir)
        pdfs = [p for p in target.iterdir() if p.suffix.lower()==".pdf"]
        print(f"Encontrados {len(pdfs)} arquivos PDF")
        for pdf in pdfs:
            process_single_pdf(pdf, out_dir, bypass_ativo)
    else:
        base = target.parent
        out_dir = output_dir or (base / "Mandados Separados")
        _ensure_dir(out_dir)
        process_single_pdf(target, out_dir, bypass_ativo)

# ---------- GUI ----------
class SimpleGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Separador de Mandados — FINAL")
        self.root.geometry("840x660")

        titulo = tk.Label(self.root, text=f"Separador de Mandados — {VERSION}",
                          font=("Arial", 16, "bold"))
        titulo.pack(pady=12)

        # Toggle de bypass
        self.acesso_total = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(self.root, text="Pular verificações (bypass)",
                             variable=self.acesso_total)
        chk.pack()

        self.btn = tk.Button(self.root, text="📁 Selecionar PDF ou Pasta",
                             command=self.pick, bg="#3498db", fg="white",
                             padx=28, pady=10, font=("Arial", 12, "bold"))
        self.btn.pack(pady=12)

        frame = tk.Frame(self.root); frame.pack(padx=16, pady=10, fill="both", expand=True)
        self.text = tk.Text(frame, height=28, font=("Consolas", 9), bg="#f7f7f7")
        sb = tk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")

    def log(self, s):
        self.text.insert("end", s + "\n"); self.text.see("end"); self.root.update()

    def pick(self):
        arq = filedialog.askopenfilename(title="Selecione um PDF",
                                         filetypes=[("PDF","*.pdf"),("Todos","*.*")])
        if arq:
            self.processar(Path(arq)); return
        pasta = filedialog.askdirectory(title="Ou selecione uma pasta com PDFs")
        if pasta:
            self.processar(Path(pasta))

    def processar(self, target: Path):
        try:
            self.text.delete(1.0, "end")
            self.log(f"🚀 Iniciando: {target.name}")

            from io import StringIO
            old_stdout = sys.stdout
            mystdout = StringIO(); sys.stdout = mystdout

            bypass = self.acesso_total.get()

            if target.is_file():
                out_dir = target.parent / "Mandados Separados"
                process_single_pdf(target, out_dir, bypass)
            else:
                process_target(target, None, bypass)

            sys.stdout = old_stdout
            self.log(mystdout.getvalue())

            messagebox.showinfo("🎉 Sucesso",
                                "Processamento concluído!\n"
                                "📁 Pasta: Mandados Separados")
        except Exception as e:
            try: sys.stdout = old_stdout
            except: pass
            self.log(f"❌ ERRO: {e}")
            import traceback; self.log(traceback.format_exc())
            messagebox.showerror("Erro", str(e))

    def run(self):
        self.root.mainloop()

# ---------- Debug ----------
def debug_listagem(pasta_mandados):
    pasta = Path(pasta_mandados)
    if not pasta.exists():
        print(f"❌ Pasta não encontrada: {pasta}"); return
    pastas = [p for p in sorted(pasta.iterdir()) if p.is_dir()]
    soltos = [p for p in sorted(pasta.iterdir()) if p.is_file() and p.suffix.lower()==".pdf"]
    print(f"\n{'='*80}\n🔍 Estrutura: {pasta.name}\nPastas: {len(pastas)} | Arquivos soltos: {len(soltos)}\n")
    for d in pastas:
        arquivos = list(d.glob("*.pdf"))
        print(f"📁 {d.name} — {len(arquivos)} arquivo(s)")
        for a in sorted(arquivos):
            print(f"   - {a.name}")
    if soltos:
        print("\n📄 Arquivos soltos:")
        for a in soltos: print(f"   - {a.name}")

def debug_extracao(caminho_pdf):
    print(f"\n{'='*80}\n🔍 EXTRAÇÃO: {Path(caminho_pdf).name}\n{'='*80}")
    mandados = extrair_mandados(caminho_pdf)
    print(f"📄 TOTAL: {len(mandados)}\n")
    todos = sorted(mandados, key=lambda x: x.get("pagina_inicial", 0))
    for i, m in enumerate(todos, 1):
        print(f"{i:02d}. ID {m['id'][:10]}… | Proc {m['processo']} | Dest {m['destinatario'][:40]} | pág ini {m.get('pagina_inicial',0)}")
    return mandados

def debug_similaridade(nome1, nome2):
    print(f"\n{'='*60}\n🔍 TESTE DE SIMILARIDADE\n{'='*60}")
    n1, n2 = normalizar_nome(nome1), normalizar_nome(nome2)
    print(f"1: {nome1} → {n1}\n2: {nome2} → {n2}")
    print("Resultado:", "SIMILARES" if nomes_sao_similares(nome1, nome2, "TESTE") else "DIFERENTES")

# ---------- Main ----------
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--debug" and len(sys.argv) >= 3:
            debug_listagem(sys.argv[2])
        elif sys.argv[1] == "--debug-extract" and len(sys.argv) >= 3:
            debug_extracao(sys.argv[2])
        elif sys.argv[1] == "--debug-similar" and len(sys.argv) >= 4:
            debug_similaridade(sys.argv[2], sys.argv[3])
        else:
            alvo = Path(sys.argv[1]).expanduser().resolve()
            out = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else None
            process_target(alvo, out, bypass_ativo=False)
    else:
        if USE_GUI:
            SimpleGUI().run()
        else:
            print(f"🧠 Separador de Mandados — {VERSION}")
            print("Uso: python script.py <PDF_ou_PASTA> [PASTA_SAIDA]")
            print("Debug estrutura: python script.py --debug <PASTA>")
            print("Debug extração: python script.py --debug-extract <ARQUIVO_PDF>")
            print("Debug similaridade: python script.py --debug-similar \"Nome 1\" \"Nome 2\"")
            sys.exit(1)
