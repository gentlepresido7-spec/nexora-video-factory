import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, render_template_string, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-production")
BASE = Path("/tmp/nexora-video-factory")
BASE.mkdir(parents=True, exist_ok=True)
ALLOWED = {".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png"}

PAGE = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXORA Video Factory</title><style>
:root{color-scheme:dark;--gold:#d6ad55;--bg:#090909;--panel:#151515;--muted:#aaa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f4f0e7;font:15px/1.55 Arial,sans-serif}
main{max-width:900px;margin:36px auto;padding:0 18px}.brand{color:var(--gold);letter-spacing:.2em;font-weight:700}
h1{font-size:clamp(28px,5vw,44px);margin:8px 0}h2{color:var(--gold);font-size:18px}
p,.muted{color:var(--muted)}.panel{background:var(--panel);border:1px solid #34302a;border-radius:14px;padding:22px;margin:18px 0}
label{display:block;margin:12px 0 6px;color:#e7d5ad}input,textarea{width:100%;background:#090909;color:#fff;border:1px solid #494239;border-radius:8px;padding:12px}
textarea{min-height:90px}button{background:var(--gold);color:#111;border:0;border-radius:8px;padding:12px 18px;font-weight:700;cursor:pointer;margin-top:14px}
button.secondary{background:#29251e;color:#f3d99e;border:1px solid #6a5734}.notice{padding:12px;border-left:3px solid var(--gold);background:#211d15;color:#e9d9b8}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.scene{background:#0e0e0e;border:1px solid #38332a;padding:14px;border-radius:10px}
a{color:var(--gold)}small{color:var(--muted)}footer{padding:24px 0;color:#777}
</style></head><body><main>
<div class="brand">N E X O R A</div><h1>Video Factory</h1><p>Intelligence. Creativity. Possibility.</p>
<div class="notice">Approval-first workflow. Nothing is published automatically. This free-tier build creates a production brief and can assemble a vertical MP4 from your own clips or images.</div>
{% with messages=get_flashed_messages() %}{% if messages %}{% for m in messages %}<p class="notice">{{m}}</p>{% endfor %}{% endif %}{% endwith %}
<section class="panel"><h2>1 · Create a video brief</h2><form method="post" action="{{ url_for('brief') }}">
<label>Video topic / hook</label><input name="topic" required value="{{topic or 'Stop doing everything manually'}}">
<label>Product / call to action</label><input name="cta" value="NEXORA AI Productivity Starter Kit — ₦2,500">
<label>Product URL</label><input name="url" value="https://selar.com/f7d2824682">
<label>Key message</label><textarea name="message">Show how practical AI workflows can help people create content, organise tasks and work smarter.</textarea>
<button type="submit">Generate 3-scene production brief</button></form></section>
{% if brief %}<section class="panel"><h2>2 · Review your creative package</h2><p><b>Hook:</b> {{brief.hook}}</p><div class="grid">{% for s in brief.scenes %}<div class="scene"><b>Scene {{loop.index}} · {{s.duration}}s</b><p>{{s.visual}}</p><small>On-screen text: {{s.text}}</small></div>{% endfor %}</div>
<h2>Voiceover</h2><p>{{brief.voiceover}}</p><h2>Caption</h2><p>{{brief.caption}}</p><h2>Hashtags</h2><p>{{brief.hashtags}}</p>
<form method="post" action="/approve"><input type="hidden" name="brief" value="{{brief_json}}"><button class="secondary">Approve brief for video assembly</button></form></section>{% endif %}
{% if approved %}<section class="panel"><h2>3 · Assemble your vertical video</h2><p>Upload three scene clips or still images. Use footage you own or have permission to use. Images are animated with a simple pan/zoom; clips are trimmed to fit the scene durations.</p>
<form method="post" action="/render" enctype="multipart/form-data">
<input type="hidden" name="voiceover_text" value="{{brief.voiceover}}">
<div class="grid">{% for i in range(1,4) %}<div><label>Scene {{i}} media</label><input type="file" name="scene{{i}}" accept="video/mp4,video/quicktime,video/webm,image/png,image/jpeg" required></div>{% endfor %}</div>
<p class="muted">A Nigerian English AI voiceover and synchronized on-screen captions will be generated automatically.</p>
<label>Optional music bed (use only licensed audio)</label><input type="file" name="music" accept="audio/mpeg,audio/wav,audio/x-wav">
<button type="submit">Render 9:16 MP4</button></form></section>{% endif %}
<footer>NEXORA Video Factory · Drafts only · Review every export before publishing.</footer></main></body></html>
"""

def make_brief(topic, cta, url, message):
    hook = topic.strip()
    scenes = [
        {"duration": 8, "visual": "A busy person at a desk, multiple tasks competing for attention; cinematic realistic footage, vertical 9:16.", "text": "STILL DOING EVERYTHING MANUALLY?"},
        {"duration": 8, "visual": "Close-up of a laptop and a person planning content and organising work; natural light, realistic documentary look, vertical 9:16.", "text": "LET AI HELP YOU WORK SMARTER"},
        {"duration": 9, "visual": "Confident small-business owner reviewing a simple plan and smiling; warm premium lighting, vertical 9:16.", "text": "15 PRACTICAL AI WORKFLOWS · NEXORA"}
    ]
    # Keep URLs out of spoken narration; direct viewers to the caption/bio instead.
    clean_cta = re.sub(r"https?://\\S+", "", cta).strip(" .")
    voiceover = f"{hook}. {message.strip()} You do not need to be a technology expert to get started. {clean_cta}. Get started today using the link in the caption. NEXORA. Intelligence. Creativity. Possibility."
    caption = f"{hook}.\n\n{message.strip()}\n\n{cta}\nGet yours: {url}\n\nFollow NEXORA for practical AI tips."
    return {"hook": hook, "scenes": scenes, "voiceover": voiceover, "caption": caption,
            "hashtags": "#NEXORA #AIProductivity #LearnAI #DigitalSkills #WorkSmarter #AITipsForBeginners"}

@app.get("/")
def home():
    return render_template_string(PAGE, brief=None, approved=False, topic="")
@app.route("/brief", methods=["GET", "POST"])
def brief():
    # Accept GET as a safe fallback for browsers or stale pages that navigate
    # to this endpoint instead of submitting the form with POST.
    values = request.values
    b = make_brief(
        values.get("topic", "Stop doing everything manually"),
        values.get("cta", "NEXORA AI Productivity Starter Kit — ₦2,500"),
        values.get("url", "https://selar.com/f7d2824682"),
        values.get("message", "Show how practical AI workflows can help people create content, organise tasks and work smarter.")
    )
    return render_template_string(PAGE, brief=b, brief_json=json.dumps(b), approved=False, topic=b["hook"])
@app.post("/approve")
def approve():
    raw = request.form.get("brief","")
    try:
        b = json.loads(raw)
        if len(b.get("scenes", [])) != 3: raise ValueError()
    except Exception:
        flash("Brief could not be validated. Please create it again.")
        return redirect(url_for("home"))
    return render_template_string(PAGE, brief=b, brief_json=raw, approved=True, topic=b["hook"])

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
    if p.returncode:
        raise RuntimeError(p.stderr[-1800:])
    return p

@app.post("/render")
def render():
    if not shutil.which("ffmpeg"):
        flash("FFmpeg is not installed in this runtime. Please use the Docker deployment configuration.")
        return redirect(url_for("home"))
    work = Path(tempfile.mkdtemp(prefix="nexora-", dir=BASE))
    try:
        inputs = []
        for i in range(1,4):
            f = request.files.get(f"scene{i}")
            if not f or not f.filename: raise ValueError(f"Scene {i} media is required.")
            ext = Path(secure_filename(f.filename)).suffix.lower()
            if ext not in ALLOWED: raise ValueError("Unsupported media type.")
            dest = work / f"scene{i}{ext}"
            f.save(dest)
            inputs.append(dest)
        clips=[]
        for i,src in enumerate(inputs,1):
            out=work/f"part{i}.mp4"
            if src.suffix.lower() in {".jpg",".jpeg",".png"}:
                # A static image becomes a 9-second vertical motion clip.
                run(["ffmpeg","-y","-loop","1","-i",str(src),"-t","8","-vf",
                     "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0008,1.12)':d=200:s=1080x1920:fps=25,format=yuv420p",
                     "-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(out)])
            else:
                run(["ffmpeg","-y","-i",str(src),"-t","8","-vf",
                     "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=25,format=yuv420p",
                     "-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(out)])
            clips.append(out)
        listing=work/"list.txt"
        listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips),encoding="utf-8")
        joined=work/"joined.mp4"
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-c","copy",str(joined)])
        voice=request.files.get("voice")
        music=request.files.get("music")
        final=work/"NEXORA_vertical_draft.mp4"
        vp=None
        if voice and voice.filename:
            vp=work/("voice"+Path(secure_filename(voice.filename)).suffix.lower())
            voice.save(vp)
        else:
            voice_text=request.form.get("voiceover_text","").strip()
            if voice_text:
                vp=work/"generated_voiceover.mp3"
                # Voice and timed captions are generated together below.\n        if vp:
            # Ask Edge TTS for timed subtitle cues from the exact spoken script.
            vtt = work/"voiceover.vtt"
            if not (voice and voice.filename):
                voice_text = request.form.get("voiceover_text","").strip()
                run(["edge-tts","--voice","en-NG-EzinneNeural","--text",voice_text,
                     "--write-media",str(vp),"--write-subtitles",str(vtt)])
            else:
                # For user-supplied narration, derive approximate timed captions from its transcript.
                raise RuntimeError("For exact synchronized captions, use the automatically generated voiceover or provide a transcript-enabled audio workflow.")
            srt = work/"captions.srt"
            def vtt_to_srt(source, target):
                raw = source.read_text(encoding="utf-8")
                blocks = re.split(r"\\n\\s*\\n", raw.replace("\\r","").strip())
                cues=[]
                for block in blocks:
                    lines=block.splitlines()
                    time_index=next((i for i,line in enumerate(lines) if "-->" in line),None)
                    if time_index is None: continue
                    timing=lines[time_index].replace(".",",")
                    caption=" ".join(line.strip() for line in lines[time_index+1:] if line.strip())
                    if caption:
                        cues.append(f"{len(cues)+1}\\n{timing}\\n{caption}")
                if not cues: raise RuntimeError("Timed captions could not be generated by the voice service.")
                target.write_text("\\n\\n".join(cues)+"\\n",encoding="utf-8")
            vtt_to_srt(vtt,srt)
            subtitle_path=str(srt).replace("\\\\","/").replace(":","\\\\:")
            vf=f"tpad=stop_mode=clone:stop_duration=600,subtitles='{subtitle_path}':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=100'"
            cmd=["ffmpeg","-y","-i",str(joined),"-i",str(vp)]
            if music and music.filename:
                mp=work/("music"+Path(secure_filename(music.filename)).suffix.lower()); music.save(mp)
                cmd += ["-stream_loop","-1","-i",str(mp),"-filter_complex","[1:a]volume=1.0[v];[2:a]volume=0.12[m];[v][m]amix=inputs=2:duration=first[a]","-map","0:v","-map","[a]","-vf",vf,"-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(final)]
            else:
                cmd += ["-map","0:v","-map","1:a","-vf",vf,"-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(final)]
            run(cmd)
        else:
            raise RuntimeError("No voiceover text was supplied. Please regenerate the brief and try again.")
        return send_file(final, as_attachment=True, download_name="NEXORA_vertical_draft.mp4", mimetype="video/mp4")
    except Exception as e:
        flash(f"Render failed: {str(e)[:500]}")
        return redirect(url_for("home"))
    finally:
        shutil.rmtree(work, ignore_errors=True)

@app.get("/health")
def health():
    return {"status":"ok","service":"NEXORA Video Factory","ffmpeg":bool(shutil.which("ffmpeg"))}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
