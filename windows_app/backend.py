from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

import pdfplumber
from pypdf import PdfReader, PdfWriter

PROC_RE = r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b"
INVALID_FS_CHARS = r'[<>:"/\\|?*]'
LogFn = Callable[[str], None]


class BypassManager:
    def __init__(self) -> None:
        self.bypass_ativo = False
        self.bypass_expira = 0.0
        self.map = {"1": 60, "7": 420, "30": 1800, "boot": 999999}

    def ativar(self, codigo: str) -> bool:
        if codigo not in self.map:
            return False
        self.bypass_ativo = True
        self.bypass_expira = time.time() + self.map[codigo]
        return True

    def ativo(self) -> bool:
        if not self.bypass_ativo:
            return False
        if time.time() > self.bypass_expira:
            self.bypass_ativo = False
            return False
        return True


bypass_manager = BypassManager()


def default_logger(message: str) -> None:
    print(message)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _unique_file(path: Path) -> Path:
    candidate = path
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        index += 1
    return candidate


def footer_candidates(texto: str) -> list[tuple[str, str, str | None]]:
    candidates: list[tuple[str, str, str | None]] = []
    for match in re.finditer(r"às (\d{2}:\d{2}:\d{2})\s*-\s*([a-f0-9]{5,})", texto, flags=re.IGNORECASE):
        hora = match.group(1)
        hid = match.group(2)
        segment = texto[match.end(): match.end() + 600]
        process_match = re.search(
            rf"(?:Número do processo|N[º°]\s*do\s*processo|Processo):\s*({PROC_RE})",
            segment,
            flags=re.IGNORECASE,
        )
        processo = process_match.group(1) if process_match else None
        candidates.append((hora, hid, processo))
    return candidates


def pick_footer(candidates: list[tuple[str, str, str | None]], proc_header: str) -> tuple[str | None, str | None, str | None]:
    if not candidates:
        return (None, None, None)
    if proc_header and proc_header != "PROCESSO_NAO_ENCONTRADO":
        for hora, hid, processo in candidates:
            if processo == proc_header:
                return (hora, hid, processo)
    return candidates[0]


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
    for pattern in patterns:
        matches = list(re.finditer(pattern, texto, flags=re.IGNORECASE | re.MULTILINE))
        if matches:
            return matches[-1].group(1)

    matches = list(re.finditer(PROC_RE, texto))
    if matches:
        processos = [match.group(0) for match in matches]
        return Counter(processos).most_common(1)[0][0]

    return "PROCESSO_NAO_ENCONTRADO"


ROTULOS_DEST = [
    r"Destinatário:\s*([^\n\r]+)",
    r"DESTINATÁRIO:\s*([^\n\r]+)",
    r"Destinatario:\s*([^\n\r]+)",
    r"DESTINATARIO:\s*([^\n\r]+)",
    r"Intimado:\s*([^\n\r]+)",
    r"INTIMADO:\s*([^\n\r]+)",
    r"Notificado:\s*([^\n\r]+)",
    r"NOTIFICADO:\s*([^\n\r]+)",
    r"Citado:\s*([^\n\r]+)",
    r"CITADO:\s*([^\n\r]+)",
    r"Reclamado:\s*([^\n\r]+)",
    r"RECLAMADO:\s*([^\n\r]+)",
    r"Executado:\s*([^\n\r]+)",
    r"EXECUTADO:\s*([^\n\r]+)",
    r"Réu:\s*([^\n\r]+)",
    r"RÉU:\s*([^\n\r]+)",
    r"Requerido:\s*([^\n\r]+)",
    r"REQUERIDO:\s*([^\n\r]+)",
    r"Para:\s*([^\n\r]+)",
    r"PARA:\s*([^\n\r]+)",
    r"A:\s*([^\n\r]+)",
    r"Ao:\s*([^\n\r]+)",
    r"Autor:\s*([^\n\r]+)",
    r"AUTOR:\s*([^\n\r]+)",
]


def extrair_destinatario(texto: str) -> str:
    for pattern in ROTULOS_DEST:
        match = re.search(pattern, texto, flags=re.MULTILINE)
        if not match:
            continue

        bruto = match.group(1).strip()
        nome = re.split(r"[,\-–;|\n\r]", bruto, maxsplit=1)[0].strip()
        nome = re.sub(r"\s+(CPF|CNPJ|RG|ID)\b.*$", "", nome, flags=re.IGNORECASE).strip()
        nome = re.sub(r"^[^\wÁÉÍÓÚÂÊÔÃÕÇ]+", "", nome)
        nome = re.sub(r"[^\wÁÉÍÓÚÂÊÔÃÕÇ\s]+$", "", nome)
        nome = re.sub(r"\s+", " ", nome)
        if len(nome) >= 3 and re.search(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇà-ü]", nome):
            return nome

    return "DESTINATARIO_NAO_ENCONTRADO"


def extrair_mandados(caminho_pdf: str) -> list[dict[str, object]]:
    itens: list[dict[str, object]] = []
    with pdfplumber.open(caminho_pdf) as pdf:
        atual: dict[str, object] | None = None
        paginas_atuais: list[int] = []

        for page_index, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text() or ""
            proc_header = extrair_processo_prioritario(texto)
            candidates = footer_candidates(texto)
            hora, hid, proc_footer = pick_footer(candidates, proc_header)
            processo_usado = proc_header if proc_header != "PROCESSO_NAO_ENCONTRADO" else (proc_footer or "PROCESSO_NAO_ENCONTRADO")

            if hid and (not atual or atual["id"] != hid):
                if atual:
                    atual["paginas"] = paginas_atuais
                    itens.append(atual)
                atual = {
                    "id": hid,
                    "timestamp": hora or "",
                    "processo": processo_usado,
                    "destinatario": extrair_destinatario(texto),
                    "pagina_inicial": page_index,
                }
                paginas_atuais = [page_index]
            elif hid and atual and atual["id"] == hid:
                paginas_atuais.append(page_index)
            else:
                if atual:
                    paginas_atuais.append(page_index)
                else:
                    itens.append(
                        {
                            "id": f"sem_id_{page_index}",
                            "timestamp": "",
                            "processo": processo_usado,
                            "destinatario": extrair_destinatario(texto),
                            "pagina_inicial": page_index,
                            "paginas": [page_index],
                        }
                    )

        if atual:
            atual["paginas"] = paginas_atuais
            itens.append(atual)

    return itens


def eh_pessoa_fisica(nome: str) -> bool:
    if not nome or nome == "DESTINATARIO_NAO_ENCONTRADO":
        return False

    empresas = [
        "LTDA",
        "S/A",
        "S.A",
        "EIRELI",
        "ME",
        "EPP",
        "CIA",
        "COMPANHIA",
        "INSTITUTO",
        "FUNDACAO",
        "FUNDAÇÃO",
        "ASSOCIACAO",
        "ASSOCIAÇÃO",
        "COOPERATIVA",
        "SINDICATO",
        "FEDERACAO",
        "FEDERAÇÃO",
        "CONSELHO",
        "SECRETARIA",
        "PREFEITURA",
        "CÂMARA",
        "CAMARA",
        "TRIBUNAL",
        "UNIVERSIDADE",
        "FACULDADE",
        "ESCOLA",
        "COLEGIO",
        "COLÉGIO",
    ]
    upper_name = nome.upper()
    if any(keyword in upper_name for keyword in empresas):
        return False
    return 2 <= len(nome.split()) <= 4


def normalizar_nome(nome: str) -> str:
    if not nome or nome == "DESTINATARIO_NAO_ENCONTRADO":
        return ""

    normalizado = re.sub(r"[^\w\s]", "", nome.upper())
    normalizado = re.sub(r"\s+", " ", normalizado).strip()
    for suffix in [" LTDA", " SA", " S A", " EIRELI", " ME", " EPP"]:
        if normalizado.endswith(suffix):
            normalizado = normalizado[: -len(suffix)].strip()
    return normalizado


def nomes_sao_similares(nome1: str, nome2: str, _processo: str) -> bool:
    if not nome1 or not nome2:
        return False

    nome1_normalizado = normalizar_nome(nome1)
    nome2_normalizado = normalizar_nome(nome2)
    if not nome1_normalizado or not nome2_normalizado:
        return False
    if nome1_normalizado == nome2_normalizado:
        return True

    if eh_pessoa_fisica(nome1) or eh_pessoa_fisica(nome2):
        return nome1_normalizado in nome2_normalizado or nome2_normalizado in nome1_normalizado

    partes1 = set(nome1_normalizado.split())
    partes2 = set(nome2_normalizado.split())
    if partes1.issubset(partes2) or partes2.issubset(partes1):
        conflitantes = {
            "ENSINO",
            "PESQUISAS",
            "PESQUISA",
            "COMERCIO",
            "COMERCIAL",
            "SERVICOS",
            "SERVICO",
            "TECNOLOGIA",
            "EDUCACAO",
            "EDUCACIONAL",
            "CONSULTORIA",
            "ASSESSORIA",
            "HOSPITAL",
            "CLINICA",
            "LABORATORIO",
            "TRANSPORTES",
            "LOGISTICA",
            "CONSTRUCAO",
            "ENGENHARIA",
            "VIGILANCIA",
            "SEGURANCA",
            "LIMPEZA",
            "TERCEIRIZACAO",
        }
        conflito1 = partes1 & conflitantes
        conflito2 = partes2 & conflitantes
        if conflito1 and conflito2 and conflito1 != conflito2:
            return False
        return True

    intersecao = partes1 & partes2
    menor = min(len(partes1), len(partes2))
    return menor > 0 and (len(intersecao) / menor) >= 0.85


def escolher_nome_principal(nomes: list[str]) -> str:
    validos = [nome for nome in nomes if nome and nome != "DESTINATARIO_NAO_ENCONTRADO"]
    return max(validos, key=len) if validos else "DESTINATARIO_NAO_ENCONTRADO"


def agrupar_inteligente(mandados: list[dict[str, object]], log: LogFn = default_logger) -> dict[str, dict[str, object]]:
    log(f"\n{'=' * 60}\nAGRUPAMENTO INTELIGENTE DE {len(mandados)} DOCUMENTOS\n{'=' * 60}")
    por_processo: dict[str, list[dict[str, object]]] = defaultdict(list)
    for documento in mandados:
        por_processo[str(documento.get("processo", "PROCESSO_NAO_ENCONTRADO"))].append(documento)

    grupos_finais: dict[str, dict[str, object]] = {}
    for processo, documentos in por_processo.items():
        log(f"\n[PROCESSO] {processo} - {len(documentos)} documentos")
        documentos_ordenados = sorted(documentos, key=lambda item: int(item.get("pagina_inicial", 0)))
        com_destinatario = [doc for doc in documentos_ordenados if doc.get("destinatario") and doc["destinatario"] != "DESTINATARIO_NAO_ENCONTRADO"]
        sem_destinatario = [doc for doc in documentos_ordenados if not doc.get("destinatario") or doc["destinatario"] == "DESTINATARIO_NAO_ENCONTRADO"]
        log(f"  📋 Com destinatário: {len(com_destinatario)}")
        log(f"  📎 Sem destinatário: {len(sem_destinatario)}")

        if not com_destinatario:
            continue

        grupos: list[dict[str, object]] = []
        for documento in com_destinatario:
            destinatario = str(documento["destinatario"])
            grupo = None
            for grupo_existente in grupos:
                if nomes_sao_similares(destinatario, str(grupo_existente["nome_principal"]), processo):
                    grupo = grupo_existente
                    break

            if grupo:
                grupo["mandados"].append(documento)
                grupo["nomes_encontrados"].append(destinatario)
                log(f"    🔗 Agrupando: {destinatario[:30]} → {str(grupo['nome_principal'])[:30]}")
            else:
                grupos.append(
                    {
                        "nome_principal": destinatario,
                        "mandados": [documento],
                        "anexos": [],
                        "nomes_encontrados": [destinatario],
                        "processo": processo,
                    }
                )
                log(f"    📁 Novo grupo: {destinatario[:30]}")

        for anexo in sem_destinatario:
            pagina_anexo = int(anexo.get("pagina_inicial", 0))
            melhor_grupo = None
            distancia = 10**9
            for grupo in grupos:
                for mandado in grupo["mandados"]:
                    pagina_mandado = int(mandado.get("pagina_inicial", 0))
                    if pagina_anexo > pagina_mandado and (pagina_anexo - pagina_mandado) < distancia:
                        distancia = pagina_anexo - pagina_mandado
                        melhor_grupo = grupo
            if melhor_grupo:
                melhor_grupo["anexos"].append(anexo)
                log(f"    📎 Anexo pág {pagina_anexo} → {str(melhor_grupo['nome_principal'])[:30]}...")
            elif grupos:
                grupos[0]["anexos"].append(anexo)
                log(f"    📎 Anexo órfão pág {pagina_anexo} → {str(grupos[0]['nome_principal'])[:30]}...")

        for index, grupo in enumerate(grupos):
            grupo["nome_principal"] = escolher_nome_principal(list(grupo["nomes_encontrados"]))
            log(
                f"  └─ {str(grupo['nome_principal'])[:40]}... "
                f"({len(grupo['mandados'])} mandado(s) + {len(grupo['anexos'])} anexo(s))"
            )
            grupos_finais[f"{processo}___{index}"] = grupo

    log(f"\n📊 RESUMO: {len(grupos_finais)} grupos criados")
    return grupos_finais


def verificar_permissoes(caminho_pdf: Path, log: LogFn = default_logger) -> bool:
    try:
        log(f"🔐 Verificando permissões em: {caminho_pdf.parent}")
        with caminho_pdf.open("rb") as arquivo:
            arquivo.read(1)
        pasta = caminho_pdf.parent / "Mandados Separados"
        pasta.mkdir(exist_ok=True)
        temporario = pasta / "teste.tmp"
        temporario.touch()
        temporario.unlink()
        log("✅ Permissões OK")
        return True
    except PermissionError as error:
        log(f"❌ Permissão negada: {error}")
        return False
    except Exception as error:
        log(f"⚠️ Aviso na verificação: {error}")
        return True


def sanitize_name(value: str) -> str:
    return re.sub(INVALID_FS_CHARS, "_", value).strip()


def salvar_grupos_inteligentes(
    grupos: dict[str, dict[str, object]],
    pasta_saida: Path,
    caminho_pdf_original: Path,
    log: LogFn = default_logger,
) -> None:
    with caminho_pdf_original.open("rb") as arquivo_origem:
        reader = PdfReader(arquivo_origem)
        log(f"\n{'=' * 60}\nSALVANDO {len(grupos)} GRUPOS\n{'=' * 60}")

        for grupo in grupos.values():
            nome = str(grupo["nome_principal"])
            processo = str(grupo["processo"])
            mandados = list(grupo.get("mandados", []))
            anexos = list(grupo.get("anexos", []))

            if nome and nome != "DESTINATARIO_NAO_ENCONTRADO":
                nome_pasta = f"{nome} - {processo}"
            else:
                nome_pasta = f"SEM_DESTINATARIO - {processo}"
            pasta = _ensure_dir(pasta_saida / sanitize_name(nome_pasta))

            for index, mandado in enumerate(mandados):
                if index == 0:
                    arquivo = f"MANDADO - {nome} - {processo}.pdf"
                else:
                    arquivo = f"MANDADO_{index + 1:02d} - {nome} - {processo}.pdf"

                destino = _unique_file(pasta / sanitize_name(arquivo))
                writer = PdfWriter()
                for pagina in mandado["paginas"]:
                    page_index = int(pagina)
                    if 0 <= page_index < len(reader.pages):
                        writer.add_page(reader.pages[page_index])
                with destino.open("wb") as arquivo_saida:
                    writer.write(arquivo_saida)
                log(f"   ✅ {destino.name}")

            for index, anexo in enumerate(anexos, start=1):
                arquivo = f"ANEXO_{index:02d} - {nome} - {str(anexo['id'])[:8]}.pdf"
                destino = _unique_file(pasta / sanitize_name(arquivo))
                writer = PdfWriter()
                for pagina in anexo["paginas"]:
                    page_index = int(pagina)
                    if 0 <= page_index < len(reader.pages):
                        writer.add_page(reader.pages[page_index])
                with destino.open("wb") as arquivo_saida:
                    writer.write(arquivo_saida)
                log(f"   📎 {destino.name}")


def process_single_pdf(
    pdf_path: Path,
    out_dir: Path,
    bypass_ativo: bool = False,
    log: LogFn = default_logger,
) -> None:
    log(f"\n🔄 PROCESSANDO: {pdf_path.name}")
    if not (bypass_ativo or bypass_manager.ativo()):
        if not verificar_permissoes(pdf_path, log=log):
            raise PermissionError(f"Sem permissão de leitura ou escrita em {pdf_path.parent}")

    mandados = extrair_mandados(str(pdf_path))
    log(f"📄 Documentos extraídos: {len(mandados)}")
    grupos = agrupar_inteligente(mandados, log=log)
    pasta = _ensure_dir(out_dir)
    salvar_grupos_inteligentes(grupos, pasta, pdf_path, log=log)
    log("✅ CONCLUÍDO!")


def process_target(
    target: Path,
    output_dir: Path | None = None,
    bypass_ativo: bool = False,
    log: LogFn = default_logger,
) -> Path:
    if not target.exists():
        raise FileNotFoundError(f"Entrada não encontrada: {target}")

    if target.is_dir():
        out_dir = output_dir or (target / "Mandados Separados")
        _ensure_dir(out_dir)
        pdfs = sorted(path for path in target.iterdir() if path.suffix.lower() == ".pdf")
        log(f"Encontrados {len(pdfs)} arquivos PDF")
        for pdf in pdfs:
            process_single_pdf(pdf, out_dir, bypass_ativo=bypass_ativo, log=log)
        return out_dir

    out_dir = output_dir or (target.parent / "Mandados Separados")
    _ensure_dir(out_dir)
    process_single_pdf(target, out_dir, bypass_ativo=bypass_ativo, log=log)
    return out_dir
