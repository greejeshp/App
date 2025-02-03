import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from flask import Flask, request, jsonify, render_template
import threading
import tempfile
from transformers import pipeline
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import docx
import logging
from pathlib import Path

# Initialize Flask application
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the AI model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

class DocumentAnalyzer:
    @staticmethod
    def process_image(image_path):
        """Process image files using OCR."""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return None

    @staticmethod
    def process_pdf(pdf_path):
        """Process PDF files."""
        try:
            text = ""
            pdf_document = fitz.open(pdf_path)
            for page in pdf_document:
                text += page.get_text()
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return None

    @staticmethod
    def process_doc(doc_path):
        """Process DOC/DOCX files."""
        try:
            doc = docx.Document(doc_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing DOC: {str(e)}")
            return None

    @staticmethod
    def summarize_text(text):
        """Generate summary using AI model."""
        try:
            chunks = [text[i:i+1024] for i in range(0, len(text), 1024)]
            summaries = []
            for chunk in chunks:
                summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
                summaries.append(summary)
            return " ".join(summaries)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None

@app.route('/')
def home():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    """Handle file upload and analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Create temporary directory for file processing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)

            # Process based on file type
            file_ext = Path(file.filename).suffix.lower()
            analyzer = DocumentAnalyzer()

            if file_ext in ['.jpg', '.jpeg', '.png']:
                text = analyzer.process_image(temp_path)
            elif file_ext == '.pdf':
                text = analyzer.process_pdf(temp_path)
            elif file_ext in ['.doc', '.docx']:
                text = analyzer.process_doc(temp_path)
            else:
                return jsonify({'error': 'Unsupported file type'}), 400

            if not text:
                return jsonify({'error': 'Could not extract text from file'}), 400

            # Generate summary
            summary = analyzer.summarize_text(text)
            if not summary:
                return jsonify({'error': 'Could not generate summary'}), 500

            return jsonify({
                'summary': summary,
                'original_text': text
            })

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': 'Error processing file'}), 500

class MainWindow(QMainWindow):
    """Main window for the desktop application."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Document Analyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create web view
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl('http://localhost:5000'))
        self.setCentralWidget(self.web_view)

def run_flask():
    """Run Flask server in debug mode."""
    app.run(debug=True, use_reloader=False)

def main():
    """Main entry point for the application."""
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Create Qt application
    qt_app = QApplication(sys.argv)
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start Qt event loop
    sys.exit(qt_app.exec_())

if __name__ == '__main__':
    main()