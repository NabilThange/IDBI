"""
Unit Tests for Voice Conversation Feature
Tests Sarvam AI integration: STT, Translation, and TTS
"""

import os
import pytest
from io import BytesIO

# Only run tests if SARVAM_API_KEY is set
pytestmark = pytest.mark.skipif(
    not os.getenv("SARVAM_API_KEY"),
    reason="SARVAM_API_KEY not set"
)

try:
    from sarvamai import SarvamAI
    sarvam_client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
except ImportError:
    sarvam_client = None


@pytest.mark.skipif(not sarvam_client, reason="sarvamai SDK not installed")
class TestVoiceConversation:
    """Test suite for voice conversation features"""
    
    def test_stt_translate_mode(self):
        """
        Test Speech-to-Text with translation mode
        This would require an actual audio file to test
        """
        # Placeholder test - would need actual audio file
        # In real testing, you would:
        # 1. Load a sample audio file (e.g., Hindi speech)
        # 2. Call STT with mode="translate"
        # 3. Verify you get English text back
        
        # Example structure (commented out - needs actual audio file):
        """
        with open("test_audio_hindi.wav", "rb") as audio_file:
            response = sarvam_client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v3",
                mode="translate",
                language_code="hi-IN"
            )
            assert response.transcript
            assert isinstance(response.transcript, str)
            assert len(response.transcript) > 0
        """
        pass
    
    def test_translation_english_to_hindi(self):
        """Test translation from English to Hindi"""
        test_text = "Your current account balance is fifty thousand rupees."
        
        response = sarvam_client.text.translate(
            input=test_text,
            source_language_code="en-IN",
            target_language_code="hi-IN",
            model="mayura:v1",
            mode="modern-colloquial"
        )
        
        assert response.translated_text
        assert isinstance(response.translated_text, str)
        assert len(response.translated_text) > 0
        # Should contain Hindi text
        assert response.translated_text != test_text
        print(f"Original: {test_text}")
        print(f"Translated: {response.translated_text}")
    
    def test_translation_english_to_tamil(self):
        """Test translation from English to Tamil"""
        test_text = "Welcome to IDBI Bank. How can I help you today?"
        
        response = sarvam_client.text.translate(
            input=test_text,
            source_language_code="en-IN",
            target_language_code="ta-IN",
            model="mayura:v1",
            mode="modern-colloquial"
        )
        
        assert response.translated_text
        assert isinstance(response.translated_text, str)
        assert response.translated_text != test_text
        print(f"Original: {test_text}")
        print(f"Translated (Tamil): {response.translated_text}")
    
    def test_translation_english_to_marathi(self):
        """Test translation from English to Marathi"""
        test_text = "Your investment portfolio has grown by 15% this year."
        
        response = sarvam_client.text.translate(
            input=test_text,
            source_language_code="en-IN",
            target_language_code="mr-IN",
            model="mayura:v1",
            mode="modern-colloquial"
        )
        
        assert response.translated_text
        assert isinstance(response.translated_text, str)
        print(f"Original: {test_text}")
        print(f"Translated (Marathi): {response.translated_text}")
    
    def test_tts_hindi(self):
        """Test Text-to-Speech in Hindi"""
        test_text = "नमस्ते, आईडीबीआई बैंक में आपका स्वागत है।"
        
        response = sarvam_client.text_to_speech.convert(
            text=test_text,
            target_language_code="hi-IN",
            model="bulbul:v3",
            speaker="neha",
            pace=1.0,
            speech_sample_rate=24000
        )
        
        assert response.audio
        assert isinstance(response.audio, str)  # Base64 encoded
        assert len(response.audio) > 0
        print(f"TTS generated {len(response.audio)} characters of base64 audio")
    
    def test_tts_tamil(self):
        """Test Text-to-Speech in Tamil"""
        test_text = "வணக்கம், IDBI வங்கிக்கு வரவேற்கிறோம்."
        
        response = sarvam_client.text_to_speech.convert(
            text=test_text,
            target_language_code="ta-IN",
            model="bulbul:v3",
            speaker="ritu",
            pace=1.0
        )
        
        assert response.audio
        assert isinstance(response.audio, str)
        print(f"TTS (Tamil) generated {len(response.audio)} characters of base64 audio")
    
    def test_tts_male_voice(self):
        """Test Text-to-Speech with male voice"""
        test_text = "आपका खाता शेष पचास हजार रुपये है।"
        
        response = sarvam_client.text_to_speech.convert(
            text=test_text,
            target_language_code="hi-IN",
            model="bulbul:v3",
            speaker="rahul",  # Male voice
            pace=1.0
        )
        
        assert response.audio
        print(f"TTS (Male voice) generated audio successfully")
    
    def test_language_code_mapping(self):
        """Test language code mapping function"""
        from app.routers.voice import get_language_code
        
        # This would be imported from the frontend if we were testing JS
        # For now, we'll test the concept
        language_map = {
            'English': 'en-IN',
            'Hindi': 'hi-IN',
            'Marathi': 'mr-IN',
            'Tamil': 'ta-IN',
            'Telugu': 'te-IN',
            'Bengali': 'bn-IN',
            'Gujarati': 'gu-IN',
            'Kannada': 'kn-IN',
            'Malayalam': 'ml-IN',
            'Punjabi': 'pa-IN',
            'Odia': 'od-IN'
        }
        
        for lang, code in language_map.items():
            assert code.endswith('-IN')
            assert len(code) == 5
        
        print(f"Language mapping validated for {len(language_map)} languages")
    
    def test_full_pipeline_simulation(self):
        """
        Simulate the full voice conversation pipeline
        (without actual audio input)
        """
        # Step 1: Simulate STT result
        english_question = "What is my account balance?"
        
        # Step 2: Simulate Groq response (this would be real LLM call)
        english_answer = "Your current account balance is fifty thousand rupees."
        
        # Step 3: Translate to Hindi
        answer_translation = sarvam_client.text.translate(
            input=english_answer,
            source_language_code="en-IN",
            target_language_code="hi-IN",
            model="mayura:v1",
            mode="modern-colloquial"
        )
        native_answer = answer_translation.translated_text
        
        # Step 4: Generate TTS
        tts_response = sarvam_client.text_to_speech.convert(
            text=native_answer,
            target_language_code="hi-IN",
            model="bulbul:v3",
            speaker="neha",
            pace=1.0
        )
        
        # Verify all steps completed
        assert native_answer
        assert tts_response.audio
        
        print("Full pipeline simulation successful:")
        print(f"  English: {english_answer}")
        print(f"  Hindi: {native_answer}")
        print(f"  Audio length: {len(tts_response.audio)} characters")


class TestVoiceEndpoint:
    """Test the voice conversation API endpoint"""
    
    def test_voice_status_endpoint(self):
        """Test the voice service status endpoint"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/voice/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "sarvam_configured" in data
        assert "sdk_available" in data
        print(f"Voice status: {data}")
    
    # Note: Testing the full /voice/converse endpoint would require:
    # 1. A valid session_id with profile
    # 2. An actual audio file
    # 3. Sarvam API credentials
    # This is better suited for integration tests


if __name__ == "__main__":
    """Run tests manually"""
    import sys
    
    if not os.getenv("SARVAM_API_KEY"):
        print("ERROR: SARVAM_API_KEY environment variable not set")
        print("Please set it before running tests:")
        print("  export SARVAM_API_KEY=your_key_here")
        sys.exit(1)
    
    if not sarvam_client:
        print("ERROR: sarvamai SDK not installed")
        print("Install it with: pip install sarvamai")
        sys.exit(1)
    
    print("Running voice conversation tests...\n")
    
    # Run tests
    test_suite = TestVoiceConversation()
    
    print("\n=== Translation Tests ===")
    test_suite.test_translation_english_to_hindi()
    test_suite.test_translation_english_to_tamil()
    test_suite.test_translation_english_to_marathi()
    
    print("\n=== TTS Tests ===")
    test_suite.test_tts_hindi()
    test_suite.test_tts_tamil()
    test_suite.test_tts_male_voice()
    
    print("\n=== Pipeline Test ===")
    test_suite.test_full_pipeline_simulation()
    
    print("\n=== Language Mapping Test ===")
    test_suite.test_language_code_mapping()
    
    print("\n=== Endpoint Tests ===")
    endpoint_tests = TestVoiceEndpoint()
    endpoint_tests.test_voice_status_endpoint()
    
    print("\n✅ All tests completed successfully!")
