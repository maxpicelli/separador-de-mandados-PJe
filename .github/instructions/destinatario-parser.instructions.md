---
description: "Use when editing the destinatario extraction, grouping, or PDF naming flow for mandados in the Python backend. Covers protected parser behavior, additive fixes, duplicated logic, and no-regression rules."
applyTo: "{windows_app/backend.py,Separador de Mandados/separador_mandados.py}"
---
# Destinatario Parser Guardrails

These two files contain duplicated production logic and must stay aligned:
- `windows_app/backend.py`
- `Separador de Mandados/separador_mandados.py`

When changing destinatario extraction or grouping in these files:
- Preserve existing working cases. Prefer additive fixes over rewrites.
- Do not remove previously supported label variants unless explicitly requested.
- Do not switch fallback behavior back to discarding a process when no destinatario is extracted.
- Keep the `SEM_DESTINATARIO` fallback group behavior intact so PDFs are still generated.
- If one of the duplicated files changes, mirror the same behavioral change in the other active file.

Supported destinatario patterns that must keep working:
- `Destinatário:`
- `Destinatários:`
- `Destinatário(a)(s):`
- `Destinatário/Testemunha:`
- same-line and following-line extraction after the label
- `Pessoa Física:` and `Pessoa Jurídica:` sublabels before the actual name
- multiple destinatarios inline on the same line; keep the first extracted name unless explicitly requested otherwise
- inline qualifiers inside parentheses such as CPF, CNPJ, or pessoa física/jurídica markers

Behavior constraints:
- Do not use party labels like `Réu`, `Reclamado`, or `Executado` as generic destinatario fallback.
- Fix root-cause parsing gaps locally instead of rewriting grouping or save flows.
- Keep file and folder naming stable unless the user asks for a naming change.

Validation expectation after edits in these files:
- Run a focused extraction check against the touched label format.
- Re-check at least one previously fixed destinatario scenario to avoid regression.
