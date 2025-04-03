#!/usr/bin/env python3
import os
import sys
import time
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QPalette, QTextCursor
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread

# Path to assets
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

class AssistantState(Enum):
    """States for the voice assistant."""
    IDLE = 0
    LISTENING = 1
    THINKING = 2
    SPEAKING = 3

class RecordingThread(QThread):
    """Thread for handling recording."""
    finished = pyqtSignal(object, str)  # Signals to emit recording results
    state_changed = pyqtSignal(AssistantState)  # Signal to update UI state
    
    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.running = False
        
    def run(self):
        """Record audio and emit result."""
        self.running = True
        self.state_changed.emit(AssistantState.LISTENING)
        
        # Record audio
        wav_buffer, wav_filename = self.recorder.wait_for_space_key_recording()
        
        # Signal completion
        self.finished.emit(wav_buffer, wav_filename)
        self.running = False

class ProcessingThread(QThread):
    """Thread for processing audio and generating response."""
    finished = pyqtSignal()
    text_updated = pyqtSignal(str)
    state_changed = pyqtSignal(AssistantState)
    
    def __init__(self, transcribe_func, chat_func, tts_func, play_func, chunk_text_func):
        super().__init__()
        self.wav_buffer = None
        self.transcribe_func = transcribe_func
        self.chat_func = chat_func
        self.tts_func = tts_func
        self.play_func = play_func
        self.chunk_text_func = chunk_text_func
        
    def set_audio(self, wav_buffer):
        """Set the audio buffer to process."""
        self.wav_buffer = wav_buffer
        
    def run(self):
        """Process audio and generate response."""
        if not self.wav_buffer:
            self.finished.emit()
            return
            
        # Transcribe audio
        self.state_changed.emit(AssistantState.THINKING)
        transcription = self.transcribe_func(self.wav_buffer)
        
        if transcription is None:
            self.finished.emit()
            return
            
        self.text_updated.emit(f"You said: {transcription}")
        
        # Generate response
        full_response = ""
        current_buffer = ""  # Buffer for accumulating text chunks
        
        self.state_changed.emit(AssistantState.SPEAKING)
        
        for chunk in self.chat_func(transcription, True):
            if chunk["type"] == "content":
                content = chunk["data"]
                full_response += content
                self.text_updated.emit(f"Assistant: {full_response}")
                
                # Process text using the chunking utility
                chunk_to_process, current_buffer = self.chunk_text_func(content, current_buffer)
                
                if chunk_to_process:
                    # Generate and play speech for this chunk
                    chunk_audio_path = self.tts_func(chunk_to_process, 2.0)
                    if chunk_audio_path:
                        # Play the generated chunk speech without blocking
                        self.play_func(chunk_audio_path, block=False)
        
        # Process any remaining text in buffer
        if current_buffer.strip():
            chunk_audio_path = self.tts_func(current_buffer, 2.0)
            if chunk_audio_path:
                self.play_func(chunk_audio_path, block=True)
        
        self.finished.emit()

class VoiceAssistantUI(QMainWindow):
    """Main UI class for the voice assistant."""
    
    def __init__(self, recording_handler, transcribe_func, chat_func, tts_func, play_func, chunk_text_func):
        super().__init__()
        
        # Store function references
        self.recording_handler = recording_handler
        self.transcribe_func = transcribe_func
        self.chat_func = chat_func
        self.tts_func = tts_func
        self.play_func = play_func
        self.chunk_text_func = chunk_text_func
        
        # Initialize threads
        self.recording_thread = RecordingThread(self.recording_handler)
        self.recording_thread.finished.connect(self.on_recording_finished)
        self.recording_thread.state_changed.connect(self.update_state)
        
        self.processing_thread = ProcessingThread(
            self.transcribe_func, self.chat_func, self.tts_func, 
            self.play_func, self.chunk_text_func
        )
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.text_updated.connect(self.update_text_display)
        self.processing_thread.state_changed.connect(self.update_state)
        
        # Initialize UI
        self.init_ui()
        
        # Set initial state
        self.current_state = AssistantState.IDLE
        self.update_state(self.current_state)
        
        # Start recording thread automatically
        self.recording_thread.start()
        
    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Voice assistant")
        self.setMinimumSize(900, 800)  # Even larger window to fit more text
        
        # Set theme colors
        self.set_dark_theme()
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setCentralWidget(main_widget)
        
        # Status display area (center of the UI)
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        self.status_frame.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); border-radius: 30px;")
        
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setAlignment(Qt.AlignCenter)
        status_layout.setContentsMargins(40, 40, 40, 40)
        
        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setMinimumSize(300, 300)  # Smaller icon to make room for text
        self.status_icon.setMaximumSize(300, 300)
        self.status_icon.setStyleSheet("font-size: 150pt;")  # Smaller font for emoji
        
        status_layout.addWidget(self.status_icon, alignment=Qt.AlignCenter)
        
        # Text display - using QTextEdit instead of QLabel for better text handling
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Arial", 24))
        self.text_display.setStyleSheet("""
            QTextEdit {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
            }
        """)
        self.text_display.setAlignment(Qt.AlignCenter)
        self.text_display.setMinimumHeight(350)  # Much taller to fit more text
        self.text_display.setText("Press and hold SPACE to record, release to process")
        self.text_display.document().setDocumentMargin(10)
        
        status_layout.addWidget(self.text_display, 1)  # Give it a stretch factor of 1
        
        main_layout.addWidget(self.status_frame, 1)
        
        # Exit button
        self.exit_button = QPushButton("Exit")
        self.exit_button.setFont(QFont("Arial", 28, QFont.Bold))
        self.exit_button.setMinimumHeight(100)
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 50px;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A93226;
            }
        """)
        self.exit_button.clicked.connect(self.close)
        
        main_layout.addWidget(self.exit_button)
        
    def update_state(self, state):
        """Update UI based on the current state."""
        self.current_state = state
        
        # Update status icon based on state
        self.status_icon.clear()
        
        if state == AssistantState.IDLE:
            self.status_icon.setText("🔍")
            self.text_display.setText("Press and hold SPACE to record, release to process")
            
        elif state == AssistantState.LISTENING:
            self.status_icon.setText("🎤")
            self.text_display.setText("Listening...")
            
        elif state == AssistantState.THINKING:
            self.status_icon.setText("⟳")
            self.text_display.setText("Processing...")
            
        elif state == AssistantState.SPEAKING:
            self.status_icon.setText("🔊")
    
    def update_text_display(self, text):
        """Update the text display."""
        # Translate common prefixes
        if text.startswith("You said: "):
            text = "You said: " + text[10:]
        elif text.startswith("Assistant: "):
            text = "Assistant: " + text[11:]
        
        # Set the text with HTML formatting to ensure line breaks work
        self.text_display.setHtml(f"<div align='center'>{text.replace('\n', '<br>')}</div>")
        
        # Ensure text is always visible by scrolling to the top
        self.text_display.moveCursor(QTextCursor.Start)
    
    def on_recording_finished(self, wav_buffer, wav_filename):
        """Handle recording completion."""
        if wav_buffer:
            # Start processing the recording
            self.processing_thread.set_audio(wav_buffer)
            self.processing_thread.start()
        else:
            # Recording failed or cancelled
            self.update_state(AssistantState.IDLE)
            self.text_display.setText("Recording cancelled or failed")
            # Restart recording thread
            if not self.recording_thread.isRunning():
                self.recording_thread.start()
    
    def on_processing_finished(self):
        """Handle processing completion."""
        self.update_state(AssistantState.IDLE)
        # Restart recording thread
        if not self.recording_thread.isRunning():
            self.recording_thread.start()
    
    def set_dark_theme(self):
        """Set dark theme for the application."""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
        self.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
    
    def closeEvent(self, event):
        """Clean up when window is closed."""
        # Clean up threads
        if self.recording_thread.isRunning():
            self.recording_thread.terminate()
        if self.processing_thread.isRunning():
            self.processing_thread.terminate()
        
        # Clean up recording handler if needed
        if hasattr(self.recording_handler, 'close'):
            self.recording_handler.close()
        
        super().closeEvent(event)
