#!/usr/bin/env python3
import os, json, subprocess, csv, time
from pathlib import Path

MODEL_ROOT = Path("/workspace/models")
OUTPUT_DIR = Path("/workspace/out")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCENES_FILE = Path("/workspace/scenes.json")
MAX_COST = 0.30

def run(cmd):
    print(f"▶ {cmd}")
    result = subprocess.run(cmd, shell=True, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return result.stdout.strip()

def tts(audio_path, text, speaker_wav):
    run(f'bark_tts "{text}" --voice "{speaker_wav}" --output "{audio_path}"')

def sd_generate(video_path, prompt, audio_path):
    run(f'python3 /app/open_sora_generate.py --prompt "{prompt}" '
        f'--audio "{audio_path}" --output "{video_path}" '
        f'--width 720 --height 1280 --model-dir "{MODEL_ROOT}"')

def upscale(input_mp4, output_mp4):
    run(f'real-esrgan -i "{input_mp4}" -o "{output_mp4}" -s 2')

def main():
    total_cost = 0.0
    with open(SCENES_FILE) as f:
        scenes = json.load(f)

    report = []
    for idx, scene in enumerate(scenes):
        prompt = scene["prompt"]
        voice_path = MODEL_ROOT / scene["voice_wav"]

        audio_path = OUTPUT_DIR / f"audio_{idx}.wav"
        tts(audio_path, prompt, voice_path)

        raw_video = OUTPUT_DIR / f"raw_{idx}.mp4"
        sd_generate(raw_video, prompt, audio_path)

        final_video = OUTPUT_DIR / f"out_{idx}.mp4"
        upscale(raw_video, final_video)

        log_path = raw_video.with_suffix(".json")
        cost = 0.0
        try:
            with open(log_path) as f:
                cost = json.load(f).get("cost_usd", 0.0)
        except Exception:
            pass
        total_cost += cost

        report.append({
            "idx": idx, "prompt": prompt,
            "final_video": str(final_video),
            "cost_usd": f"{cost:.5f}",
            "cum_cost_usd": f"{total_cost:.5f}"
        })
        print(f"✅ Clip {idx} fertig – Kosten bisher: ${total_cost:.5f}")

        if total_cost >= MAX_COST:
            print(f"⚠️ Kosten-Grenze ${MAX_COST:.2f} erreicht – Stopp.")
            break

    csv_path = OUTPUT_DIR / "run_report.csv"
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=report[0].keys())
        writer.writeheader()
        writer.writerows(report)

    print(f"\n🗂️ Report: {csv_path}")
    print("🎉 Fertige MP4s liegen in:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
