import whisper
import json
import argparse
import os

def transcribe_and_save(video_path):
    print("Transcribiendo...")
    model = whisper.load_model("small")
    result = model.transcribe(video_path, word_timestamps=True)
    
    with open("full_transcription.json", "w", encoding="utf-8") as f:
        json.dump(result["segments"], f, indent=4, ensure_ascii=False)
    print("Transcipción finalizada y guardada en full_transcription.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    args = parser.parse_args()
    transcribe_and_save(args.input)
