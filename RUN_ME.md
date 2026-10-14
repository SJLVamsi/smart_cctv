# RUN_ME - Smart CCTV demo (Mac)

## Do this tonight/before class (needs internet once, ~5-15 min)
Open Terminal:
```sh
cd ~/Downloads/smart-cctv
bash setup_and_run.sh
```
That picks your Python, makes a venv, installs packages, runs the tests-free demo and opens both pages in your browser.
(If you prefer manual steps: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python run.py`)

If the zip unzipped to a different folder, `cd` to wherever `smart-cctv` is.

## Before class: run it ONCE fully
Do the full run tonight so all packages are installed. In class you only need:
```sh
cd ~/Downloads/smart-cctv && source .venv/bin/activate && python run.py
```
No internet needed in class. No camera needed (assets/sample.mp4 is the camera stand-in; YOLOv8n weights are included).

## What you should see
- Terminal prints `Dashboard: http://127.0.0.1:5050` and `Local video overlay: http://127.0.0.1:5051`
- 5051: video with person boxes, IDs, teal restricted zone
- 5050: alert dashboard. Alerts appear through the clip (28 s) — an early intrusion, loitering near 11 s and another intrusion near 18 s — each with a keyframe, plus FPS/latency/CPU/memory
- Replay: press the **Replay run** button on the edge monitor (5051) — no terminal needed, alerts reset at the start of each run. (Ctrl+C and `python run.py` also works.)

## If something goes wrong (fallbacks)
1. pip install fails / no wifi: open the screenshots in `evidence/` (dashboard-desktop.png, edge-monitor.png) and present from those. Say it was captured from this same code.
2. Slow or stuttering: close other apps; run `python run.py --fast` (no real-time pacing).
3. Port busy: `pkill -f run.py` then rerun.
4. Python 3.14 or odd version fails on torch: `brew install python@3.13` then `python3.13 -m venv .venv` (delete old `.venv`).
5. Try Apple GPU: `python run.py --device mps` (optional, CPU is the verified default).
6. Other video: `python run.py --video /path/to/clip.mp4`

## 60-second demo script
0:00 - Open http://127.0.0.1:5051 (edge overlay). "A video file stands in for an IP camera. The edge device, here my laptop, runs YOLOv8n on every frame, tracks people, and applies rules locally."
0:15 - Point at the teal zone. "If a person's center enters this restricted zone, that's an intrusion. If someone stays within a small radius for 4 seconds, that's loitering. Around 10-18 s the clip is deliberately frozen to stage a stationary person - it's labeled, not passed off as real."
0:30 - Switch to http://127.0.0.1:5050. "Only alerts go to the cloud dashboard: timestamp, type, reason, and one keyframe. Not the full video."
0:45 - Point to metrics. "FPS, latency, CPU and memory are measured live. Sending alerts instead of video saves most of the bandwidth - that's the edge benefit."
0:55 - "Limits: rules are heuristic, no fights/falls/bags, and both nodes run on one laptop. Next: real RTSP and a Jetson/Pi."
