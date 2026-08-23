# separador-de-mandados-PJe

Repositório preparado para a versão desktop Windows do Separador de Mandados PJe.

## Estrutura nova

- `windows_app/backend.py`: lógica consolidada de separação dos PDFs.
- `windows_app/app.py`: interface desktop em PySide6.
- `windows_app/assets/app_icon.png`: ícone base reutilizado do app original.
- `windows_app/separador_windows.spec`: configuração do PyInstaller para gerar `Separador-de-Mandados-PJe.exe`.
- `scripts/generate_windows_icon.py`: gera `app_icon.ico` a partir do PNG.
- `scripts/build_windows.ps1`: build local de Windows em um passo.
- `.github/workflows/build-windows.yml`: build automático em runner Windows.

## Rodar localmente no macOS ou Windows

Use Python 3.12. Python 3.14 ainda não é uma base segura para empacotamento com todas as dependências gráficas.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-windows.txt
python -m windows_app
```

No Windows, ative a venv com:

```powershell
.venv\Scripts\Activate.ps1
```

## Gerar o EXE em Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-windows.txt
python scripts\generate_windows_icon.py
pwsh -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Saída esperada:

- `dist\Separador-de-Mandados-PJe.exe`

## Gerar o EXE sem ter um PC Windows

1. Envie este projeto para um repositório GitHub.
2. Abra a aba `Actions`.
3. Rode o workflow `Build Windows EXE`.
4. Baixe o artefato `separador-de-mandados-PJe-windows`.

## Observações técnicas

- A lógica usada como base veio do script mais completo de separação por grupos e anexos.
- A interface do antigo projeto Swift/macOS não é reaproveitada no Windows; ela foi substituída por uma interface Python própria.
- A saída automática continua sendo `Mandados Separados` ao lado da entrada, salvo quando você escolhe uma pasta fixa de saída.
- O workflow e o script local geram o `.ico` automaticamente antes do empacotamento.

## Windows 11 bloqueia a abertura do .exe (Controle inteligente de aplicativos / SmartScreen)

O executável gerado pelo PyInstaller não possui assinatura digital de um certificado reconhecido pela
Microsoft. Por isso, ao baixar o `.exe` pela internet (ex.: OneDrive, e-mail, navegador), o Windows marca
o arquivo com o "Mark of the Web" e o **Controle inteligente de aplicativos** (ou o SmartScreen) pode
bloquear a execução por falta de reputação, mesmo o app não tendo nenhum problema real.

Opções para quem já baixou o `.exe` e precisa rodar:

1. **Desbloquear o arquivo**: clique com o botão direito no `.exe` → `Propriedades` → marque
   `Desbloquear` (na parte inferior da aba `Geral`) → `Aplicar`/`OK`. Também funciona via PowerShell:
   `Unblock-File -Path "C:\caminho\Separador-de-Mandados-PJe.exe"`.
2. **Desativar o Controle Inteligente de Aplicativos**: abra o menu `Iniciar`, pesquise por
   `Segurança do Windows` e abra o aplicativo. Entre em `Controle de aplicativos e navegador` →
   `Configurações do Controle Inteligente de Aplicativos` → selecione `Desativado` e confirme a
   solicitação do Windows. Esse recurso não permite liberar apenas um aplicativo. Depois de
   desativá-lo, normalmente só é possível ativá-lo novamente redefinindo ou reinstalando o Windows;
   use esta opção somente se você confia na origem do executável.
3. **Assinatura de código (solução definitiva)**: para o Windows parar de exibir esse aviso para todo
   mundo que baixa o app, é necessário assinar o `.exe` com um certificado de assinatura de código
   (idealmente EV) ou usar o Azure Trusted Signing da Microsoft. Sem assinatura, o aviso tende a
   aparecer sempre que o arquivo for baixado da internet, independentemente do quão "seguro" o app seja.


