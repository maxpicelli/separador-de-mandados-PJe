# Separador de Mandados PJe — Windows

Aplicativo Windows para separar automaticamente mandados em PDF extraídos do PJe, organizando por destinatário em pastas individuais.

## Como usar

1. Baixe o arquivo `Separador-de-Mandados-PJe.exe` na aba [Releases](../../releases) ou [Actions](../../actions)
2. Execute o `.exe` — na primeira vez o Windows pode exibir um aviso de SmartScreen, clique em **"Mais informações"** → **"Executar assim mesmo"**
3. Clique em **"Adicionar arquivos"** para selecionar PDFs ou **"Adicionar pasta"** para processar em lote (também é possível arrastar os arquivos direto para a lista)
4. Escolha a pasta de saída ou use a **saída automática** (cria a pasta `Mandados Separados` ao lado do arquivo)
5. Clique em **"Processar agora"**
6. Ao terminar, a pasta com os mandados separados abre automaticamente

## O que o app faz

- Lê PDFs do PJe e identifica cada mandado pelo número do processo e destinatário
- Agrupa mandados do mesmo destinatário automaticamente
- Associa anexos ao mandado correspondente pela proximidade de página
- Salva cada grupo em uma subpasta com o nome do destinatário dentro de `Mandados Separados`

## Build automático via GitHub Actions

A cada push na branch `master`, o GitHub Actions gera automaticamente o `.exe`:

1. Abra a aba **Actions** no repositório
2. Clique no build mais recente
3. Baixe o artefato **`separador-de-mandados-PJe-windows`**
4. Extraia o ZIP e execute o `Separador-de-Mandados-PJe.exe`

## Build local (Windows)

Requisitos: Python 3.13+

```powershell
pip install -r requirements-windows.txt
pwsh -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Saída: `dist\Separador-de-Mandados-PJe.exe`

## Observações

- O app é um único `.exe` — não precisa de instalação nem pasta adicional
- A pasta `Mandados Separados` é criada automaticamente ao lado do PDF processado
- Compatível com Windows 10 e 11

