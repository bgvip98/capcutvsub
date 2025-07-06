from flask import Flask, request, render_template, send_file
import json
import re
from io import BytesIO
from deep_translator import GoogleTranslator

app = Flask(__name__)

def seconds_to_srt_time(microsec):
    seconds = microsec / 1e6
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def extract_text_from_html(html):
    # Lấy nội dung trong dấu [ ]
    match = re.search(r'\[([^\[\]]+)\]', html)
    return match.group(1).strip() if match else ""

def convert_json_to_srt(data, translate=True):
    text_map = {}
    for t in data.get("materials", {}).get("texts", []):
        text_map[t["id"]] = extract_text_from_html(t.get("content", ""))

    srt_entries = []
    for track in data.get("tracks", []):
        if track.get("type") != "text":
            continue
        for seg in track.get("segments", []):
            material_id = seg.get("material_id")
            if not material_id or material_id not in text_map:
                continue

            text = text_map[material_id]
            if not text:
                continue

            start = seg["target_timerange"]["start"]
            duration = seg["target_timerange"]["duration"]
            end = start + duration

            if translate:
                try:
                    text = GoogleTranslator(source='auto', target='vi').translate(text)
                except Exception as e:
                    print("❌ Lỗi dịch:", e)

            srt_entries.append({
                "start": seconds_to_srt_time(start),
                "end": seconds_to_srt_time(end),
                "text": text
            })

    srt_entries.sort(key=lambda x: x["start"])

    srt = ""
    for i, entry in enumerate(srt_entries, start=1):
        srt += f"{i}\n{entry['start']} --> {entry['end']}\n{entry['text']}\n\n"
    return srt

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('jsonfile')
        if file:
            try:
                data = json.load(file)
                srt_content = convert_json_to_srt(data, translate=True)
                if not srt_content.strip():
                    return "⚠️ Không có phụ đề hợp lệ trong file.", 400
                return send_file(BytesIO(srt_content.encode('utf-8')),
                                 download_name="subtitles_vi.srt",
                                 as_attachment=True,
                                 mimetype="text/srt")
            except Exception as e:
                return f"❌ Lỗi xử lý JSON: {str(e)}", 500
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000)
