# Smart CCTV with anomaly detection using edge computing

TEAM14 demo: IP-camera file substitute -> laptop edge node -> alert-only cloud-dashboard substitute.

**Honest scope:** intrusion and loitering are explainable heuristic demonstrations, not validated anomaly recognition. Fights, falls, abandoned bags and live RTSP are not implemented. Both nodes run on your laptop; no actual cloud deployment is claimed.

## Fast setup on your Mac

Internet is needed once to install Python packages. The sample video and YOLOv8n weights are already included. Setup targets Python 3.13, Apple Silicon, macOS 13 or newer. About 5-15 minutes on a typical connection, but download speed can change this. No paid service, account, camera, training or GPU is needed.

1. Download `smart-cctv-demo.zip` from Drive into Downloads. Double-click to unzip. You should get `smart-cctv` in Downloads.
2. Open Terminal. Run these lines **one at a time**:

```sh
cd ~/Downloads/smart-cctv
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py
```

3. Leave that Terminal open. Open these two addresses in your browser:

- Dashboard: `http://127.0.0.1:5050`
- Local edge video overlay: `http://127.0.0.1:5051`

The first inference can take a few seconds. The clip lasts 28 seconds. When it completes, the dashboard and final frame stay open. To run it again, press **Replay run** on the edge monitor (port 5051) — no terminal needed. Alerts reset at the start of every run. You can still press Control+C and run `python run.py` again.

If your existing venv already uses Python 3.13, you can install the requirements there instead. For a fresh session tomorrow:

```sh
cd ~/Downloads/smart-cctv
source .venv/bin/activate
python run.py
```

## What to show faculty in 2 minutes

- Open the local edge monitor. Point to YOLO bounding boxes, person IDs and the teal restricted zone.
- Explain that a person center entering the zone creates an intrusion event.
- At 10-18 seconds, the sample is frozen and clearly labeled. This deliberately stages a stationary person so the loitering rule can be shown repeatably, not passed off as a real event.
- Open the dashboard. Show the alert timestamps, types, reasons and uploaded keyframes.
- Explain that the full video is visible only at edge port 5051. Port 5050 has alert keyframes and metrics only.
- Show FPS, latency, bandwidth estimate, CPU and memory. Explain limitations below.
- If someone asks to see it again, press **Replay run** on the edge monitor and the clip restarts from the first frame.

## Architecture that actually runs

```text
assets/sample.mp4 (file stands in for IP camera / RTSP)
    |
    v
EdgeNode on laptop CPU
  OpenCV decoding -> YOLOv8n person boxes -> greedy center tracking
  -> intrusion/loitering rules -> cooldown filter
  -> annotated local view at 127.0.0.1:5051 (smooth MJPEG stream + live stats)
  -> 3-second JPEG ring buffer saved locally when an alert fires
    |
    | HTTP POST: alert metadata + one JPEG keyframe
    | HTTP POST: metric JSON about once per second
    v
Flask dashboard (cloud substitute) at 127.0.0.1:5050
  persisted keyframes + alerts.json -> browser alert feed
```

`run.py` starts both independent HTTP servers and the processor. The edge monitor serves the live view as a multipart JPEG stream at `/stream.mjpg` (a rolling sequence of annotated frames, not a video file). The dashboard has no full-frame/video route. Local UI viewing traffic is separate from the measured edge-to-dashboard channel. Short clips are not uploaded in this prototype. `.mjpeg` files in the local output folder are concatenated JPEG ring-buffer snapshots, not MP4 files. If the dashboard link drops mid-run, the edge node keeps processing, lists the missed uploads on the edge monitor, and continues; alerts in that window are not stored.

## Detection rules

- YOLOv8n COCO-pretrained person class only; confidence >= .35, inference size 416, default CPU.
- Tracker: one-to-one nearest-center assignment, max distance 85 pixels. Tracks expire after 1 video second without detection. IDs may switch during occlusion; this is not a production tracker.
- Intrusion: bounding-box center enters the configured normalized rectangle `(0.42, 0.10, 0.92, 0.96)`.
- Loitering: center stays within 24 pixels of an anchor for 4 source-video seconds. Moving outside the radius resets the anchor and timer.
- Alert filter: at least 5 video seconds between alerts of the same type, and 10 seconds between alerts for the same track/type. This cuts repeated uploads but may suppress distinct events in a busy scene.

Edit the defaults in `rules.py` to change thresholds. Pixel thresholds suit the supplied 768x576 clip and must be recalibrated for other cameras.

## Metrics and honesty

- Processing FPS = processed frames / wall-clock run time. Default pacing caps playback at the source's 10 FPS. `--fast` removes that cap for a benchmark.
- Mean latency = average time for detection + tracking + rules per frame. It excludes encoding, network upload, dashboard refresh and model loading, so it is **not end-to-end alert latency**.
- Bandwidth baseline = encoded sample file bytes * fraction of video processed. Actual transmitted volume counts JSON request bodies, including base64 JPEGs and telemetry. Saving = `100 * (1 - transmitted / baseline)`. This is an estimate, not packet-level bandwidth or a measured live RTSP bitrate. It may be negative early or with many alerts. HTTP/TCP overhead, browser viewing and responses are excluded.
- CPU = edge process CPU usage on a one-core basis; above 100% means multiple cores are used. Memory = edge process RSS, not combined edge+dashboard/system memory.
- No labeled anomaly dataset was used and no accuracy, precision, recall or safety guarantee is claimed.

A tested Linux CPU paced run on Python 3.13.16 processed 280 frames in 28 seconds, emitted 6 alerts (4 intrusion, 2 loitering), showed 10.0 FPS, 55.18 ms mean detection/rule latency, 390.88 MiB edge RSS and 48.4% final-interval CPU. Sent payload was 487.49 KiB vs a 3490.22 KiB encoded-file baseline (86.03% estimated reduction). Your Mac's results will differ. Top-level macOS arm64 wheels were verified, but native macOS execution was not available for testing.

## Useful commands

Faster unpaced run (replay stops processing but dashboard stays open):

```sh
python run.py --fast
```

One-shot benchmark that exits when complete:

```sh
python run.py --fast --exit-when-done
```

Own local video file:

```sh
python run.py --video /full/path/to/video.mp4
```

Optional Apple GPU path (CPU is tested; MPS path was not tested):

```sh
python run.py --device mps
```

## Troubleshooting

- `python3.13: command not found`: check `python3 --version`. If it is 3.13, use `python3` for the venv command. Otherwise install Python 3.13 from python.org before setup.
- `Port 5050 is already in use`: the launcher prints this and stops instead of crashing with a traceback. Stop the other run (`pkill -f run.py`) and start again. Ports 5050/5051 must be free.
- No frame yet: wait for model startup. Read the Terminal error if one appears. Do not rename or remove the `assets` folder.
- Browser says connection refused: the Terminal must still be running `python run.py`. Use http, not https.
- Installation fails on old macOS: pinned OpenCV's arm64 wheel requires macOS 13+. Update macOS or use another supported machine; do not randomly mix dependency versions before your presentation.
- Stop safely with Control+C. Restart to replay. To remove generated output after stopping: `rm -rf output` (only removes demo-generated files).

## Files

- `run.py`: launcher, `edge.py`: video/detection/local monitor, `rules.py`: tracker and rules.
- `dashboard.py` + `templates/dashboard.html`: cloud substitute and UI; `templates/edge.html`: local edge monitor page.
- `assets/sample.mp4`: bundled 28-second modified OpenCV surveillance clip.
- `assets/yolov8n.pt`: bundled model weights (~6.3 MiB).
- `tests/`: unittest suite covering the rules, the dashboard API, the edge reliability and replay endpoints, and the launcher's port check.
- `evidence/`: actual screenshots and test results from Linux/Python 3.13.
- `output/`: generated at runtime; not sent in the ZIP.

## Sources and licenses

- YOLOv8 documentation: https://docs.ultralytics.com/models/yolov8/
- Ultralytics setup: https://docs.ultralytics.com/quickstart/
- Model download used: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
- OpenCV original sample: https://github.com/opencv/opencv/blob/master/samples/data/vtest.avi
- Clip source bytes: https://raw.githubusercontent.com/opencv/opencv/master/samples/data/vtest.avi

The bundled sample is a modified excerpt: 100 original frames, then an 8-second labeled freeze of the last frame, then 100 more original frames. The clip is for an academic demonstration; it is not your recorded CCTV data. OpenCV's Apache 2.0 notice is in `assets/OPENCV-LICENSE.txt`; sample footage's separate provenance/redistribution terms are not documented here, so do not treat it as cleared for commercial/public reuse. Ultralytics code/model are AGPL-3.0 (or separate enterprise license); the project source is supplied under AGPL-3.0 with the full text in `LICENSE`.
