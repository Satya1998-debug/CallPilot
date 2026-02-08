#!/usr/bin/env python3
"""Test ElevenLabs Speech-to-Text (STT) functionality."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_elevenlabs_stt():
    """Test ElevenLabs STT with a sample audio file."""
    
    # Check API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ERROR: ELEVENLABS_API_KEY not found in environment")
        print("   Add it to your .env file:")
        print("   ELEVENLABS_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Import ElevenLabs client
    try:
        from elevenlabs.client import ElevenLabs
        print("✅ ElevenLabs client imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import ElevenLabs: {e}")
        print("   Install it with: pip install elevenlabs")
        return False
    
    # Test with a sample audio file (you need to provide one)
    # For now, let's test the API connection
    try:
        client = ElevenLabs(api_key=api_key)
        print("✅ ElevenLabs client initialized")
        
        # Check if speech_to_text exists
        stt = getattr(client, "speech_to_text", None)
        if stt:
            print("✅ speech_to_text module available")
            print(f"   Methods: {dir(stt)}")
            
            if hasattr(stt, "convert"):
                print("✅ convert() method found")
            else:
                print("⚠️  convert() method not found")
                print(f"   Available methods: {[m for m in dir(stt) if not m.startswith('_')]}")
        else:
            print("❌ speech_to_text module not available in this ElevenLabs version")
            print("   You may need to upgrade elevenlabs package")
            return False
            
    except Exception as e:
        print(f"❌ ERROR initializing client: {e}")
        return False
    
    # Test with sample audio if file exists
    sample_audio_path = Path("test_audio.mp3")
    if sample_audio_path.exists():
        print(f"\n📁 Found sample audio: {sample_audio_path}")
        print("🎤 Testing STT conversion...")
        
        try:
            with open(sample_audio_path, "rb") as f:
                audio_bytes = f.read()
            
            # Use correct API signature (requires model_id and file)
            # Available models: 'scribe_v1', 'scribe_v1_experimental', 'scribe_v2'
            model_id = os.getenv("ELEVENLABS_STT_MODEL_ID", "scribe_v1")
            print(f"   Using model_id: {model_id}")
            
            result = stt.convert(
                model_id=model_id,
                file=audio_bytes
            )
            
            # Extract text from result
            if isinstance(result, dict) and "text" in result:
                transcript = result["text"]
            elif hasattr(result, "text"):
                transcript = result.text
            else:
                transcript = str(result)
            
            print(f"✅ Transcription successful!")
            print(f"📝 Result: {transcript}")
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"\n⚠️  No test audio file found at {sample_audio_path}")
        print("   To test actual conversion, add a test_audio.mp3 file")
        print("   Or record audio using the Streamlit app")
    
    print("\n✅ All basic checks passed!")
    return True


def create_test_audio():
    """Generate a simple test audio file using TTS (for testing STT)."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ Need API key to generate test audio")
        return
    
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        
        print("🎙️  Generating test audio using TTS...")
        audio = client.text_to_speech.convert(
            text="Hello, this is a test of the ElevenLabs speech to text system.",
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
            model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            output_format="mp3_44100_128",
        )
        
        # Save audio
        if isinstance(audio, (bytes, bytearray)):
            audio_bytes = bytes(audio)
        else:
            audio_bytes = b"".join(audio)
        
        with open("test_audio.mp3", "wb") as f:
            f.write(audio_bytes)
        
        print("✅ Test audio saved to test_audio.mp3")
        print("   You can use this to test STT")
        
    except Exception as e:
        print(f"❌ Failed to generate test audio: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ElevenLabs Speech-to-Text Test")
    print("=" * 60)
    print()
    
    # Run basic tests
    success = test_elevenlabs_stt()
    
    if success:
        print("\n" + "=" * 60)
        print("Would you like to generate a test audio file?")
        print("This will use TTS to create audio, then you can test STT")
        print("=" * 60)
        
        if "--generate" in sys.argv:
            create_test_audio()
    
    sys.exit(0 if success else 1)
