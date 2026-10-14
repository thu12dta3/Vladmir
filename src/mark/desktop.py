
from __future__ import annotations

import html
import difflib
import base64
import json
import mimetypes
import os
import re
import sqlite3
import stat
import subprocess
import sys
import ssl
import hashlib
import time
import urllib.request
import zipfile
from array import array
from collections import deque
import xml.etree.ElementTree as ET
from http.client import HTTPSConnection
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode
from uuid import uuid4

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, QBuffer, QIODevice, QSize, QEvent, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QIcon, QKeyEvent, QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QDropEvent, QPixmap
from PyQt6.QtMultimedia import QAudioFormat, QAudioOutput, QAudioSource, QMediaDevices, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QGridLayout,
    QSizePolicy, QVBoxLayout, QWidget, QInputDialog, QStackedWidget, QToolButton, QMenu,
)

from . import github
from .package_install import parse_install_request, inspect as inspect_package, install as install_package
from .memory import source_label
from .desktop_theme import STYLESHEET,message_html,safe_web_link
from .desktop_dialogs import WorkerDialog
from .cognition.professor import MODES as STUDY_MODES, StudyPlanStore, build_study_prompt


ROOT = Path(__file__).resolve().parents[2]
API = "http://127.0.0.1:8765"
TOKEN_FILE = Path.home() / ".config/vladmir/mobile.token"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "vladmir"
MEMORY_FILE = STATE_DIR / "conversation.sqlite3"
DESKTOP_CONVERSATIONS_FILE = STATE_DIR / "desktop-conversations.sqlite3"
VOICE_SERVICE = "vladmir-voice.service"
MOBILE_SERVICE = "vladmir-mobile.service"
from .attachment_limits import MAX_ATTACHMENTS, MAX_ATTACHMENT_BYTES, MAX_ATTACHMENTS_TOTAL, MAX_ATTACHMENT_TEXT
TEXT_ATTACHMENT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".xml", ".html", ".py", ".log", ".toml", ".ini", ".cfg"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ICON_DIR = ROOT / "assets/icons/desktop"


def _mark_icon(name: str) -> QIcon:

    return QIcon(str(ICON_DIR / f"{name}.svg"))


def _prepare_attachments(paths: list[Path]) -> list[dict]:

    if len(paths) > MAX_ATTACHMENTS:
        raise ValueError(f"Anexe no máximo {MAX_ATTACHMENTS} arquivos por mensagem.")
    total = 0
    text_total = 0
    prepared = []
    for path in paths:
        info = path.stat()
        if not path.is_file():
            raise ValueError(f"{path.name} não é um arquivo regular.")
        if info.st_size > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"{path.name} excede o limite de 6 MB por arquivo.")
        total += info.st_size
        if total > MAX_ATTACHMENTS_TOTAL:
            raise ValueError("Os anexos juntos não podem passar de 8 MB.")
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            mime = mimetypes.guess_type(path.name)[0]
            if mime not in IMAGE_MIME_TYPES:
                raise ValueError(f"Formato de imagem não suportado: {path.name}.")
            if suffix == ".webp":
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "3", "-"],
                        capture_output=True, timeout=12, check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    raise ValueError(f"Não consegui converter a imagem {path.name}.") from None
                if result.returncode or not result.stdout or len(result.stdout) > MAX_ATTACHMENT_BYTES:
                    raise ValueError(f"Não consegui converter {path.name} para uma imagem compatível.")
                raw_image, mime = result.stdout, "image/jpeg"
            else:
                raw_image = path.read_bytes()
            encoded = base64.b64encode(raw_image).decode("ascii")
            prepared.append({"name": path.name, "mime": mime, "data": encoded})
        elif suffix in TEXT_ATTACHMENT_EXTENSIONS:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"{path.name} não está codificado em UTF-8.") from None
            text_total += len(text)
            if text_total > MAX_ATTACHMENT_TEXT:
                raise ValueError("O texto extraído dos anexos passou de 400 mil caracteres.")
            prepared.append({"name": path.name, "text": text})
        elif suffix == ".pdf":
            try:
                result = subprocess.run(
                    ["pdftotext", "-enc", "UTF-8", str(path), "-"],
                    capture_output=True, text=True, timeout=15, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                raise ValueError(f"Não consegui extrair texto de {path.name}.") from None
            if result.returncode:
                raise ValueError(f"Não consegui abrir o PDF {path.name}.")
            text = result.stdout[:MAX_ATTACHMENT_TEXT + 1]
            text_total += len(text)
            if text_total > MAX_ATTACHMENT_TEXT:
                raise ValueError("O texto extraído dos anexos passou de 400 mil caracteres.")
            prepared.append({"name": path.name, "text": text})
        elif suffix == ".docx":
            try:
                with zipfile.ZipFile(path) as archive:
                    member = archive.getinfo("word/document.xml")
                    if member.file_size > 4 * 1024 * 1024:
                        raise ValueError("Documento DOCX muito grande.")
                    document = archive.read("word/document.xml")
                root = ET.fromstring(document)
                paragraphs = []
                for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    line = "".join(node.text or "" for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
                    if line:
                        paragraphs.append(line)
                text = "\n".join(paragraphs)
            except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError, ValueError):
                raise ValueError(f"Não consegui abrir o documento {path.name}.") from None
            text_total += len(text)
            if text_total > MAX_ATTACHMENT_TEXT:
                raise ValueError("O texto extraído dos anexos passou de 400 mil caracteres.")
            prepared.append({"name": path.name, "text": text})
        else:
            raise ValueError(f"Formato não suportado: {path.name}. Use imagem, PDF, DOCX ou arquivo de texto.")
    return prepared


def _token() -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(TOKEN_FILE, flags)
    with os.fdopen(fd, "r", encoding="utf-8") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PermissionError("A chave local do Vladmir não está com permissões privadas.")
        value = source.read(256).strip()
    if not value:
        raise ValueError("A chave local do Vladmir está vazia.")
    return value


def _request(path: str, payload: dict | None = None, timeout: int = 240):
    headers = {"Authorization": "Bearer " + _token(), "X-Vladmir-Client": "desktop"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(API + path, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def _voice_request(pcm: bytes) -> tuple[bytes, bool]:
    if not 5760 <= len(pcm) <= 960_000 or len(pcm) % 2:
        raise ValueError("A fala precisa ter entre 0,18 e 30 segundos.")
    request = urllib.request.Request(
        API + "/v1/voice/turn", data=pcm, method="POST",
        headers={"Authorization": "Bearer " + _token(), "X-Vladmir-Client": "desktop",
                 "Content-Type": "application/octet-stream"},
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        if response.status != 200 or response.headers.get_content_type() != "audio/wav":
            raise RuntimeError("O Vladmir não devolveu uma resposta de áudio válida.")
        data = response.read(8_000_001)
        if not 44 <= len(data) <= 8_000_000:
            raise RuntimeError("A resposta de áudio do Vladmir está vazia ou excede o limite.")
        return data, response.headers.get("X-Vladmir-Sleep") == "1"


def _service(action: str, unit: str) -> str:
    result = subprocess.run(
        ["systemctl", "--user", action, unit], capture_output=True, text=True,
        timeout=30, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"Não foi possível {action} {unit}.")
    return result.stdout.strip()


def _mobile_pairing() -> dict:

    from .device_auth import DeviceRegistry
    result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=8, check=True)
    hostname = json.loads(result.stdout)["Self"]["DNSName"].rstrip(".")
    if not hostname.endswith(".ts.net"):
        raise RuntimeError("O nome Tailscale do computador não está disponível.")
    connection = HTTPSConnection(hostname, 443, timeout=8, context=ssl.create_default_context())
    try:
        connection.connect()
        if connection.sock is None or connection.sock.version() != "TLSv1.3":
            raise RuntimeError("A conexão com o celular exige TLS 1.3.")
        pin = hashlib.sha256(connection.sock.getpeercert(binary_form=True)).hexdigest()
        connection.request("GET", "/v1/pair/status", headers={"X-Vladmir-Device": "probe"})
        response = connection.getresponse()
        if response.status != 200 or json.loads(response.read(1024)).get("status") != "unknown":
            raise RuntimeError("A API móvel não respondeu como esperado no HTTPS do Tailscale.")
    finally:
        connection.close()
    registry = DeviceRegistry()
    try:
        code = registry.open_enrollment()
    finally:
        registry.close()
    return {"url": "https://" + hostname, "code": code, "pin": pin}


class Task(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, operation: Callable, parent=None):
        super().__init__(parent)
        self.operation = operation
        self._result = None
        self._error = None
        self.finished.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    def run(self):
        try:
            self._result = self.operation()
        except Exception as exc:
            self._error = str(exc) or type(exc).__name__

    @pyqtSlot()
    def _deliver(self):


        if self._error is None:
            self.completed.emit(self._result)
        else:
            self.failed.emit(self._error)


class Composer(QPlainTextEdit):
    send_requested = pyqtSignal()
    files_dropped = pyqtSignal(list)
    drag_hover_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            self.drag_hover_changed.emit(True)
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.drag_hover_changed.emit(False)
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.drag_hover_changed.emit(False)
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class AgendaDialog(WorkerDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workers: set[Task] = set()
        self.setWindowTitle("Agenda do Vladmir")
        self.setMinimumSize(480, 420)
        layout = QVBoxLayout(self)
        intro = QLabel("Compromissos e lembretes compartilhados com o celular e a voz do Vladmir.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.items = QListWidget()
        layout.addWidget(self.items, 1)
        row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Ex.: me lembre de buscar encomenda amanhã às 16h")
        self.entry.returnPressed.connect(self.add_item)
        row.addWidget(self.entry, 1)
        self.add_button = QPushButton("Adicionar")
        self.add_button.clicked.connect(self.add_item)
        row.addWidget(self.add_button)
        layout.addLayout(row)
        self.refresh()

    def refresh(self):
        self.items.clear()

        def load():
            _, body = _request("/v1/agenda", timeout=5)
            return json.loads(body).get("items", [])

        def done(items):
            if not items:
                self.items.addItem("Sua agenda está vazia.")
                return
            from datetime import datetime
            for item in items:
                if item["due_at"]:
                    when = datetime.fromisoformat(item["due_at"]).astimezone().strftime("%d/%m %H:%M")
                    line = f"{when}  ·  {item['title']}"
                else:
                    line = f"Sem horário  ·  {item['title']}"
                if item["completed"]:
                    line = "✓  " + line
                self.items.addItem(line)

        def failed(message):
            self.items.addItem("Não consegui carregar a agenda: " + message)

        self._start_task(load, done, failed)

    def add_item(self):
        command = self.entry.text().strip()
        if not command:
            return
        self.add_button.setDisabled(True)
        self.entry.setDisabled(True)

        def add():
            _, body = _request("/v1/chat/completions", {
                "model": "vladmir", "stream": False,
                "messages": [{"role": "user", "content": command}],
            })
            return json.loads(body)["choices"][0]["message"]["content"]

        def done(reply):
            self.add_button.setDisabled(False)
            self.entry.setDisabled(False)
            self.entry.clear()
            self.items.insertItem(0, reply)
            self.refresh()

        def failed(message):
            self.add_button.setDisabled(False)
            self.entry.setDisabled(False)
            QMessageBox.warning(self, "Agenda", "Não consegui salvar esse item.\n\n" + message)

        self._start_task(add, done, failed)

    def _start_task(self, operation, success, failure):
        worker = Task(operation, self)
        self.workers.add(worker)
        worker.completed.connect(lambda result, w=worker: self._finish(w, success, result))
        worker.failed.connect(lambda message, w=worker: self._finish(w, failure, message))
        worker.start()

    def _finish(self, worker, callback, result):
        self.workers.discard(worker)
        callback(result)
        worker.deleteLater()

    def closeEvent(self, event):
        if self.workers:
            event.ignore()
            return
        event.accept()


class CallDialog(WorkerDialog):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chamada com Vladmir")
        self.setMinimumSize(390, 330)
        self.active = False
        self.closing_when_idle = False
        self.worker = None
        self.source = None
        self.microphone = None
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.errorOccurred.connect(self._playback_error)
        self.player.mediaStatusChanged.connect(self._media_status)
        self.devices = QMediaDevices(self)
        self.devices.audioOutputsChanged.connect(self._refresh_audio_outputs)
        self.audio_buffer = None
        self.sleep_after_playback = False
        self.pending = bytearray()
        self.pre_frames = deque(maxlen=3)
        self.samples = bytearray()
        self.heard = False
        self.silent_frames = 0
        self.elapsed_frames = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("◉  Vladmir")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #bdf5f6; font-size: 29px; font-weight: bold;")
        layout.addWidget(title)
        self.state = QLabel("Pronto para conversar")
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.setWordWrap(True)
        self.state.setStyleSheet("font-size: 19px; color: #e6edf3;")
        layout.addWidget(self.state, 1)
        self.detail = QLabel("Fale normalmente. O Vladmir responde pelo fone ou alto-falante do PC.")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("color: #91a4b4;")
        layout.addWidget(self.detail)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Saída de áudio"))
        self.output_selector = QComboBox()
        self.output_selector.setToolTip("Escolha onde o Vladmir reproduz a resposta falada")
        self.output_selector.currentIndexChanged.connect(self._select_audio_output)
        output_row.addWidget(self.output_selector, 1)
        layout.addLayout(output_row)
        self.toggle = QPushButton("Iniciar chamada")
        self.toggle.clicked.connect(self.toggle_call)
        layout.addWidget(self.toggle)
        self.interrupt = QPushButton("Interromper resposta e falar")
        self.interrupt.clicked.connect(self._interrupt_playback)
        self.interrupt.hide()
        layout.addWidget(self.interrupt)
        self.setStyleSheet("QDialog { background: #0c1219; } QPushButton { background: #143943; "
                           "color: #bdf5f6; border: 1px solid #20525a; border-radius: 13px; padding: 12px; }")
        self._refresh_audio_outputs()

    def _refresh_audio_outputs(self):
        outputs = QMediaDevices.audioOutputs()
        current_id = bytes(self.audio_output.device().id())
        self.output_selector.blockSignals(True)
        self.output_selector.clear()
        for device in outputs:
            self.output_selector.addItem(device.description(), bytes(device.id()))
        self.output_selector.setEnabled(bool(outputs))
        index = self.output_selector.findData(current_id)
        if index < 0 and outputs:
            default_id = bytes(QMediaDevices.defaultAudioOutput().id())
            index = self.output_selector.findData(default_id)
        if index < 0 and outputs:
            index = 0
        if index >= 0:
            self.output_selector.setCurrentIndex(index)
        self.output_selector.blockSignals(False)
        if index >= 0:
            self._select_audio_output(index)
        else:
            self.output_selector.addItem("Nenhuma saída disponível")

    def _select_audio_output(self, index):
        device_id = self.output_selector.itemData(index) if index >= 0 else None
        if device_id is None:
            return
        device = next((item for item in QMediaDevices.audioOutputs()
                       if bytes(item.id()) == bytes(device_id)), None)
        if device is None:
            self._refresh_audio_outputs()
            return
        self.audio_output.setDevice(device)
        if self.active:
            self.detail.setText(f"Saída: {device.description()}. A chamada continua ativa.")

    def _playback_error(self, error, message):
        if error == QMediaPlayer.Error.NoError and not message:
            return
        self.interrupt.hide()
        self.audio_buffer = None
        self.state.setText("Falha ao reproduzir a resposta")
        detail = message.strip() if message and message.strip() else "O dispositivo de saída recusou o áudio."
        self.detail.setText(f"{detail} Escolha outra saída de áudio e tente falar novamente.")
        if self.active:
            QTimer.singleShot(1200, self._listen)

    def toggle_call(self):
        if self.active:
            self._stop_call()
        else:
            self.active = True
            self.toggle.setText("Encerrar chamada")
            self.state.setText("Conferindo conexão com o Vladmir…")
            self.detail.setText("O microfone só será ativado depois que o servidor responder.")
            self.worker = Task(lambda: _request("/health", timeout=8), self)
            self.worker.completed.connect(self._connection_ready)
            self.worker.failed.connect(self._connection_failed)
            self.worker.start()

    def _finish_connection_check(self):
        worker, self.worker = self.worker, None
        if worker is not None:
            worker.deleteLater()
        if self.closing_when_idle:
            self.close()
            return False
        return self.active

    def _connection_ready(self, result):
        if not self._finish_connection_check():
            return
        status, _ = result
        if status == 200:
            self._listen()
        else:
            self._connection_failed(f"O servidor respondeu HTTP {status}.")

    def _connection_failed(self, message):
        if self.worker is not None:
            worker, self.worker = self.worker, None
            worker.deleteLater()
        if self.closing_when_idle:
            self.close()
            return
        self.active = False
        self.toggle.setText("Tentar chamada novamente")
        self.state.setText("Chat indisponível")
        self.detail.setText("Verifique a conexão com o servidor Vladmir e tente novamente. " + str(message))

    def _listen(self):
        if not self.active or self.closing_when_idle:
            return
        device = QMediaDevices.defaultAudioInput()
        audio_format = QAudioFormat()
        audio_format.setSampleRate(16_000)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if device.isNull() or not device.isFormatSupported(audio_format):
            self._stop_call("Microfone indisponível ou sem suporte a 16 kHz mono.")
            return
        self.pending.clear()
        self.pre_frames.clear()
        self.samples.clear()
        self.heard = False
        self.silent_frames = 0
        self.elapsed_frames = 0
        self.source = QAudioSource(device, audio_format, self)
        self.microphone = self.source.start()
        if self.microphone is None:
            self._stop_call("Não consegui abrir o microfone do PC.")
            return
        self.microphone.readyRead.connect(self._audio_ready)
        self.state.setText("Ouvindo…")
        self.detail.setText("Fale naturalmente; o Vladmir escuta até você fazer uma pausa.")

    def _audio_ready(self):
        if not self.active or self.microphone is None or self.worker is not None:
            return
        self.pending.extend(bytes(self.microphone.readAll()))
        while len(self.pending) >= 3200:
            frame = bytes(self.pending[:3200])
            del self.pending[:3200]
            values = array("h")
            values.frombytes(frame)
            energy = sum(abs(sample) for sample in values) // len(values)
            voice = energy > 480
            self.elapsed_frames += 1
            if not self.heard:
                self.pre_frames.append(frame)
                if voice:
                    self.heard = True
                    for previous in self.pre_frames:
                        self.samples.extend(previous)
                    self.pre_frames.clear()
            else:
                self.samples.extend(frame)
                self.silent_frames = 0 if voice else self.silent_frames + 1
                if (self.silent_frames >= 5 and len(self.samples) >= 5760) or len(self.samples) >= 480_000:
                    self._send_turn(bytes(self.samples))
                    return
            if self.elapsed_frames >= 100 and not self.heard:
                self.elapsed_frames = 0
                self.pre_frames.clear()

    def _stop_microphone(self):
        if self.source is not None:
            self.source.stop()
            self.source.deleteLater()
            self.source = None
            self.microphone = None

    def _send_turn(self, pcm: bytes):
        self._stop_microphone()
        self.state.setText("Vladmir está pensando…")
        self.detail.setText("Aguarde a resposta da conversa.")
        self.worker = Task(lambda: _voice_request(pcm), self)
        self.worker.completed.connect(self._received)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _received(self, result):
        self.worker.deleteLater()
        self.worker = None
        if self.closing_when_idle:
            self.close()
            return
        if not self.active:
            return
        wav, self.sleep_after_playback = result
        self.audio_buffer = QBuffer(self)
        self.audio_buffer.setData(wav)
        self.audio_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.player.setSourceDevice(self.audio_buffer, QUrl("file:///vladmir-answer.wav"))
        self.state.setText("Vladmir está falando…")
        self.detail.setText("Você pode interromper para voltar a falar.")
        self.interrupt.show()
        self.player.play()

    def _failed(self, message):
        self.worker.deleteLater()
        self.worker = None
        if self.closing_when_idle:
            self.close()
            return
        self.state.setText("Não consegui concluir a fala")
        self.detail.setText(message)
        if self.active:
            QTimer.singleShot(1800, self._listen)

    def _media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.active:
            self.interrupt.hide()
            self.audio_buffer = None
            if self.sleep_after_playback:
                self._stop_call("Vladmir descansando. Chamada encerrada.")
            else:
                self._listen()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia and self.active:
            self._playback_error(self.player.error(), self.player.errorString() or "O formato do áudio não foi reconhecido.")

    def _interrupt_playback(self):
        self.player.stop()
        self.interrupt.hide()
        self.audio_buffer = None
        self._listen()

    def _stop_call(self, message="Chamada encerrada"):
        self.active = False
        self._stop_microphone()
        self.player.stop()
        self.interrupt.hide()
        self.audio_buffer = None
        self.toggle.setText("Iniciar chamada")
        self.state.setText(message)

    def closeEvent(self, event):
        self._stop_call()
        if self.worker is not None:
            self.closing_when_idle = True
            self.state.setText("Encerrando a chamada…")
            event.ignore()
            return
        event.accept()


class EmailComposerDialog(QDialog):


    def __init__(self, body: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preparar email no Tuta")
        self.setMinimumSize(560, 520)
        layout = QVBoxLayout(self)
        hint = QLabel("Confira destinatário, assunto e texto. O Tuta abrirá o rascunho para você revisar e enviar.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(QLabel("Para"))
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("pessoa@exemplo.com")
        layout.addWidget(self.recipient)
        layout.addWidget(QLabel("Assunto"))
        self.subject = QLineEdit()
        layout.addWidget(self.subject)
        layout.addWidget(QLabel("Mensagem"))
        self.body = QPlainTextEdit()
        self.body.setPlainText(body)
        self.body.setPlaceholderText("Escreva a mensagem ou use a resposta mais recente do Vladmir.")
        layout.addWidget(self.body, 1)
        self.open_button = QPushButton("Abrir rascunho no Tuta")
        self.open_button.clicked.connect(self.open_draft)
        layout.addWidget(self.open_button)

    def open_draft(self):
        recipient = self.recipient.text().strip()
        if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", recipient):
            QMessageBox.warning(self, "Email", "Informe um único endereço de email válido.")
            return
        query = urlencode({"subject": self.subject.text().strip(), "body": self.body.toPlainText()},
                          quote_via=quote)
        url = QUrl("mailto:" + quote(recipient, safe="@._+-") + "?" + query)
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self, "Email", "Não há um aplicativo padrão configurado para abrir rascunhos mailto. "
                "Defina o Tuta Mail como manipulador de links mailto no Linux e tente novamente.",
            )
            return
        self.accept()


class GitHubDialog(WorkerDialog):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub do Vladmir")
        self.setMinimumSize(760, 600)
        self.resize(900, 700)
        self.workers: set[Task] = set()
        self.loaded_identity: tuple[str, str, str] | None = None
        self.loaded_sha: str | None = None
        self.loaded_content: str | None = None
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Veja repositórios e arquivos acessíveis pela sua conta GitHub. "
            "Ao salvar, o Vladmir cria um commit no branch selecionado."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.account_label = QLabel("Verificando a conta GitHub…")
        layout.addWidget(self.account_label)

        layout.addWidget(QLabel("Repositório (dono/nome)"))
        repo_row = QHBoxLayout()
        self.repo = QComboBox()
        self.repo.setEditable(True)
        self.repo.addItem("thu12dta3/Vladmir")
        repo_row.addWidget(self.repo, 1)
        self.refresh_repos_button = QPushButton("Atualizar lista")
        self.refresh_repos_button.clicked.connect(self.refresh_repositories)
        repo_row.addWidget(self.refresh_repos_button)
        layout.addLayout(repo_row)

        layout.addWidget(QLabel("Branch"))
        self.branch = QLineEdit("main")
        layout.addWidget(self.branch)
        layout.addWidget(QLabel("Caminho do arquivo"))
        path_row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("Ex.: README.md ou src/app.py")
        path_row.addWidget(self.path, 1)
        self.load_button = QPushButton("Abrir arquivo")
        self.load_button.clicked.connect(self.load_file)
        path_row.addWidget(self.load_button)
        layout.addLayout(path_row)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Abra um arquivo de texto para revisar ou editar.")
        layout.addWidget(self.editor, 1)

        layout.addWidget(QLabel("Mensagem do commit"))
        self.commit_message = QLineEdit("Atualizar arquivo pelo Vladmir")
        layout.addWidget(self.commit_message)
        footer = QHBoxLayout()
        self.status = QLabel("Os arquivos permanecem no GitHub; nenhum token é copiado para o Vladmir.")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.save_button = QPushButton("Revisar e salvar no GitHub")
        self.save_button.clicked.connect(self.save_file)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self.refresh_repositories()

    def _start(self, operation, success):
        worker = Task(operation, self)
        self.workers.add(worker)
        worker.completed.connect(lambda value, w=worker: self._finish(w, success, value))
        worker.failed.connect(lambda message, w=worker: self._fail(w, message))
        worker.start()

    def _finish(self, worker, callback, value):
        self.workers.discard(worker)
        worker.deleteLater()
        callback(value)

    def _fail(self, worker, message):
        self.workers.discard(worker)
        worker.deleteLater()
        for widget in (self.refresh_repos_button, self.load_button, self.save_button,
                       self.repo, self.branch, self.path, self.editor, self.commit_message):
            widget.setDisabled(False)
        self.status.setText("Não consegui acessar o GitHub.")
        QMessageBox.warning(self, "GitHub", message)

    def refresh_repositories(self):
        self.refresh_repos_button.setDisabled(True)
        self.account_label.setText("Conectando ao GitHub…")

        def load():
            return github.account(), github.repositories()

        def done(result):
            account, repositories = result
            self.account_label.setText("Conectado como " + account)
            current = self.repo.currentText().strip()
            self.repo.clear()
            for item in repositories:
                self.repo.addItem(item["name"], item["branch"])
            if current:
                index = self.repo.findText(current)
                if index >= 0:
                    self.repo.setCurrentIndex(index)
                else:
                    self.repo.setEditText(current)
            elif self.repo.count():
                self.repo.setCurrentIndex(0)
            self.refresh_repos_button.setDisabled(False)
            self.status.setText(f"{len(repositories)} repositórios disponíveis.")

        self._start(load, done)

    def _target(self):
        return (self.repo.currentText().strip(), self.branch.text().strip(), self.path.text().strip())

    def load_file(self):
        repo, branch, path = self._target()
        self.load_button.setDisabled(True)

        def done(result):
            self.loaded_sha, content = result
            self.loaded_identity = (repo, branch, path)
            self.loaded_content = content
            self.editor.setPlainText(content)
            self.load_button.setDisabled(False)
            self.status.setText(f"Arquivo aberto · revisão {self.loaded_sha[:8]}")

        self._start(lambda: github.read_file(repo, branch, path), done)

    def save_file(self):
        repo, branch, path = self._target()
        if not self.loaded_sha or self.loaded_identity != (repo, branch, path):
            QMessageBox.information(self, "GitHub", "Abra o arquivo antes de salvar para proteger alterações recentes.")
            return
        content = self.editor.toPlainText()
        if content == self.loaded_content:
            QMessageBox.information(self, "GitHub", "O arquivo não tem alterações para salvar.")
            return
        if not content.strip():
            answer = QMessageBox.question(
                self, "Arquivo vazio", "O conteúdo ficará vazio. Quer continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        message = self.commit_message.text().strip()
        preview = "".join(difflib.unified_diff(
            (self.loaded_content or "").splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile="a/" + path, tofile="b/" + path,
        ))
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Revisar alteração no GitHub")
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setText(
            f"Criar um commit em {repo}, branch {branch}, arquivo {path}?\n\n"
            "Confira o resumo da alteração antes de continuar."
        )
        confirm.setDetailedText(preview[:20000] + ("\n… diff cortado" if len(preview) > 20000 else ""))
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        confirm.button(QMessageBox.StandardButton.Yes).setText("Criar commit")
        confirm.button(QMessageBox.StandardButton.No).setText("Cancelar")
        answer = confirm.exec()
        if answer != QMessageBox.StandardButton.Yes:
            return
        sha = self.loaded_sha
        for widget in (self.refresh_repos_button, self.load_button, self.save_button,
                       self.repo, self.branch, self.path, self.editor, self.commit_message):
            widget.setDisabled(True)

        def save():
            commit_url = github.update_file(repo, branch, path, sha, message, content)
            new_sha, refreshed = github.read_file(repo, branch, path)
            return commit_url, new_sha, refreshed

        def done(result):
            commit_url, self.loaded_sha, saved_content = result
            self.loaded_identity = (repo, branch, path)
            self.loaded_content = saved_content
            self.editor.setPlainText(saved_content)
            for widget in (self.refresh_repos_button, self.load_button, self.save_button,
                           self.repo, self.branch, self.path, self.editor, self.commit_message):
                widget.setDisabled(False)
            self.status.setText("Commit criado: " + commit_url)
            QMessageBox.information(self, "GitHub", "Arquivo salvo no GitHub.\n\n" + commit_url)

        self._start(save, done)

    def closeEvent(self, event):
        if self.workers:
            self.status.setText("Aguarde a tarefa do GitHub terminar para fechar esta janela.")
            event.ignore()
            return
        event.accept()


class MobileDevicesDialog(WorkerDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Celular e segurança · Vladmir")
        self.resize(600, 650)
        self.worker = None
        self.pair_expiry_timer = QTimer(self)
        self.pair_expiry_timer.setSingleShot(True)
        self.pair_expiry_timer.timeout.connect(self._expire_pairing)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Conexão protegida do Vladmir Mobile"))
        self.status = QLabel("Pareamento fechado. Abra um código temporário quando o celular estiver pronto.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.qr = QLabel()
        self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr.setMinimumHeight(230)
        layout.addWidget(self.qr)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(120)
        layout.addWidget(self.details)
        self.pair_button = QPushButton("Abrir pareamento por 5 minutos")
        self.pair_button.clicked.connect(self.open_pairing)
        layout.addWidget(self.pair_button)
        layout.addWidget(QLabel("Aparelhos registrados no PC"))
        self.devices_status = QLabel()
        self.devices_status.setWordWrap(True)
        layout.addWidget(self.devices_status)
        self.devices = QListWidget()
        layout.addWidget(self.devices)
        controls = QHBoxLayout()
        for label, callback in (("Atualizar", self.refresh_devices),
                                ("Aprovar", self.approve), ("Revogar", self.revoke)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.refresh_devices()
        self.devices_timer = QTimer(self)
        self.devices_timer.timeout.connect(self.refresh_devices)
        self.devices_timer.start(3000)

    def refresh_devices(self):
        from .device_auth import DeviceRegistry
        selected = self.devices.currentItem()
        selected_id = selected.data(Qt.ItemDataRole.UserRole)[0] if selected else None
        registry = DeviceRegistry()
        try:
            rows = registry.list_devices()
            lockdown = registry.lockdown()
        finally:
            registry.close()
        self.devices.clear()
        for device_id, name, status in rows:
            item = QListWidgetItem(f"{status.upper()} · {name} · {device_id[:16]}…")
            item.setData(Qt.ItemDataRole.UserRole, (device_id, status))
            self.devices.addItem(item)
            if device_id == selected_id:
                self.devices.setCurrentItem(item)
        self.devices_status.setText("Vladmir em lockdown: acesso móvel bloqueado." if lockdown else
                                    f"{len(rows)} aparelho(s) registrados. Apenas os aprovados podem criar sessão.")

    def open_pairing(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.pair_expiry_timer.stop()
        self.qr.clear()
        self.details.clear()
        self.status.setText("Verificando HTTPS e identidade Tailscale…")
        self.pair_button.setDisabled(True)
        self.worker = Task(_mobile_pairing, self)
        self.worker.completed.connect(self._show_pairing)
        self.worker.failed.connect(lambda message: self.status.setText("Pareamento não aberto: " + message))
        self.worker.finished.connect(lambda: self.pair_button.setEnabled(True))
        self.worker.start()

    def _show_pairing(self, data):
        payload = json.dumps(data, separators=(",", ":"))
        self.details.setPlainText(f"Endereço: {data['url']}\nCódigo temporário: {data['code']}\nIdentidade SHA-256: {data['pin']}")
        result = subprocess.run(["qrencode", "-t", "PNG", "-o", "-"],
                                input=payload.encode("utf-8"), capture_output=True,
                                timeout=5, check=False)
        image = QPixmap()
        if result.returncode == 0 and image.loadFromData(result.stdout):
            self.qr.setPixmap(image.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
            self.status.setText("Leia o QR no celular. Depois selecione o aparelho PENDING e aprove aqui.")
        else:
            self.qr.clear()
            self.status.setText("Não consegui gerar o QR. Informe os dados acima manualmente no celular.")
        self.refresh_devices()
        self.pair_expiry_timer.start(300_000)

    def _expire_pairing(self):
        self.qr.clear()
        self.details.clear()
        self.status.setText("O pareamento expirou. Abra outro código para conectar um aparelho.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Aguarde a verificação da conexão antes de fechar esta janela.")
            event.ignore()
            return
        self.devices_timer.stop()
        self.pair_expiry_timer.stop()
        self.qr.clear()
        self.details.clear()
        event.accept()

    def _selected(self):
        item = self.devices.currentItem()
        if item is None:
            QMessageBox.information(self, "Vladmir Mobile", "Selecione um aparelho na lista.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def approve(self):
        selected = self._selected()
        if selected is None:
            return
        device_id, status = selected
        if status != "pending":
            QMessageBox.information(self, "Vladmir Mobile", "Somente um aparelho pendente pode ser aprovado.")
            return
        if QMessageBox.question(self, "Aprovar aparelho", f"Autorizar este aparelho?\n{device_id}") != QMessageBox.StandardButton.Yes:
            return
        from .device_auth import DeviceRegistry
        registry = DeviceRegistry()
        try:
            approved = registry.update_device(device_id, "authorized")
        finally:
            registry.close()
        self.refresh_devices()
        self.status.setText("Aparelho aprovado; toque ↻ no celular." if approved else "O aparelho não estava mais pendente.")

    def revoke(self):
        selected = self._selected()
        if selected is None:
            return
        device_id, status = selected
        if status == "revoked":
            return
        if QMessageBox.question(self, "Revogar aparelho", f"Cortar imediatamente o acesso deste aparelho?\n{device_id}") != QMessageBox.StandardButton.Yes:
            return
        from .device_auth import DeviceRegistry
        registry = DeviceRegistry()
        try:
            registry.update_device(device_id, "revoked")
        finally:
            registry.close()
        self.refresh_devices()


class MarkWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vladmir")
        self.setWindowIcon(QIcon(str(ROOT / "assets/vladmir.svg")))
        self.setMinimumSize(900, 620)
        self.resize(1280, 850)
        self.tasks: set[Task] = set()
        self.shared_session_id = uuid4().hex
        self.current_specialization = "general"
        self.current_conversation_id = "general-main"
        self.specialization_conversations = {"general": "general-main"}
        self._conversation_switching = False
        self.current_project_id: str | None = None
        self.current_task_id: str | None = None
        self._engineer_profile_restore = None
        self.engineer_status_loading = False
        self.evolution_status_loading = False
        self.busy = False
        self.last_assistant_reply = ""
        self.history_signature = None
        self.follow_latest=True
        self.attachments: list[Path] = []
        self.voice_active = False
        self.closing_when_idle = False
        self._build_ui()
        self._load_history()
        self._set_style()
        QTimer.singleShot(0, self.input.setFocus)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(6000)
        self.history_timer = QTimer(self)
        self.history_timer.timeout.connect(self._sync_history)
        self.history_timer.start(6000)
        QTimer.singleShot(100, self.refresh_status)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(15, 19, 15, 14)
        side_layout.setSpacing(5)
        brand_row = QHBoxLayout()
        brand_icon = QLabel()
        brand_icon.setPixmap(_mark_icon("brand").pixmap(QSize(25, 25)))
        brand_row.addWidget(brand_icon)
        brand = QLabel("Vladmir")
        brand.setObjectName("brand")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        side_layout.addLayout(brand_row)
        tagline = QLabel("ASSISTENTE PESSOAL")
        tagline.setObjectName("brandCaption")
        side_layout.addWidget(tagline)
        side_layout.addSpacing(24)
        side_layout.addWidget(self._section_label("CONVERSAR"))
        self.shared_chat_button = QPushButton("Geral")
        self.shared_chat_button.setIcon(_mark_icon("chat"))
        self.shared_chat_button.setObjectName("navButtonActive")
        self.shared_chat_button.setIconSize(QSize(17, 17))
        self.shared_chat_button.setFixedHeight(42)
        self.shared_chat_button.setToolTip("Conversa compartilhada, chamada e visão")
        self.shared_chat_button.clicked.connect(lambda: self.open_area("general"))
        side_layout.addWidget(self.shared_chat_button)
        self.engineer_button = self._nav_button("Engenheiro", "github")
        self.engineer_button.clicked.connect(lambda: self.open_area("engineer"))
        side_layout.addWidget(self.engineer_button)
        self.professor_button = self._nav_button("Professor", "chat")
        self.professor_button.clicked.connect(lambda: self.open_area("professor"))
        side_layout.addWidget(self.professor_button)
        self.library_nav_button = self._nav_button("Biblioteca", "attach")
        self.library_nav_button.clicked.connect(lambda: self.open_area("library"))
        self.evolution_nav_button = self._nav_button("Evolução", "evolution")
        self.evolution_nav_button.clicked.connect(lambda: self.open_area("evolution"))
        self.settings_nav_button = self._nav_button("Configurações", "menu")
        self.settings_nav_button.clicked.connect(lambda: self.open_area("settings"))
        self.area_buttons = {
            "general": self.shared_chat_button,
            "engineer": self.engineer_button,
            "professor": self.professor_button,
            "library": self.library_nav_button,
            "evolution": self.evolution_nav_button,
            "settings": self.settings_nav_button,
        }
        side_layout.addSpacing(20)
        side_layout.addWidget(self._section_label("SEU ESPAÇO"))
        side_layout.addWidget(self.library_nav_button)
        side_layout.addWidget(self.evolution_nav_button)
        self.tools_button = QToolButton()
        self.tools_button.setObjectName("toolsButton")
        self.tools_button.setText("Ferramentas")
        self.tools_button.setIcon(_mark_icon("menu"))
        self.tools_button.setIconSize(QSize(17, 17))
        self.tools_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.tools_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.tools_button.setFixedHeight(37)
        self.tools_button.setAccessibleName("Abrir ferramentas do Vladmir")
        self.tools_menu = QMenu(self.tools_button)
        plugins_action = self.tools_menu.addAction(_mark_icon("menu"), "Plugins…")
        plugins_action.triggered.connect(self.open_plugins)
        ide_action = self.tools_menu.addAction(_mark_icon("github"), "IDEs JetBrains · MCP…")
        ide_action.triggered.connect(self.open_jetbrains)
        sentinel_action = self.tools_menu.addAction(_mark_icon("sentinel"), "Antivírus e ameaças · Sentinel…")
        sentinel_action.triggered.connect(self.open_sentinel)
        self.tools_menu.addSeparator()
        self.voice_button = self.tools_menu.addAction("Escuta por voz")
        self.voice_button.setIcon(_mark_icon("microphone"))
        self.voice_button.triggered.connect(self.toggle_voice)
        for label, icon, operation in (
            ("Agenda e lembretes", "calendar", self.open_agenda),
            ("E-mail · Tuta", "mail", self.open_email_composer),
            ("Código · GitHub", "github", self.open_github),
        ):
            action = self.tools_menu.addAction(_mark_icon(icon), label)
            action.triggered.connect(operation)
        self.tools_menu.addSeparator()
        for label, icon, operation in (
            ("Tarefas do Engineer", "github", self.open_missions),
            ("Dispositivos e segurança", "device", self.open_mobile_devices),
            ("Visão ao vivo", "camera", self.open_vision),
            ("Verificar câmera", "camera", self.test_camera),
        ):
            action = self.tools_menu.addAction(_mark_icon(icon), label)
            action.triggered.connect(operation)
        self.tools_menu.addSeparator()
        self.connect_button = self.tools_menu.addAction("Iniciar Vladmir")
        self.connect_button.setIcon(_mark_icon("power"))
        self.connect_button.triggered.connect(self.start_mark)
        clear_action = self.tools_menu.addAction(_mark_icon("trash"), "Limpar conversa")
        clear_action.triggered.connect(self.clear_memory)
        self.tools_button.setMenu(self.tools_menu)
        side_layout.addSpacing(5)
        side_layout.addWidget(self.tools_button)
        side_layout.addStretch(1)
        side_layout.addWidget(self.settings_nav_button)
        side_layout.addSpacing(9)
        self.api_status = self._status_row("Vladmir", "Verificando…")
        self.voice_status = self._status_row("Microfone", "Verificando…")
        side_layout.addWidget(self.api_status)
        side_layout.addWidget(self.voice_status)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setFixedWidth(224)
        self.sidebar_scroll.setWidget(side)
        layout.addWidget(self.sidebar_scroll)

        content = QWidget()
        content.setObjectName("contentArea")
        main = QVBoxLayout(content)
        main.setContentsMargins(42, 22, 42, 20)
        main.setSpacing(13)
        top = QHBoxLayout()
        top.setSpacing(12)
        toggle = QPushButton()
        toggle.setObjectName("iconButton")
        toggle.setIcon(_mark_icon("menu"))
        toggle.setIconSize(QSize(19, 19))
        toggle.setToolTip("Mostrar ou ocultar o menu")
        toggle.setAccessibleName("Mostrar ou ocultar o menu")
        toggle.clicked.connect(lambda: self.sidebar_scroll.setVisible(not self.sidebar_scroll.isVisible()))
        top.addWidget(toggle)
        heading = QVBoxLayout()
        heading.setSpacing(4)
        title = QLabel("Conversa")
        title.setObjectName("title")
        heading.addWidget(title)
        self.connection_label = QLabel("Verificando conexão…")
        self.connection_label.setObjectName("connectionStatus")
        heading.addWidget(self.connection_label)
        top.addLayout(heading)
        self.engineer_chat_badge = QLabel("ENGINEER · QWEN CODER")
        self.engineer_chat_badge.setObjectName("engineerBadge")
        self.engineer_chat_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.engineer_chat_badge.hide()
        top.addWidget(self.engineer_chat_badge)
        self.conversation_selector = QComboBox()
        self.conversation_selector.setObjectName("chatSelector")
        self.conversation_selector.setMinimumWidth(190)
        self.conversation_selector.setToolTip("Conversas separadas por perfil; memórias salvas continuam compartilhadas")
        self.conversation_selector.currentIndexChanged.connect(self._select_conversation_from_header)
        self.conversation_selector.hide()
        top.addWidget(self.conversation_selector)
        self.new_conversation_button = QPushButton("Nova conversa")
        self.new_conversation_button.setObjectName("headerAction")
        self.new_conversation_button.clicked.connect(self._create_specialized_conversation)
        self.new_conversation_button.hide()
        top.addWidget(self.new_conversation_button)
        top.addStretch()
        call_shortcut = QPushButton("Chamada")
        call_shortcut.setObjectName("headerAction")
        call_shortcut.setIcon(_mark_icon("call"))
        call_shortcut.setIconSize(QSize(17, 17))
        call_shortcut.setToolTip("Abrir chamada dentro do app")
        call_shortcut.clicked.connect(self.open_call)
        top.addWidget(call_shortcut)
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.setIcon(_mark_icon("refresh"))
        self.refresh_button.setIconSize(QSize(18, 18))
        self.refresh_button.setToolTip("Atualizar estado do Vladmir")
        self.refresh_button.clicked.connect(self.refresh_status)
        top.addWidget(self.refresh_button)
        main.addLayout(top)
        divider = QFrame()
        divider.setObjectName("headerDivider")
        divider.setFixedHeight(1)
        main.addWidget(divider)
        self.engineer_work_feedback = QFrame()
        self.engineer_work_feedback.setObjectName("engineerWorkFeedback")
        feedback_layout = QVBoxLayout(self.engineer_work_feedback)
        feedback_layout.setContentsMargins(12, 6, 12, 6)
        feedback_layout.setSpacing(4)
        self.engineer_work_label = QLabel("Engineer está analisando sua solicitação…")
        self.engineer_work_label.setObjectName("engineerWorkLabel")
        feedback_layout.addWidget(self.engineer_work_label)
        self.engineer_work_bar = QProgressBar()
        self.engineer_work_bar.setObjectName("engineerWorkBar")
        self.engineer_work_bar.setRange(0, 0)
        self.engineer_work_bar.setTextVisible(False)
        self.engineer_work_bar.setMaximumHeight(4)
        self.engineer_work_feedback.hide()
        feedback_layout.addWidget(self.engineer_work_bar)
        main.addWidget(self.engineer_work_feedback)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("chatScroll")
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat = QWidget()
        self.chat.setObjectName("chatContent")
        self.chat_layout = QVBoxLayout(self.chat)
        self.chat_layout.setContentsMargins(8, 26, 8, 26)
        self.chat_layout.setSpacing(20)
        self.empty_state = QWidget()
        self.empty_state.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        empty = QVBoxLayout(self.empty_state)
        empty.setSpacing(10)
        empty.addStretch(2)
        eyebrow = QLabel("UM ASSISTENTE. TODOS OS SEUS DISPOSITIVOS.")
        eyebrow.setObjectName("welcomeEyebrow")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(eyebrow)
        welcome = QLabel("O que vamos fazer hoje?")
        welcome.setObjectName("welcomeTitle")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(welcome)
        hint = QLabel("Converse, planeje ou explore uma ideia com o Vladmir.")
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(hint)
        empty.addSpacing(22)
        cards = QWidget()
        cards.setMaximumWidth(570)
        grid = QGridLayout(cards)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        suggestions = (
            ("Organizar meu dia", "calendar", "Me ajude a organizar meu dia e priorizar minhas tarefas."),
            ("Explorar uma ideia", "chat", "Quero desenvolver uma ideia. Me ajude a pensar nas opções."),
            ("Entender um arquivo", "attach", "Vou anexar um arquivo. Me ajude a entender e resumir o conteúdo."),
            ("Resolver um problema", "github", "Me ajude a investigar um problema passo a passo."),
        )
        for index, (caption, icon, prompt) in enumerate(suggestions):
            button = QPushButton(caption)
            button.setObjectName("suggestionCard")
            button.setIcon(_mark_icon(icon))
            button.setIconSize(QSize(22, 22))
            button.setMinimumHeight(70)
            button.setToolTip(prompt)
            button.clicked.connect(lambda checked=False, text=prompt: self._prefill_message(text))
            grid.addWidget(button, index // 2, index % 2)
        empty.addWidget(cards, alignment=Qt.AlignmentFlag.AlignHCenter)
        empty.addStretch(3)
        self.chat_layout.addWidget(self.empty_state)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat)
        self.scroll.verticalScrollBar().rangeChanged.connect(self._chat_range_changed)
        self.scroll.verticalScrollBar().sliderMoved.connect(lambda value:setattr(self,'follow_latest',self.scroll.verticalScrollBar().maximum()-value<80))
        self.scroll.verticalScrollBar().actionTriggered.connect(lambda _:QTimer.singleShot(0,self._record_manual_scroll))
        self.scroll.viewport().installEventFilter(self)
        main.addWidget(self.scroll, 1)

        self.composer_box = QFrame()
        self.composer_box.setObjectName("composerBox")
        compose = QVBoxLayout(self.composer_box)
        compose.setContentsMargins(17, 13, 13, 11)
        compose.setSpacing(7)
        self.input = Composer()
        self.input.setObjectName("messageInput")
        self.input.setPlaceholderText("Escreva para o Vladmir ou arraste um arquivo aqui…")
        self.input.setFixedHeight(66)
        self.input.send_requested.connect(self.send_message)
        self.input.files_dropped.connect(self._add_attachment_paths)
        self.input.drag_hover_changed.connect(self._set_drop_target_state)
        compose.addWidget(self.input, 1)
        self.attachment_list = QListWidget()
        self.attachment_list.setObjectName("attachmentList")
        self.attachment_list.setMaximumHeight(76)
        self.attachment_list.hide()
        compose.addWidget(self.attachment_list)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.attach_button = QPushButton("Anexar")
        self.attach_button.setObjectName("attachButton")
        self.attach_button.setIcon(_mark_icon("attach"))
        self.attach_button.setIconSize(QSize(17, 17))
        self.attach_button.setToolTip("Imagens, PDFs, documentos DOCX e arquivos de texto")
        self.attach_button.clicked.connect(self.add_attachments)
        actions.addWidget(self.attach_button)
        self.remove_attachment_button = QPushButton()
        self.remove_attachment_button.setObjectName("attachButton")
        self.remove_attachment_button.setIcon(_mark_icon("trash"))
        self.remove_attachment_button.setToolTip("Remover o arquivo selecionado")
        self.remove_attachment_button.setAccessibleName("Remover o arquivo selecionado")
        self.remove_attachment_button.setDisabled(True)
        self.remove_attachment_button.hide()
        self.remove_attachment_button.clicked.connect(self.remove_selected_attachment)
        actions.addWidget(self.remove_attachment_button)
        self.attachment_list.currentRowChanged.connect(lambda row: self.remove_attachment_button.setEnabled(row >= 0))
        self.composer_hint = QLabel("Enter envia · Shift+Enter nova linha")
        self.composer_hint.setObjectName("composerHint")
        actions.addWidget(self.composer_hint)
        actions.addStretch(1)
        self.model_selector = QComboBox()
        self.model_selector.setObjectName("modelSelector")
        self.model_selector.addItem("Qwen · conversa", "vladmir")
        self.model_selector.addItem("Qwen · resposta rápida", "vladmir-call")
        self.model_selector.setToolTip("Os dois perfis usam a memória compartilhada")
        actions.addWidget(self.model_selector)
        self.reasoning_selector = QComboBox()
        self.reasoning_selector.setObjectName("reasoningSelector")
        self.reasoning_selector.addItem("Instantâneo", "instant")
        self.reasoning_selector.addItem("Médio", "medium")
        self.reasoning_selector.addItem("Alto", "high")
        self.reasoning_selector.setCurrentIndex(1)
        self.reasoning_selector.setAccessibleName("Nível de resposta e raciocínio")
        self.reasoning_selector.setToolTip(
            "Instantâneo: sem raciocínio estendido, contexto 4k e até 512 tokens. "
            "Médio: contexto 6k e até 2048 tokens. "
            "Alto: contexto 8k e até 4096 tokens, com explicação mais aprofundada. "
            "Níveis maiores podem levar mais tempo e usar mais VRAM."
        )
        self.model_selector.currentIndexChanged.connect(
            lambda _index: self.reasoning_selector.setEnabled(self.model_selector.currentData() == "vladmir")
        )
        actions.addWidget(self.reasoning_selector)
        self.send_button = QPushButton()
        self.send_button.setObjectName("sendButton")
        self.send_button.setIcon(_mark_icon("send"))
        self.send_button.setIconSize(QSize(21, 21))
        self.send_button.setToolTip("Enviar mensagem")
        self.send_button.setAccessibleName("Enviar mensagem")
        self.send_button.clicked.connect(self.send_message)
        actions.addWidget(self.send_button)
        compose.addLayout(actions)
        main.addWidget(self.composer_box)
        footer = QLabel("PC, celular e voz · uma memória compartilhada")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(footer)
        self.chat_page = content
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("markAreas")
        self.page_stack.addWidget(content)
        self.content_layout = self.page_stack
        self.page_heading = title
        self._build_specialization_pages()
        layout.addWidget(self.page_stack, 1)

    def _area_page(self, key: str, title: str, description: str):
        page = QWidget()
        page.setObjectName(f"area_{key}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 34, 40, 28)
        layout.setSpacing(14)
        eyebrow = QLabel("Vladmir · ÁREA DE TRABALHO")
        eyebrow.setObjectName("welcomeEyebrow")
        heading = QLabel(title)
        heading.setObjectName("welcomeTitle")
        detail = QLabel(description)
        detail.setObjectName("welcomeHint")
        detail.setWordWrap(True)
        detail.setMaximumWidth(720)
        layout.addWidget(eyebrow)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addSpacing(8)
        return page, layout

    def _build_specialization_pages(self):
        self.area_pages = {}

        engineer, engineer_layout = self._area_page(
            "engineer", "Engenheiro",
            "Um espaço de trabalho focado em programação, com modelo, contexto de projeto e tarefas visíveis.",
        )
        model_card = QFrame()
        model_card.setObjectName("engineerHero")
        model_layout = QHBoxLayout(model_card)
        model_layout.setContentsMargins(18, 14, 18, 14)
        model_layout.setSpacing(14)
        model_icon = QLabel()
        model_icon.setPixmap(_mark_icon("github").pixmap(QSize(28, 28)))
        model_layout.addWidget(model_icon)
        model_copy = QVBoxLayout()
        model_copy.setSpacing(4)
        model_title = QLabel("Perfil Engineer")
        model_title.setObjectName("engineerCardTitle")
        model_copy.addWidget(model_title)
        self.engineer_model_status = QLabel("Verificando o modelo configurado…")
        self.engineer_model_status.setObjectName("engineerModelStatus")
        self.engineer_model_status.setWordWrap(True)
        model_copy.addWidget(self.engineer_model_status)
        model_layout.addLayout(model_copy, 1)
        self.engineer_model_indicator = QLabel("…")
        self.engineer_model_indicator.setObjectName("engineerModelIndicator")
        model_layout.addWidget(self.engineer_model_indicator)
        engineer_layout.addWidget(model_card)

        project_title = QLabel("Contexto do projeto")
        project_title.setObjectName("engineerSectionTitle")
        engineer_layout.addWidget(project_title)
        self.engineer_project_input = QLineEdit()
        self.engineer_project_input.setObjectName("engineerProjectId")
        self.engineer_project_input.setPlaceholderText("ID curto e opcional, por exemplo mark-core")
        self.engineer_project_input.setAccessibleName("Projeto para associar ao contexto e à memória")
        engineer_layout.addWidget(self.engineer_project_input)
        project_hint = QLabel("O ID separa o contexto e as memórias deste projeto. Para permitir leitura, edição ou testes em arquivos, abra uma Tarefa e escolha a pasta de trabalho.")
        project_hint.setObjectName("engineerHint")
        project_hint.setWordWrap(True)
        engineer_layout.addWidget(project_hint)

        workflow_title = QLabel("Fluxo de trabalho")
        workflow_title.setObjectName("engineerSectionTitle")
        engineer_layout.addWidget(workflow_title)
        workflow_row = QHBoxLayout()
        workflow_row.setSpacing(10)
        for number, title, detail in (
            ("01", "Analisar", "Converse sobre código, erros ou arquitetura."),
            ("02", "Preparar", "Revise o plano e escolha uma pasta."),
            ("03", "Verificar", "Autorize operações e confira o relatório."),
        ):
            tile = QFrame()
            tile.setObjectName("engineerStepCard")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(14, 12, 14, 12)
            tile_layout.setSpacing(5)
            number_label = QLabel(number)
            number_label.setObjectName("engineerStepNumber")
            tile_layout.addWidget(number_label)
            step_title = QLabel(title)
            step_title.setObjectName("engineerStepTitle")
            tile_layout.addWidget(step_title)
            step_detail = QLabel(detail)
            step_detail.setObjectName("engineerHint")
            step_detail.setWordWrap(True)
            tile_layout.addWidget(step_detail)
            workflow_row.addWidget(tile, 1)
        engineer_layout.addLayout(workflow_row)

        quick_title = QLabel("Começar com")
        quick_title.setObjectName("engineerSectionTitle")
        engineer_layout.addWidget(quick_title)
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        for label, prompt in (
            ("Investigar um erro", "Ajude a investigar este erro. Explique a causa provável, indique quais arquivos ou informações precisa e proponha uma correção verificável."),
            ("Revisar código", "Revise este código considerando bugs, segurança, legibilidade e desempenho. Primeiro liste os achados com gravidade e evidência."),
            ("Entender um projeto", "Ajude a entender a arquitetura deste projeto. Diga quais arquivos devo anexar ou qual pasta selecionar numa Tarefa."),
        ):
            quick = QPushButton(label)
            quick.setObjectName("engineerQuickAction")
            quick.setMinimumHeight(40)
            quick.clicked.connect(lambda checked=False, text=prompt: self._start_engineer_prompt(text))
            quick_row.addWidget(quick, 1)
        engineer_layout.addLayout(quick_row)

        self.engineer_mission_summary = QLabel("Tarefas: carregando…")
        self.engineer_mission_summary.setObjectName("engineerMissionSummary")
        engineer_layout.addWidget(self.engineer_mission_summary)
        engineer_actions = QHBoxLayout()
        engineer_chat = QPushButton("Abrir chat de código")
        engineer_chat.setObjectName("primaryButton")
        engineer_chat.clicked.connect(lambda: self.open_specialized_chat("engineer"))
        engineer_missions = QPushButton("Tarefas e permissões…")
        engineer_missions.setIcon(_mark_icon("github"))
        engineer_missions.clicked.connect(self.open_missions)
        engineer_github = QPushButton("Repositórios GitHub…")
        engineer_github.clicked.connect(self.open_github)
        engineer_actions.addWidget(engineer_chat)
        engineer_actions.addWidget(engineer_missions)
        engineer_actions.addWidget(engineer_github)
        engineer_actions.addStretch(1)
        engineer_layout.addLayout(engineer_actions)
        engineer_content = engineer
        engineer_scroll = QScrollArea()
        engineer_scroll.setObjectName("engineerScroll")
        engineer_scroll.setWidgetResizable(True)
        engineer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        engineer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        engineer_scroll.setWidget(engineer_content)
        engineer = engineer_scroll
        self.area_pages["engineer"] = engineer
        self.page_stack.addWidget(engineer)

        professor, professor_layout = self._area_page(
            "professor", "Professor",
            "Conversas de estudo independentes, com a mesma memória salva do Vladmir. A Biblioteca é opcional; planos e progresso ficam locais.",
        )
        professor_layout.addWidget(QLabel("Assunto"))
        self.professor_subject = QLineEdit();self.professor_subject.setPlaceholderText("Ex.: circuitos elétricos")
        professor_layout.addWidget(self.professor_subject)
        professor_layout.addWidget(QLabel("Objetivo (opcional)"))
        self.professor_objective = QLineEdit();self.professor_objective.setPlaceholderText("O que você quer conseguir fazer?")
        professor_layout.addWidget(self.professor_objective)
        professor_layout.addWidget(QLabel("Fonte da Biblioteca (opcional; título exato)"))
        self.professor_source = QLineEdit();self.professor_source.setPlaceholderText("Ex.: Manual de eletrônica.pdf")
        professor_layout.addWidget(self.professor_source)
        study_options=QHBoxLayout()
        self.professor_mode=QComboBox()
        for mode in STUDY_MODES:self.professor_mode.addItem(mode.label,mode.key)
        self.professor_level=QComboBox()
        for level in ("iniciante","intermediário","avançado"):self.professor_level.addItem(level.capitalize(),level)
        study_options.addWidget(self.professor_mode,2);study_options.addWidget(self.professor_level,1);professor_layout.addLayout(study_options)
        study_actions=QHBoxLayout()
        professor_start=QPushButton("Preparar estudo");professor_start.setObjectName("primaryButton");professor_start.clicked.connect(self.prepare_study)
        professor_start.setAccessibleName("Iniciar um plano de estudo")
        professor_chat=QPushButton("Abrir conversa");professor_chat.clicked.connect(lambda: self.open_specialized_chat("professor"))
        professor_plan=QPushButton("Plano e progresso ▾")
        plan_menu=QMenu(professor_plan)
        plan_menu.addAction("Retomar último plano",self.resume_study_plan)
        plan_menu.addAction("Ver progresso",self.view_study_progress)
        plan_menu.addAction("Concluir plano atual",self.complete_study_plan)
        plan_menu.addSeparator();plan_menu.addAction("Apagar progresso…",self.reset_study_progress)
        professor_plan.setMenu(plan_menu)
        study_actions.addWidget(professor_chat);study_actions.addWidget(professor_start);study_actions.addWidget(professor_plan);study_actions.addStretch(1)
        professor_layout.addLayout(study_actions)
        self.professor_status=QLabel("Seu progresso só é guardado quando você prepara um plano.");self.professor_status.setWordWrap(True)
        professor_layout.addWidget(self.professor_status)
        professor_layout.addStretch(1)
        self.area_pages["professor"] = professor
        self.page_stack.addWidget(professor)

        evolution, evolution_layout = self._area_page(
            "evolution", "Evolução",
            "Acompanhe experimentos em ambiente separado. Propostas continuam dependendo de avaliação e revisão antes de serem instaladas.",
        )
        evolution_layout.addWidget(QLabel(
            "A Autoevolução de código propõe mudanças, mede e verifica cada ciclo isoladamente; só uma revisão sua instala uma proposta. O treino QLoRA é outro processo: produz um adaptador candidato e exige avaliação de qualidade, VRAM e energia."
        ))
        evolution_cards = QHBoxLayout()
        for title, detail in (
            ("Código · ciclos de melhoria", "Observa métricas → prepara uma hipótese → altera um candidato isolado → compara e registra relatório. Nunca promove mudanças sozinho."),
            ("Modelo · treino QLoRA", "Treino experimental separado do Vladmir em uso. O checkpoint da primeira rodada está pausado; avaliação comparativa ainda pendente."),
        ):
            card = QFrame(); card.setObjectName("engineerStepCard")
            card_layout = QVBoxLayout(card)
            heading = QLabel(title); heading.setObjectName("engineerStepTitle")
            body = QLabel(detail); body.setObjectName("engineerHint"); body.setWordWrap(True)
            card_layout.addWidget(heading); card_layout.addWidget(body)
            evolution_cards.addWidget(card, 1)
        evolution_layout.addLayout(evolution_cards)
        self.evolution_status = QLabel("Consultando o estado da rotina…")
        self.evolution_status.setObjectName("engineerMissionSummary")
        self.evolution_status.setWordWrap(True)
        evolution_layout.addWidget(self.evolution_status)
        self.evolution_progress_bar = QProgressBar()
        self.evolution_progress_bar.setObjectName("evolutionProgress")
        self.evolution_progress_bar.setRange(0, 7)
        self.evolution_progress_bar.setValue(0)
        self.evolution_progress_bar.setFormat("%v de %m etapas")
        self.evolution_progress_bar.setMaximumHeight(18)
        evolution_layout.addWidget(self.evolution_progress_bar)
        evolution_open = QPushButton("Abrir painel de evolução")
        evolution_open.setObjectName("primaryButton")
        evolution_open.clicked.connect(self.open_evolution_dialog)
        evolution_layout.addWidget(evolution_open, alignment=Qt.AlignmentFlag.AlignLeft)
        evolution_layout.addStretch(1)
        self.area_pages["evolution"] = evolution
        self.page_stack.addWidget(evolution)

        settings, settings_layout = self._area_page(
            "settings", "Configurações",
            "Resumo local e seguro das opções compartilhadas. Segredos e credenciais não são exibidos.",
        )
        self.settings_summary = QLabel("Carregando…")
        self.settings_summary.setObjectName("settingsSummary")
        self.settings_summary.setWordWrap(True)
        settings_layout.addWidget(self.settings_summary)
        refresh_settings = QPushButton("Atualizar resumo")
        refresh_settings.clicked.connect(self.refresh_settings_summary)
        settings_layout.addWidget(refresh_settings, alignment=Qt.AlignmentFlag.AlignLeft)
        providers_button = QPushButton("Modelos e APIs…")
        providers_button.setObjectName("primaryButton")
        providers_button.clicked.connect(self.open_provider_manager)
        settings_layout.addWidget(providers_button, alignment=Qt.AlignmentFlag.AlignLeft)
        manage_memories = QPushButton("Gerenciar memórias salvas…")
        manage_memories.setObjectName("manageMemories")
        manage_memories.clicked.connect(self.open_memory_manager)
        settings_layout.addWidget(manage_memories, alignment=Qt.AlignmentFlag.AlignLeft)
        settings_layout.addStretch(1)
        self.area_pages["settings"] = settings
        self.page_stack.addWidget(settings)

    def _study_store(self):
        return StudyPlanStore()

    def prepare_study(self):
        try:
            subject=self.professor_subject.text()
            mode=self.professor_mode.currentData()
            level=self.professor_level.currentData()
            objective=self.professor_objective.text()
            source=self.professor_source.text()
            prompt=build_study_prompt(subject,mode,level,objective=objective,source=source)
            with self._study_store() as store:
                plan=store.start(subject,objective,source,level,mode)
        except (ValueError,OSError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Professor",str(exc) if isinstance(exc,ValueError) else "Não consegui salvar o plano local; nada foi apagado.")
            return
        self.professor_plan_id=plan.id
        self.professor_status.setText(f"Plano salvo · {plan.subject} · {plan.status.lower()}")
        self.open_specialized_chat("professor")
        self._prefill_message(prompt)

    def resume_study_plan(self):
        try:
            with self._study_store() as store:
                plans=store.list()
                plan=next((item for item in plans if item.status=="ACTIVE"),None)
        except (OSError,sqlite3.Error,ValueError):
            QMessageBox.warning(self,"Professor","Não consegui ler o progresso local.");return
        if plan is None:
            QMessageBox.information(self,"Professor","Não há plano ativo para retomar.");return
        self.professor_plan_id=plan.id
        self.professor_subject.setText(plan.subject);self.professor_objective.setText(plan.objective)
        self.professor_source.setText(plan.source);self.professor_level.setCurrentIndex(self.professor_level.findData(plan.level))
        self.professor_mode.setCurrentIndex(self.professor_mode.findData(plan.mode))
        prompt=build_study_prompt(plan.subject,plan.mode,plan.level,objective=plan.objective,source=plan.source)
        self.professor_status.setText(f"Plano retomado · {plan.subject}")
        self.open_specialized_chat("professor");self._prefill_message(prompt)

    def view_study_progress(self):
        try:
            with self._study_store() as store:plans=store.list()
        except (OSError,sqlite3.Error,ValueError):
            QMessageBox.warning(self,"Progresso","Não consegui ler o progresso local.");return
        if not plans:
            QMessageBox.information(self,"Progresso","Ainda não há planos de estudo salvos.");return
        lines=[]
        for plan in plans:
            line=f"{plan.subject} · {plan.status.lower()} · nível {plan.level}"
            line+=f" · modo {next((item.label for item in STUDY_MODES if item.key==plan.mode),plan.mode)}"
            if plan.objective:line+=f"\nObjetivo: {plan.objective}"
            if plan.source:line+=f"\nFonte: {plan.source}"
            lines.append(line)
        QMessageBox.information(self,"Progresso de estudo","\n\n".join(lines))

    def complete_study_plan(self):
        plan_id=getattr(self,"professor_plan_id",None)
        if plan_id is None:
            QMessageBox.information(self,"Professor","Prepare um plano nesta sessão para marcá-lo como concluído.");return
        try:
            with self._study_store() as store:completed=store.complete(plan_id)
        except (OSError,sqlite3.Error,ValueError):
            QMessageBox.warning(self,"Professor","Não consegui atualizar o progresso local.");return
        if completed:self.professor_status.setText("Plano concluído; histórico preservado localmente.")
        else:self.professor_status.setText("Esse plano já estava concluído ou foi apagado.")

    def reset_study_progress(self):
        if QMessageBox.question(self,"Apagar progresso","Apagar somente planos de estudo do Vladmir? Conversas, Biblioteca e arquivos não serão alterados.")!=QMessageBox.StandardButton.Yes:return
        try:
            with self._study_store() as store:store.reset()
        except (OSError,sqlite3.Error,ValueError):
            QMessageBox.warning(self,"Professor","Não consegui apagar o progresso local.");return
        self.professor_plan_id=None;self.professor_status.setText("Progresso de estudo apagado; conversa e Biblioteca preservadas.")

    def refresh_settings_summary(self):
        try:
            from .config import load_config
            cfg = load_config()
            models = cfg.get("models", {})
            memory = cfg.get("memory", {})
            lines = (
                f"Conversa: {models.get('chat', 'não configurado')}",
                f"Resposta rápida: {models.get('call', 'não configurado')}",
                f"Contexto curto: até {memory.get('max_messages', '—')} mensagens",
                f"Memória compartilhada local: {MEMORY_FILE}",
                "GitHub: integração existente, chamada somente quando solicitada",
                "Câmera e microfone: controles permanecem nas áreas Geral e Conexões",
            )
            self.settings_summary.setText("\n".join(lines))
        except Exception as exc:
            self.settings_summary.setText(f"Não consegui ler o resumo local ({type(exc).__name__}).")

    def open_area(self, area: str):
        if area in self.area_buttons:
            self._set_active_area(area)
        if area == "library":
            self.open_library()
            return
        page = self.area_pages.get(area)
        if page is None:
            if area == "general":
                self.open_specialized_chat("general")
            return
        self.page_stack.setCurrentWidget(page)

        if area == "engineer":
            self._refresh_engineer_overview()
        if area == "evolution":
            self._refresh_evolution_overview()

    def _refresh_evolution_overview(self):
        if self.evolution_status_loading:
            return
        self.evolution_status_loading = True
        self.evolution_status.setText("Atualizando estado da rotina…")

        def inspect_state():
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [sys.executable, "-m", "mark.evolution.cli", "status"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=8, check=False,
            )
            if result.returncode:
                raise RuntimeError("não foi possível ler o estado")
            return json.loads(result.stdout)

        def show_state(state):
            self.evolution_status_loading = False
            progress = state.get("progress", {})
            total_steps = max(1, int(progress.get("total", 7)))
            step = max(0, min(total_steps, int(progress.get("step", 0))))
            self.evolution_progress_bar.setRange(0, total_steps)
            self.evolution_progress_bar.setValue(step)
            self.evolution_progress_bar.setFormat(f"{step} de {total_steps} etapas")
            if state.get("paused"):
                text = "Rotina pausada · timer periódico desativado · alterações candidatas aguardam revisão."
            elif state.get("enabled"):
                text = f"Rotina ativa · etapa: {progress.get('label', 'aguardando')} · timer periódico {'ativo' if state.get('schedule_enabled') else 'desativado'}."
            else:
                text = "Rotina desativada · nenhum ciclo está executando."
            backlog = state.get("backlog", 0)
            text += f"  ·  {backlog} oportunidade(s) na fila."
            self.evolution_status.setText(text)

        def failed(_message):
            self.evolution_status_loading = False
            self.evolution_status.setText("Estado da rotina indisponível; abra o painel para consultar os detalhes.")

        self._task(inspect_state, show_state, failed)

    def _refresh_engineer_overview(self):
        if self.engineer_status_loading:
            return
        self.engineer_status_loading = True
        self.engineer_model_status.setText("Verificando o modelo configurado no Ollama…")

        def inspect_local_state():
            from .config import load_config
            from .missions import MissionStore
            cfg = load_config()
            model = cfg.get("models", {}).get("engineer", "")
            installed = None
            try:
                request = urllib.request.Request(
                    cfg["ollama"]["url"].rstrip("/") + "/api/tags",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    rows = json.load(response).get("models", [])
                installed_names = {row.get("name", "").removesuffix(":latest")
                                   for row in rows if isinstance(row, dict)}
                installed = model.removesuffix(":latest") in installed_names
            except (OSError, ValueError, KeyError, TypeError):
                pass

            mission_count = {}
            db_path = MissionStore.DEFAULT_PATH
            if db_path.is_file() and not db_path.is_symlink():
                try:
                    uri = "file:" + quote(str(db_path)) + "?mode=ro"
                    db = sqlite3.connect(uri, uri=True, timeout=2)
                    try:
                        mission_count = dict(db.execute(
                            "SELECT state, COUNT(*) FROM missions GROUP BY state"
                        ).fetchall())
                    finally:
                        db.close()
                except (OSError, sqlite3.Error):
                    mission_count = {}
            return {"model": model, "installed": installed,
                    "mission_count": mission_count}

        def show_local_state(result):
            self.engineer_status_loading = False
            model = result["model"] or "Modelo Engineer não configurado"
            self.engineer_model_status.setToolTip(model)
            self.engineer_model_indicator.setText(
                "PRONTO" if result["installed"] is True else
                "AUSENTE" if result["installed"] is False else "SEM STATUS"
            )
            self.engineer_model_indicator.setProperty("ready", result["installed"] is True)
            self.engineer_model_indicator.style().unpolish(self.engineer_model_indicator)
            self.engineer_model_indicator.style().polish(self.engineer_model_indicator)
            if result["installed"] is True:
                self.engineer_model_status.setText(model + " · instalado; carrega quando você usa")
            elif result["installed"] is False:
                self.engineer_model_status.setText(model + " · não encontrado no Ollama")
            else:
                self.engineer_model_status.setText(model + " · não foi possível consultar o Ollama")
            counts = result["mission_count"]
            total = sum(counts.values())
            active = sum(counts.get(state, 0) for state in
                         ("WAITING_APPROVAL", "QUEUED", "RUNNING", "PAUSED", "BLOCKED", "VERIFYING"))
            completed = counts.get("COMPLETED", 0)
            if total:
                self.engineer_mission_summary.setText(
                    f"Tarefas locais · {total} registradas · {active} aguardando ou em andamento · {completed} concluídas"
                )
            else:
                self.engineer_mission_summary.setText("Tarefas locais · nenhuma registrada")

        def failed_local_state(_message):
            self.engineer_status_loading = False
            self.engineer_model_indicator.setText("ERRO")
            self.engineer_model_status.setText("Não consegui atualizar o estado local do Engineer.")
            self.engineer_mission_summary.setText("Tarefas locais · estado indisponível")

        self._task(inspect_local_state, show_local_state, failed_local_state)

    def _start_engineer_prompt(self, prompt: str):
        self.open_specialized_chat("engineer")
        self._prefill_message(prompt)

    def open_specialized_chat(self, specialization: str):
        if specialization not in {"general", "engineer", "professor"}:
            raise ValueError("Área de conversa desconhecida")
        if self.current_specialization in {"engineer", "professor"}:
            self.specialization_conversations[self.current_specialization] = self.current_conversation_id
        self.current_specialization = specialization
        self._set_active_area(specialization)
        self.engineer_work_feedback.hide()
        if specialization == "engineer":
            if self._engineer_profile_restore is None:
                self._engineer_profile_restore = self.model_selector.currentIndex()
            self.model_selector.setCurrentIndex(0)
            self.model_selector.setItemText(0, "Qwen Coder · Engineer")
            self.model_selector.setToolTip("O Engineer usa o perfil de código configurado e a memória compartilhada.")
            self.model_selector.setEnabled(False)
            self.engineer_chat_badge.setText("ENGINEER · PERFIL DE CÓDIGO")
            self.engineer_chat_badge.show()
        else:
            if self._engineer_profile_restore is not None:
                self.model_selector.setItemText(0, "Qwen · conversa")
                self.model_selector.setEnabled(True)
                self.model_selector.setCurrentIndex(self._engineer_profile_restore)
                self.model_selector.setToolTip("Os dois perfis usam a memória compartilhada")
                self._engineer_profile_restore = None
            self.engineer_chat_badge.hide()
        self.current_project_id = None
        self.current_task_id = None
        if specialization == "engineer":
            raw_project_id = self.engineer_project_input.text().strip().lower()
            if raw_project_id:
                import re
                project_id = re.sub(r"[^a-z0-9_.:-]+", "-", raw_project_id).strip("-.:_")
                if not project_id or len(project_id) > 128:
                    QMessageBox.warning(self, "Projeto", "Use um ID de até 128 caracteres.")
                    return
                self.current_project_id = project_id
        self.page_heading.setText({"general": "Geral", "engineer": "Engenheiro", "professor": "Professor"}[specialization])
        if specialization == "general":
            self.current_conversation_id = "general-main"
        else:
            self.current_conversation_id = self.specialization_conversations.get(specialization, "")
        self._refresh_conversation_selector(self.current_conversation_id or None)
        self._load_active_conversation()
        self.page_stack.setCurrentWidget(self.chat_page)
        self.input.setFocus()

    def _set_active_area(self, active: str):
        for key, button in self.area_buttons.items():
            button.setObjectName("navButtonActive" if key == active else "navButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _prefill_message(self, text):
        if not self.busy:
            self.input.setPlainText(text)
            self.input.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "composer_hint"):
            self.composer_hint.setVisible(self.width() >= 1100)

    def _section_label(self, text):
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _nav_button(self, text: str, icon_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("navButton")
        button.setIcon(_mark_icon(icon_name))
        button.setIconSize(QSize(18, 18))
        button.setFixedHeight(36)
        return button

    def _status_row(self, name, value):
        box = QFrame()
        box.setObjectName("statusBox")
        row = QHBoxLayout(box)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(8)
        label = QLabel(name)
        label.setObjectName("statusTitle")
        text = QLabel(value)
        text.setObjectName("statusValue")
        text.setWordWrap(True)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(text)
        box.setFixedHeight(32)
        box.value_label = text
        return box

    def _set_style(self):
        self.setStyleSheet(STYLESHEET)

    def _append_bubble(self, text: str, role: str, created_at: int | None = None,
                       auto_scroll: bool = True, source: str = ""):
        if self.empty_state is not None:
            self.chat_layout.removeWidget(self.empty_state)
            self.empty_state.hide()
            self.empty_state.deleteLater()
            self.empty_state = None
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        bubble = QFrame()
        bubble.setMaximumWidth(760)
        bubble.setObjectName("userBubble" if role == "user" else "assistantBubble")
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding if role == "assistant" else QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        inner=QVBoxLayout(bubble);inner.setContentsMargins(16,12,16,12)
        label=QLabel(message_html(text));label.setObjectName('messageBody');label.setTextFormat(Qt.TextFormat.RichText);label.setWordWrap(True)
        if role == "user":
            first_line = text.splitlines()[0] if text else ""
            natural = label.fontMetrics().horizontalAdvance(first_line[:72]) + 42
            bubble.setMinimumWidth(min(520, max(190, natural)))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse|Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
        label.setOpenExternalLinks(False);label.linkActivated.connect(self._open_message_link)
        if role=='assistant':
            label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            def context_menu(position,value=text,target=label):
                from PyQt6.QtWidgets import QMenu
                menu=QMenu(target);menu.addAction('Copiar resposta',lambda:QApplication.clipboard().setText(value));menu.exec(target.mapToGlobal(position))
            label.customContextMenuRequested.connect(context_menu)
        inner.addWidget(label)
        if role == "user":
            label_origin = source_label(source)
            who = QLabel("Você · " + label_origin if label_origin else "Você")
            who.setStyleSheet("color: #999999; font-size: 10px; border: 0; background: transparent;")
            inner.addWidget(who)
        if role == "user":
            row.addStretch(1)
        row.addWidget(bubble, 1 if role == "assistant" else 0)
        if role == "assistant":
            row.addStretch(1)
        wrapper = QWidget()
        wrapper.setLayout(row)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, wrapper)
        if auto_scroll:
            self.follow_latest=True
            self._schedule_bottom_scroll()

    def _open_message_link(self,url):
        if safe_web_link(url):QDesktopServices.openUrl(QUrl(url))

    def _scroll_to_latest(self):
        if self.follow_latest:
            self.chat_layout.activate()
            self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def _schedule_bottom_scroll(self):
        for delay in (0,30,100):QTimer.singleShot(delay,self._scroll_to_latest)

    def _chat_range_changed(self,*_):
        if self.follow_latest:self._schedule_bottom_scroll()

    def _record_manual_scroll(self):
        bar=self.scroll.verticalScrollBar();self.follow_latest=bar.maximum()-bar.value()<80

    def eventFilter(self,watched,event):
        if hasattr(self,'scroll') and watched is self.scroll.viewport() and event.type()==QEvent.Type.Wheel:
            self.follow_latest=False;QTimer.singleShot(0,self._record_manual_scroll)
        return super().eventFilter(watched,event)

    def _load_history(self):
        self._ensure_conversation_store()
        self._load_active_conversation()

    def _conversation_db(self):
        DESKTOP_CONVERSATIONS_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = DESKTOP_CONVERSATIONS_FILE.parent.stat()
        if parent.st_uid != os.getuid():
            raise PermissionError("A pasta das conversas do Vladmir precisa pertencer ao usuário.")
        DESKTOP_CONVERSATIONS_FILE.parent.chmod(0o700)
        if not DESKTOP_CONVERSATIONS_FILE.exists():
            try:
                fd = os.open(DESKTOP_CONVERSATIONS_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        info = DESKTOP_CONVERSATIONS_FILE.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PermissionError("O histórico de conversas do Vladmir precisa ser privado (0600).")
        return sqlite3.connect(DESKTOP_CONVERSATIONS_FILE, timeout=2)

    def _ensure_conversation_store(self):
        db = self._conversation_db()
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, specialization TEXT NOT NULL, title TEXT NOT NULL,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
                role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL,
                created_at INTEGER NOT NULL)""")
            db.execute("CREATE TABLE IF NOT EXISTS imported_remote_turns(turn_id INTEGER PRIMARY KEY)")
            db.execute("CREATE INDEX IF NOT EXISTS conversation_messages_order ON conversation_messages(conversation_id,id)")
            now = int(time.time())
            db.execute("INSERT OR IGNORE INTO conversations VALUES('general-main','general','Geral',?,?)", (now, now))
            for specialization, title in (("engineer", "Nova conversa"), ("professor", "Nova conversa")):
                exists = db.execute("SELECT 1 FROM conversations WHERE specialization=? LIMIT 1", (specialization,)).fetchone()
                if not exists:
                    db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)",
                               (uuid4().hex, specialization, title, now, now))
            general_count = db.execute(
                "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id='general-main'"
            ).fetchone()[0]
            if not general_count and MEMORY_FILE.exists():
                info = MEMORY_FILE.lstat()
                if stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077:
                    legacy = sqlite3.connect(f"file:{MEMORY_FILE}?mode=ro", uri=True, timeout=0.2)
                    try:
                        old_turns = legacy.execute(
                            "SELECT id,created_at,source,user_text,assistant_text FROM turns ORDER BY id DESC LIMIT 30"
                        ).fetchall()
                    except sqlite3.Error:
                        old_turns = []
                    finally:
                        legacy.close()
                    for turn_id,created,source_name,user_text,assistant_text in reversed(old_turns):
                        db.execute("INSERT INTO conversation_messages(conversation_id,role,content,created_at) VALUES('general-main','user',?,?)",
                                   (user_text, created))
                        db.execute("INSERT INTO conversation_messages(conversation_id,role,content,created_at) VALUES('general-main','assistant',?,?)",
                                   (assistant_text, created))
                        if source_name.startswith(("mobile-","wear-")):
                            db.execute("INSERT OR IGNORE INTO imported_remote_turns VALUES(?)",(turn_id,))
            db.commit()
        finally:
            db.close()

    def _conversation_rows(self, specialization):
        self._ensure_conversation_store()
        db = self._conversation_db()
        try:
            return db.execute(
                "SELECT id,title FROM conversations WHERE specialization=? ORDER BY updated_at DESC,id",
                (specialization,),
            ).fetchall()
        finally:
            db.close()

    def _refresh_conversation_selector(self, select_id=None):
        if not hasattr(self, "conversation_selector"):
            return
        self._conversation_switching = True
        try:
            self.conversation_selector.clear()
            rows = self._conversation_rows(self.current_specialization)
            for conversation_id, title in rows:
                self.conversation_selector.addItem(title, conversation_id)
            if self.current_specialization == "general":
                self.conversation_selector.setCurrentIndex(0)
                self.conversation_selector.hide()
                self.new_conversation_button.hide()
                self.current_conversation_id = "general-main"
            else:
                self.conversation_selector.show()
                self.new_conversation_button.show()
                wanted = select_id or self.current_conversation_id
                index = self.conversation_selector.findData(wanted)
                if index < 0 and self.conversation_selector.count():
                    index = 0
                if index >= 0:
                    self.conversation_selector.setCurrentIndex(index)
                    self.current_conversation_id = self.conversation_selector.currentData()
                    self.specialization_conversations[self.current_specialization] = self.current_conversation_id
        finally:
            self._conversation_switching = False

    def _select_conversation_from_header(self, _index):
        if self._conversation_switching or self.current_specialization == "general":
            return
        conversation_id = self.conversation_selector.currentData()
        if conversation_id:
            self.current_conversation_id = conversation_id
            self._load_active_conversation()

    def _create_specialized_conversation(self):
        specialization = self.current_specialization
        if specialization not in {"engineer", "professor"}:
            return
        conversation_id = uuid4().hex
        now = int(time.time())
        db = self._conversation_db()
        try:
            db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)",
                       (conversation_id, specialization, "Nova conversa", now, now))
            db.commit()
        finally:
            db.close()
        self.current_conversation_id = conversation_id
        self.specialization_conversations[specialization] = conversation_id
        self._refresh_conversation_selector(conversation_id)
        self._load_active_conversation()
        self.input.setFocus()

    def _load_active_conversation(self):
        if not hasattr(self, "chat_layout"):
            return
        try:
            db = self._conversation_db()
            try:
                rows = db.execute(
                    "SELECT role,content,created_at FROM conversation_messages WHERE conversation_id=? ORDER BY id",
                    (self.current_conversation_id,),
                ).fetchall()
            finally:
                db.close()
        except sqlite3.Error:
            rows = []
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget is self.empty_state:
                    if not rows:
                        self.chat_layout.insertWidget(0,widget)
                        break
                    self.empty_state = None
                widget.deleteLater()
        if not rows and self.empty_state is None:
            self.empty_state=QWidget();empty=QVBoxLayout(self.empty_state);empty.addStretch(1)
            welcome=QLabel("O que vamos fazer hoje?");welcome.setObjectName("welcomeTitle")
            welcome.setAlignment(Qt.AlignmentFlag.AlignCenter);empty.addWidget(welcome);empty.addStretch(1)
            self.chat_layout.insertWidget(0,self.empty_state)
        self.last_assistant_reply = ""
        for role, content, created in rows:
            self._append_bubble(content, role, created, auto_scroll=False)
            if role == "assistant":
                self.last_assistant_reply = content
        self.history_signature = None
        if rows:
            self._schedule_bottom_scroll()

    def _save_conversation_message(self, role, content, conversation_id=None):
        if role not in {"user", "assistant"} or not isinstance(content, str):
            return
        conversation_id = conversation_id or self.current_conversation_id
        now = int(time.time())
        db = self._conversation_db()
        try:
            db.execute("INSERT INTO conversation_messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",
                       (conversation_id, role, content, now))
            if role == "user":
                title_row = db.execute("SELECT title FROM conversations WHERE id=?", (conversation_id,)).fetchone()
                if title_row and title_row[0] == "Nova conversa":
                    clean = " ".join(content.split())
                    title = clean[:42] + ("…" if len(clean) > 42 else "") if clean else "Nova conversa"
                    db.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=?",
                               (title, now, conversation_id))
                    if conversation_id == self.current_conversation_id:
                        self._refresh_conversation_selector(conversation_id)
            else:
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                           (now, conversation_id))
            db.commit()
        finally:
            db.close()

    def _conversation_request_messages(self, latest):
        db = self._conversation_db()
        try:
            rows = db.execute(
                "SELECT role,content FROM conversation_messages WHERE conversation_id=? ORDER BY id DESC LIMIT 31",
                (self.current_conversation_id,),
            ).fetchall()
        finally:
            db.close()
        rows.reverse()
        messages = [{"role": role, "content": content} for role, content in rows]
        messages.append({"role": "user", "content": latest})
        return messages[-32:]

    def _sync_history(self, force: bool = False):
        if self.busy and not force:
            return
        try:
            self._import_remote_turns()
            db = self._conversation_db()
            try:
                rows = db.execute(
                    "SELECT id,role,content,created_at FROM conversation_messages WHERE conversation_id=? ORDER BY id DESC LIMIT 64",
                    (self.current_conversation_id,),
                ).fetchall()
            finally:
                db.close()
            signature = tuple(rows)
            if signature == self.history_signature:
                return
            self._load_active_conversation()
            self.history_signature = signature
        except (OSError, sqlite3.Error, PermissionError):
            return

    def _import_remote_turns(self):
        if self.current_specialization != "general" or not MEMORY_FILE.exists():
            return
        self._ensure_conversation_store()
        info=MEMORY_FILE.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            return
        source=sqlite3.connect(f"file:{MEMORY_FILE}?mode=ro",uri=True,timeout=0.2)
        try:
            rows=source.execute("SELECT id,created_at,source,user_text,assistant_text FROM turns WHERE source LIKE 'mobile-%' OR source LIKE 'wear-%' ORDER BY id").fetchall()
        except sqlite3.Error:
            return
        finally:
            source.close()
        if not rows:
            return
        db=self._conversation_db()
        try:
            with db:
                for turn_id,created_at,source_name,user_text,assistant_text in rows:
                    found=db.execute("INSERT OR IGNORE INTO imported_remote_turns VALUES(?)",(turn_id,)).rowcount
                    if not found:
                        continue
                    db.execute("INSERT INTO conversation_messages(conversation_id,role,content,created_at) VALUES('general-main','user',?,?)",(user_text,created_at))
                    db.execute("INSERT INTO conversation_messages(conversation_id,role,content,created_at) VALUES('general-main','assistant',?,?)",(assistant_text,created_at))
        finally:
            db.close()

    def _task(self, operation, success, failure=None):
        if self.closing_when_idle:
            return
        worker = Task(operation, self)
        self.tasks.add(worker)
        worker.completed.connect(lambda value, w=worker: self._finish_task(w, success, value))
        worker.failed.connect(lambda message, w=worker: self._finish_error(w, failure, message))
        worker.start()

    def _finish_task(self, worker, callback, value):
        self.tasks.discard(worker)
        worker.deleteLater()
        callback(value)
        self._close_when_idle()

    def _finish_error(self, worker, callback, message):
        self.tasks.discard(worker)
        worker.deleteLater()
        if callback:
            callback(message)
        self._close_when_idle()

    def _close_when_idle(self):
        if self.closing_when_idle and not self.tasks:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event):
        if hasattr(self,'library_page') and self.library_page.worker.isRunning():
            self.library_page.shutdown()
            QTimer.singleShot(150,self.close)
            event.ignore();return
        if self.tasks:
            self.status_timer.stop()
            self.history_timer.stop()
            self.closing_when_idle = True
            self.connection_label.setText("Finalizando a tarefa antes de fechar…")
            self.centralWidget().setDisabled(True)
            event.ignore()
            self._close_when_idle()
            return
        event.accept()

    def refresh_status(self):
        def check():
            states = {}
            for key, unit in (("api", MOBILE_SERVICE), ("voice", VOICE_SERVICE)):
                result = subprocess.run(["systemctl", "--user", "is-active", unit], capture_output=True, text=True, timeout=5)
                states[key] = result.stdout.strip() == "active"
            try:
                status, _ = _request("/health", timeout=4)
                states["reachable"] = status == 200
            except Exception:
                states["reachable"] = False
            return states

        def update(states):
            self.api_status.value_label.setText("Conectado" if states["reachable"] else "Offline")
            self.api_status.value_label.setStyleSheet("color: #66db9b" if states["reachable"] else "color: #f39a86")
            self.connect_button.setText("Vladmir conectado" if states["reachable"] else "Iniciar Vladmir")
            self.connect_button.setEnabled(not states["reachable"])
            self.voice_active = states["voice"]
            self.voice_status.value_label.setText("Ativa" if self.voice_active else "Desligada")
            self.voice_status.value_label.setStyleSheet("color: #66db9b" if self.voice_active else "color: #91a4b4")
            self.voice_button.setText("Parar escuta" if self.voice_active else "Iniciar escuta")
            self.connection_label.setText("Vladmir está pensando…" if self.busy else "Conectado · memória compartilhada" if states["reachable"] else "Offline · inicie o Vladmir")

        self._task(check, update)

    def send_message(self):
        message = self.input.toPlainText().strip()
        paths = list(self.attachments)
        if self.busy or (not message and not paths):
            return
        if paths and not message:
            message = "Analise os arquivos anexados e me ajude com eles."
        self.input.clear()
        visible_message = message
        if paths:
            visible_message += "\n\nArquivos: " + " · ".join(path.name for path in paths)
        conversation_id = self.current_conversation_id
        request_messages = self._conversation_request_messages(message)
        self._save_conversation_message("user", visible_message)
        self._append_bubble(visible_message, "user", source="desktop-chat")
        install_request = parse_install_request(message) if not paths else None
        if install_request:
            self.conversation_selector.setEnabled(True)
            self.new_conversation_button.setEnabled(True)
            self._begin_package_install(install_request)
            return
        self.busy = True
        self.send_button.setDisabled(True)
        self.attach_button.setDisabled(True)
        self.conversation_selector.setEnabled(False)
        self.new_conversation_button.setEnabled(False)
        self.remove_attachment_button.setDisabled(True)
        self.send_button.setIcon(QIcon())
        self.send_button.setText("…")
        self.connection_label.setText("Vladmir está pensando…")
        specialization = self.current_specialization
        context_payload = {
            "specialization": specialization,
            "session_id": conversation_id,
        }
        if self.current_project_id:
            context_payload["project_id"] = self.current_project_id
        if self.current_task_id:
            context_payload["task_id"] = self.current_task_id
        profile = self.model_selector.currentData()
        reasoning_level = self.reasoning_selector.currentData() if profile == "vladmir" else "instant"
        engineer_mode = specialization == "engineer"
        engineer_multimodal = engineer_mode and any(
            path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} for path in paths
        )
        if engineer_mode:
            self.engineer_work_label.setText(
                "Imagem anexada · usando o perfil multimodal do Vladmir" if engineer_multimodal
                else "Preparando contexto e consultando o modelo Engineer…"
            )
            self.engineer_chat_badge.setText(
                "ENGINEER · VISÃO MULTIMODAL" if engineer_multimodal else "ENGINEER · PERFIL DE CÓDIGO"
            )
            self.engineer_work_feedback.setVisible(True)

        def ask():
            prepared = _prepare_attachments(paths)
            content = [{"type": "text", "text": message}]
            file_context = []
            for item in prepared:
                if "data" in item:
                    data_url = f"data:{item['mime']};base64,{item['data']}"
                    content.append({"type": "image_url", "image_url": {"url": data_url}})
                    content.append({"type": "text", "text": f"[Imagem anexada: {item['name']}]"})
                else:
                    file_context.append({"name": item["name"], "text": item["text"]})
            _, body = _request("/v1/chat/completions", {
                "model": profile, "stream": False,
                "vladmir_reasoning_level": reasoning_level,
                "messages": request_messages,
                "vladmir_attachments": file_context,
                "vladmir_context": context_payload,
            })
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]

        def done(reply):
            self.busy = False
            self.engineer_work_feedback.hide()
            if engineer_mode:
                self.engineer_chat_badge.setText("ENGINEER · PERFIL DE CÓDIGO")
            self.send_button.setDisabled(False)
            self.attach_button.setDisabled(False)
            self.conversation_selector.setEnabled(True)
            self.new_conversation_button.setEnabled(True)
            self.send_button.setText("")
            self.send_button.setIcon(_mark_icon("send"))
            self.attachments.clear()
            self._refresh_attachment_list()
            self._save_conversation_message("assistant", reply, conversation_id)
            if self.current_conversation_id == conversation_id:
                self._append_bubble(reply, "assistant")
            self.last_assistant_reply = reply
            self.connection_label.setText("Conectado ao Vladmir · memória compartilhada")
            self.input.setFocus()

        def failed(message):
            self.busy = False
            self.engineer_work_feedback.hide()
            if engineer_mode:
                self.engineer_chat_badge.setText("ENGINEER · PERFIL DE CÓDIGO")
            self.send_button.setDisabled(False)
            self.attach_button.setDisabled(False)
            self.conversation_selector.setEnabled(True)
            self.new_conversation_button.setEnabled(True)
            self.remove_attachment_button.setEnabled(self.attachment_list.currentRow() >= 0)
            self.send_button.setText("")
            self.send_button.setIcon(_mark_icon("send"))
            self.input.setPlainText(message)
            self._append_bubble("Não consegui falar com o Vladmir. " + message, "assistant")
            self.refresh_status()

        self._task(ask, done, failed)

    def _begin_package_install(self, request):

        self.busy = True
        self.send_button.setDisabled(True)
        self.attach_button.setDisabled(True)
        self.send_button.setText("…")
        self.send_button.setIcon(QIcon())
        self.connection_label.setText("Verificando pacote e origem…")

        def ready(info):
            details = (f"Pacote: {info['package']}\nVersão: {info['version']}\nOrigem: {info['source']}"
                       + (f"\nDescrição: {info['description']}" if info.get("description") else "")
                       + (f"\nAviso: {info['warning']}" if info.get("warning") else "")
                       + ("\nPacotes na transação: " + str(info["transaction_count"])
                          + ("\nPrévia: " + ", ".join(info["transaction_preview"])
                             + (" …" if info["transaction_count"] > len(info["transaction_preview"]) else "")
                             if info.get("transaction_preview") else "")
                          if info.get("transaction_count") is not None else "")
                       + "\n\nAntes de instalar, o Vladmir salvará um backup privado do inventário atual de programas. "
                         "Se não conseguir salvar o backup, a instalação será cancelada. "
                         "Se autorizar, o Vladmir instalará somente este pacote. Dependências serão tratadas pelo gerenciador. "
                         "No caso do pacman, o Polkit também pedirá autenticação do sistema."
                       + "\n\nO Vladmir não usa AUR, scripts arbitrários nem instruções vindas de páginas.")
            box = QMessageBox(self)
            box.setWindowTitle("Autorizar instalação")
            box.setTextFormat(Qt.TextFormat.PlainText)
            box.setText("O Vladmir encontrou este pacote:")
            box.setInformativeText(details)
            box.setIcon(QMessageBox.Icon.Question)
            approve = box.addButton("Autorizar instalação", QMessageBox.ButtonRole.AcceptRole)
            cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel)
            box.exec()
            if box.clickedButton() != approve:
                self._finish_package_install("Instalação cancelada; nada foi instalado.")
                return
            self.connection_label.setText("Aguardando o gerenciador de pacotes…")
            self._task(lambda: install_package(request), self._finish_package_install,
                       lambda error: self._finish_package_install("Instalação não concluída: " + error))

        self._task(lambda: inspect_package(request), ready,
                   lambda error: self._finish_package_install("Não iniciei a instalação: " + error))

    def _finish_package_install(self, reply):
        self.busy = False
        self.send_button.setDisabled(False)
        self.attach_button.setDisabled(False)
        self.remove_attachment_button.setEnabled(self.attachment_list.currentRow() >= 0)
        self.send_button.setText("")
        self.send_button.setIcon(_mark_icon("send"))
        self._append_bubble(reply, "assistant")
        self.last_assistant_reply = reply
        self.connection_label.setText("Conectado ao Vladmir · memória compartilhada")
        self.input.setFocus()

    def add_attachments(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Anexar arquivos", str(Path.home()),
            "Arquivos aceitos (*.jpg *.jpeg *.png *.webp *.pdf *.docx *.txt *.md *.csv *.json *.yaml *.yml *.xml *.html *.py *.log *.toml *.ini *.cfg);;Todos os arquivos (*)",
        )
        if not paths:
            return
        self._add_attachment_paths(paths)

    def _set_drop_target_state(self, active: bool):
        self.composer_box.setProperty("dropActive", active)
        self.composer_box.style().unpolish(self.composer_box)
        self.composer_box.style().polish(self.composer_box)
        self.composer_box.update()
        if active:
            self.composer_hint.setText("Solte para anexar · até 5 arquivos")
        else:
            self.composer_hint.setText("Enter envia · Shift+Enter quebra a linha")

    def _add_attachment_paths(self, paths):
        accepted = set(self.attachments)
        for name in paths:
            path = Path(name)
            if path in accepted:
                continue
            if len(self.attachments) >= MAX_ATTACHMENTS:
                QMessageBox.information(self, "Anexos", f"O limite é de {MAX_ATTACHMENTS} arquivos por mensagem.")
                break
            if not path.is_file():
                QMessageBox.warning(self, "Anexos", f"{path.name} não é um arquivo regular.")
                continue
            if path.suffix.lower() not in TEXT_ATTACHMENT_EXTENSIONS | {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".webp"}:
                QMessageBox.warning(self, "Anexos", f"Formato não suportado: {path.name}.")
                continue
            try:
                new_size = path.stat().st_size
                current_size = sum(item.stat().st_size for item in self.attachments)
            except OSError:
                QMessageBox.warning(self, "Anexos", f"Não consegui acessar {path.name}.")
                continue
            if new_size > MAX_ATTACHMENT_BYTES:
                QMessageBox.warning(self, "Anexos", f"{path.name} excede o limite de 6 MB por arquivo.")
                continue
            if current_size + new_size > MAX_ATTACHMENTS_TOTAL:
                QMessageBox.warning(self, "Anexos", "Os anexos juntos não podem passar de 8 MB.")
                continue
            self.attachments.append(path)
            accepted.add(path)
        self._refresh_attachment_list()

    def remove_selected_attachment(self):
        index = self.attachment_list.currentRow()
        if 0 <= index < len(self.attachments):
            self.attachments.pop(index)
            self._refresh_attachment_list()

    def _refresh_attachment_list(self):
        self.attachment_list.clear()
        for path in self.attachments:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            label = f"{path.name}  ·  {size / 1024:.0f} KB"
            self.attachment_list.addItem(label)
        self.attachment_list.setVisible(bool(self.attachments))
        self.remove_attachment_button.setVisible(bool(self.attachments))
        self.remove_attachment_button.setEnabled(
            bool(self.attachments) and self.attachment_list.currentRow() >= 0
        )

    def toggle_voice(self):
        starting = not self.voice_active
        self.voice_button.setDisabled(True)
        action = "start" if starting else "stop"

        def done(_):
            self.voice_button.setDisabled(False)
            self.refresh_status()

        def failed(message):
            self.voice_button.setDisabled(False)
            QMessageBox.warning(self, "Vladmir", "Não consegui alterar a escuta por voz.\n\n" + message)
            self.refresh_status()

        self._task(lambda: _service(action, VOICE_SERVICE), done, failed)

    def start_mark(self):
        self.connect_button.setDisabled(True)

        def start():
            _service("start", MOBILE_SERVICE)
            return True

        def done(_):
            self.refresh_status()

        def failed(message):
            self.connect_button.setEnabled(True)
            QMessageBox.warning(self, "Vladmir", "Não consegui iniciar o serviço do Vladmir.\n\n" + message)

        self._task(start, done, failed)

    def open_call(self):
        CallDialog(self).exec()

    def open_agenda(self):
        dialog = AgendaDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_email_composer(self):
        dialog = EmailComposerDialog(self.last_assistant_reply, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_github(self):
        from .plugins import enabled as plugin_enabled
        from .config import load_config
        if not plugin_enabled("github", load_config()):
            QMessageBox.information(self, "Plugins", "Ative o plugin GitHub em Ferramentas → Plugins.")
            return
        dialog = GitHubDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_mobile_devices(self):
        dialog = MobileDevicesDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_chat(self):
        self.open_specialized_chat("general")

    def open_library(self):
        if not hasattr(self,'library_page'):
            from .desktop_library import LibraryPage
            from .cognition.knowledge import DEFAULT_DB
            from .config import load_config
            cfg=load_config()
            self.library_page=LibraryPage(self,Path(cfg.get('cognition',{}).get('knowledge_db',str(DEFAULT_DB))))
            self.page_stack.addWidget(self.library_page)
        self._set_active_area("library")
        self.page_stack.setCurrentWidget(self.library_page)

    def open_memory_manager(self):
        from .desktop_memory import MemoryDialog
        dialog = MemoryDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_provider_manager(self):
        from .desktop_providers import ProviderDialog
        dialog = ProviderDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_plugins(self):
        from .desktop_plugins import PluginsDialog
        dialog = PluginsDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_jetbrains(self):
        from .desktop_jetbrains import JetBrainsDialog
        dialog = JetBrainsDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_sentinel(self):
        from .desktop_sentinel import SentinelDialog
        dialog = SentinelDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_missions(self):
        from .desktop_missions import MissionDialog
        dialog = MissionDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_evolution(self):
        self.open_area("evolution")

    def open_evolution_dialog(self):
        from .desktop_evolution import EvolutionDialog
        dialog=EvolutionDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def open_vision(self):
        from .plugins import enabled as plugin_enabled
        from .config import load_config
        if not plugin_enabled("gods_eye", load_config()):
            QMessageBox.information(self, "Plugins", "Ative o plugin God’s Eye View em Ferramentas → Plugins.")
            return
        from .desktop_vision import VisionDialog
        dialog = VisionDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def test_camera(self):
        button = self.sender()
        if isinstance(button, QPushButton):
            button.setDisabled(True)
            button.setText("Testando câmera…")

        def check():
            result = subprocess.run([str(ROOT / "scripts/test_camera.sh")], capture_output=True, text=True, timeout=35)
            if result.returncode:
                raise RuntimeError((result.stdout or "A câmera não respondeu.").strip())
            return (result.stdout or "Captura da câmera: OK.").strip()

        def done(message):
            button.setDisabled(False)
            button.setText("Testar câmera")
            QMessageBox.information(self, "Teste da câmera", message)

        def failed(message):
            button.setDisabled(False)
            button.setText("Testar câmera")
            QMessageBox.warning(self, "Teste da câmera", message)

        self._task(check, done, failed)

    def clear_memory(self):
        phrase, accepted = QInputDialog.getText(
            self,
            "Apagar conversa",
            "Esta ação apaga a conversa compartilhada em todos os dispositivos.\n\n"
            "Para confirmar, digite Vladmir:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or phrase != "Vladmir":
            return
        self.busy = True
        self.send_button.setDisabled(True)

        def clear():
            _, body = _request("/v1/chat/completions", {
                "model": "vladmir", "stream": False,
                "messages": [{"role": "user", "content": "limpa a memória"}],
            })
            return json.loads(body)["choices"][0]["message"]["content"]

        def done(reply):
            self.busy = False
            self.send_button.setDisabled(False)
            while self.chat_layout.count() > 1:
                item = self.chat_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self._append_bubble(reply, "assistant")

        def failed(message):
            self.busy = False
            self.send_button.setDisabled(False)
            QMessageBox.warning(self, "Vladmir", "Não foi possível limpar a conversa.\n\n" + message)

        self._task(clear, done, failed)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Vladmir")
    app.setOrganizationName("Vladmir")
    window = MarkWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
