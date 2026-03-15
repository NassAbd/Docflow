import os
import unittest
from unittest.mock import patch, MagicMock
from app.services import classifier, extractor

class TestProviderSwitch(unittest.TestCase):
    
    @patch('app.services.classifier._classify_with_ollama')
    @patch('app.services.classifier._classify_with_groq')
    def test_classifier_provider_switch(self, mock_groq, mock_ollama):
        # Test Ollama (default)
        os.environ["LLM_PROVIDER"] = "ollama"
        classifier.classify_document("test text")
        mock_ollama.assert_called_once()
        mock_groq.assert_not_called()
        
        mock_ollama.reset_mock()
        mock_groq.reset_mock()
        
        # Test Groq
        os.environ["LLM_PROVIDER"] = "groq"
        classifier.classify_document("test text")
        mock_groq.assert_called_once()
        mock_ollama.assert_not_called()

    @patch('app.services.extractor._call_ollama')
    @patch('app.services.extractor._call_groq')
    def test_extractor_provider_switch(self, mock_groq, mock_ollama):
        mock_ollama.return_value = "{}"
        mock_groq.return_value = "{}"
        
        # Test Ollama
        os.environ["LLM_PROVIDER"] = "ollama"
        extractor.extract_document_data("test text")
        mock_ollama.assert_called_once()
        mock_groq.assert_not_called()
        
        mock_ollama.reset_mock()
        mock_groq.reset_mock()
        
        # Test Groq
        os.environ["LLM_PROVIDER"] = "groq"
        extractor.extract_document_data("test text")
        mock_groq.assert_called_once()
        mock_ollama.assert_not_called()

if __name__ == '__main__':
    unittest.main()
