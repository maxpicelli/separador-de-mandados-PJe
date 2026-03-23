from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import APP_EXE_NAME, APP_NAME, APP_VERSION
from .backend import process_target


class DropListWidget(QListWidget):
    filesDropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        self.filesDropped.emit(paths)
        event.acceptProposedAction()


class Worker(QObject):
    log = Signal(str)
    itemStarted = Signal(str)
    itemFinished = Signal(str, str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, items: list[Path], output_dir: Path | None, bypass: bool) -> None:
        super().__init__()
        self.items = items
        self.output_dir = output_dir
        self.bypass = bypass

    def run(self) -> None:
        last_output = None
        try:
            for item in self.items:
                self.itemStarted.emit(item.name)
                self.log.emit(f"▶️ Iniciando: {item}")
                effective_output = self.output_dir
                last_output = process_target(item, effective_output, bypass_ativo=self.bypass, log=self.log.emit)
                self.itemFinished.emit(item.name, str(last_output))
            self.finished.emit(str(last_output) if last_output else "")
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[Path] = []
        self.output_dir: Path | None = None
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None

        self.setWindowTitle(f"{APP_NAME} for Windows")
        self.resize(1180, 760)

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        title = QLabel(APP_NAME)
        title.setObjectName("heroTitle")
        title.setFont(QFont("Segoe UI", 24, QFont.Black))
        subtitle = QLabel(f"Arraste PDFs ou pastas, escolha a saída e gere o build de {APP_EXE_NAME}.exe para Windows.")
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        body = QGridLayout()
        body.setHorizontalSpacing(18)
        body.setVerticalSpacing(18)

        queue_card = QFrame()
        queue_card.setObjectName("card")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(18, 18, 18, 18)
        queue_layout.setSpacing(12)

        queue_title = QLabel("Fila de entrada")
        queue_title.setObjectName("sectionTitle")
        queue_hint = QLabel("Aceita arquivos PDF e pastas com PDFs.")
        queue_hint.setObjectName("muted")

        self.drop_list = DropListWidget()
        self.drop_list.filesDropped.connect(self.add_items)
        self.drop_list.setMinimumHeight(300)
        self.drop_list.setObjectName("dropList")
        self.drop_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        queue_buttons = QHBoxLayout()
        queue_buttons.setSpacing(10)
        add_files = QPushButton("Adicionar arquivos")
        add_files.clicked.connect(self.pick_files)
        add_folder = QPushButton("Adicionar pasta")
        add_folder.clicked.connect(self.pick_folder)
        remove_selected = QPushButton("Remover selecionados")
        remove_selected.clicked.connect(self.remove_selected_items)
        clear_all = QPushButton("Limpar fila")
        clear_all.clicked.connect(self.clear_items)
        for button in [add_files, add_folder, remove_selected, clear_all]:
            queue_buttons.addWidget(button)

        queue_layout.addWidget(queue_title)
        queue_layout.addWidget(queue_hint)
        queue_layout.addWidget(self.drop_list)
        queue_layout.addLayout(queue_buttons)

        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(18, 18, 18, 18)
        settings_layout.setSpacing(14)

        settings_title = QLabel("Saída e execução")
        settings_title.setObjectName("sectionTitle")
        self.output_label = QLabel("Saída automática: ao lado do arquivo ou pasta de entrada")
        self.output_label.setWordWrap(True)
        self.output_label.setObjectName("pathLabel")

        pick_output = QPushButton("Escolher pasta de saída")
        pick_output.clicked.connect(self.pick_output_dir)
        reset_output = QPushButton("Usar saída automática")
        reset_output.clicked.connect(self.reset_output_dir)
        self.open_output_button = QPushButton("Abrir última saída")
        self.open_output_button.clicked.connect(self.open_output_dir)
        self.open_output_button.setEnabled(False)
        self.bypass_checkbox = QCheckBox("Pular verificação preliminar de permissões")

        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(self.output_label)
        settings_layout.addWidget(pick_output)
        settings_layout.addWidget(reset_output)
        settings_layout.addWidget(self.open_output_button)
        settings_layout.addWidget(self.bypass_checkbox)
        settings_layout.addStretch(1)

        run_card = QFrame()
        run_card.setObjectName("cardAccent")
        run_layout = QVBoxLayout(run_card)
        run_layout.setContentsMargins(18, 18, 18, 18)
        run_layout.setSpacing(12)

        self.status_label = QLabel(f"Pronto para processar com {APP_NAME}")
        self.status_label.setObjectName("statusLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.run_button = QPushButton("Processar agora")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.start_processing)
        copy_log = QPushButton("Copiar log")
        copy_log.clicked.connect(self.copy_log)

        run_layout.addWidget(self.status_label)
        run_layout.addWidget(self.progress)
        run_layout.addWidget(self.run_button)
        run_layout.addWidget(copy_log)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 18, 18, 18)
        log_layout.setSpacing(12)
        log_title = QLabel("Log de processamento")
        log_title.setObjectName("sectionTitle")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_view)

        body.addWidget(queue_card, 0, 0, 2, 2)
        body.addWidget(settings_card, 0, 2)
        body.addWidget(run_card, 1, 2)
        body.addWidget(log_card, 2, 0, 1, 3)
        body.setRowStretch(2, 1)
        body.setColumnStretch(0, 2)
        body.setColumnStretch(1, 2)
        body.setColumnStretch(2, 1)

        root.addLayout(body)
        self.setCentralWidget(central)

        open_action = QAction("Abrir saída", self)
        open_action.triggered.connect(self.open_output_dir)
        self.addAction(open_action)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #f4efe5;
                color: #261b16;
                font-family: 'Segoe UI', 'Arial';
                font-size: 14px;
            }
            QFrame#hero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1f4d3a, stop:0.55 #386641, stop:1 #d6a84f);
                border-radius: 22px;
            }
            QLabel#heroTitle {
                color: #fff7df;
                font-size: 28px;
                font-weight: 900;
            }
            QLabel#heroSubtitle {
                color: rgba(255, 247, 223, 0.9);
                font-size: 14px;
            }
            QFrame#card, QFrame#cardAccent {
                border-radius: 20px;
                border: 1px solid #d2c2a8;
            }
            QFrame#card {
                background: #fffaf1;
            }
            QFrame#cardAccent {
                background: #f2dfb5;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#muted, QLabel#pathLabel {
                color: #6d5d4f;
            }
            QLabel#statusLabel {
                font-size: 18px;
                font-weight: 700;
            }
            QListWidget#dropList, QPlainTextEdit#logView {
                background: #fffdf7;
                border: 1px solid #d9ccb8;
                border-radius: 16px;
                padding: 8px;
            }
            QPushButton {
                background: #ede1c6;
                border: 1px solid #c2a36a;
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #e5d5b0;
            }
            QPushButton#primaryButton {
                background: #1f4d3a;
                color: #fff7df;
                border: 1px solid #17382b;
                font-size: 15px;
            }
            QPushButton#primaryButton:hover {
                background: #2a654c;
            }
            QProgressBar {
                background: #ddcfb6;
                border-radius: 8px;
                min-height: 14px;
            }
            QProgressBar::chunk {
                border-radius: 8px;
                background: #7f4f24;
            }
            QCheckBox {
                spacing: 8px;
            }
            """
        )

    def append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def add_items(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if path in self.items:
                continue
            if path.is_file() and path.suffix.lower() != ".pdf":
                continue
            self.items.append(path)
            item = QListWidgetItem(str(path))
            item.setData(Qt.UserRole, str(path))
            self.drop_list.addItem(item)
        self.status_label.setText(f"{len(self.items)} item(ns) na fila")

    def pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "PDF (*.pdf)")
        if files:
            self.add_items(files)

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta com PDFs")
        if folder:
            self.add_items([folder])

    def pick_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta de saída")
        if not folder:
            return
        self.output_dir = Path(folder)
        self.output_label.setText(f"Saída fixa: {self.output_dir}")

    def reset_output_dir(self) -> None:
        self.output_dir = None
        self.output_label.setText("Saída automática: ao lado do arquivo ou pasta de entrada")

    def remove_selected_items(self) -> None:
        for item in self.drop_list.selectedItems():
            path = Path(item.data(Qt.UserRole))
            if path in self.items:
                self.items.remove(path)
            self.drop_list.takeItem(self.drop_list.row(item))
        self.status_label.setText(f"{len(self.items)} item(ns) na fila")

    def clear_items(self) -> None:
        self.items.clear()
        self.drop_list.clear()
        self.status_label.setText("Fila vazia")

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.log_view.toPlainText())

    def start_processing(self) -> None:
        if not self.items:
            QMessageBox.warning(self, APP_NAME, "Adicione pelo menos um PDF ou pasta antes de processar.")
            return
        if self.worker_thread is not None:
            return

        self.log_view.clear()
        self.progress.setRange(0, 0)
        self.run_button.setEnabled(False)
        self.status_label.setText("Processando...")
        self.open_output_button.setEnabled(False)

        self.worker_thread = QThread(self)
        self.worker = Worker(list(self.items), self.output_dir, self.bypass_checkbox.isChecked())
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self.append_log)
        self.worker.itemStarted.connect(lambda name: self.status_label.setText(f"Processando {name}"))
        self.worker.itemFinished.connect(self._on_item_finished)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()

    def _on_item_finished(self, item_name: str, output_dir: str) -> None:
        self.status_label.setText(f"Concluído: {item_name}")
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_label.setText(f"Última saída: {self.output_dir}")
            self.open_output_button.setEnabled(True)

    def _on_finished(self, output_dir: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.run_button.setEnabled(True)
        self.status_label.setText("Processamento concluído")
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_label.setText(f"Última saída: {self.output_dir}")
            self.open_output_button.setEnabled(True)
        QMessageBox.information(self, APP_NAME, "Processamento concluído com sucesso.")

    def _on_failed(self, message: str) -> None:
        self.append_log(f"❌ ERRO: {message}")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_button.setEnabled(True)
        self.status_label.setText("Falha no processamento")
        QMessageBox.critical(self, APP_NAME, message)

    def _cleanup_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None

    def open_output_dir(self) -> None:
        if not self.output_dir or not self.output_dir.exists():
            QMessageBox.warning(self, APP_NAME, "Nenhuma pasta de saída disponível.")
            return
        QDesktopServices.openUrl(self.output_dir.as_uri())


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Max.1974")
    app.setDesktopFileName(APP_EXE_NAME)

    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
