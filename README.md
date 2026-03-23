# separador-de-mandados-PJe

Port do projeto original em macOS para uma base desktop preparada para Windows.

## Estado atual

- O frontend antigo em SwiftUI/AppKit continua no repositório como backup.
- A versão nova para Windows está em `windows_app/`.
- O backend consolidado de separação de PDFs está em `windows_app/backend.py`.
- O build automático de `.exe` está em `.github/workflows/build-windows.yml`.

## Nome do produto

- Repositório: `separador-de-mandados-PJe`
- Aplicativo: `Separador de Mandados PJe`
- Executável Windows: `Separador-de-Mandados-PJe.exe`

## Gerar o executável Windows

Sem PC Windows local, use GitHub Actions:

1. Publique este conteúdo em um repositório GitHub chamado `separador-de-mandados-PJe`.
2. Abra a aba `Actions`.
3. Rode `Build Windows EXE`.
4. Baixe o artefato `separador-de-mandados-PJe-windows`.

## Publicar no GitHub

Este diretório já foi inicializado como repositório git local com branch `main`.

```bash
git add .
git commit -m "Prepare Windows port for separador-de-mandados-PJe"
git remote add origin <URL_DO_REPOSITORIO>
git push -u origin main
```

## Rodar localmente para desenvolvimento

Consulte `README-Windows.md`.
