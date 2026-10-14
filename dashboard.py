"""Cloud-side simulation. No full frames or video endpoint exists here."""
import base64, json, threading, time
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory, request

ROOT=Path(__file__).resolve().parent

def create_app(output=None):
    app=Flask(__name__); app.config['MAX_CONTENT_LENGTH']=3*1024*1024
    storage=Path(output or ROOT/'output/cloud'); storage.mkdir(parents=True,exist_ok=True)
    lock=threading.Lock(); alerts=[]; metrics={'status':'Waiting for edge node'}
    @app.get('/')
    def home():return render_template('dashboard.html')
    @app.get('/api/state')
    def state():
        with lock:return jsonify(alerts=list(reversed(alerts)),metrics=metrics.copy())
    @app.post('/api/alerts')
    def alert():
        data=request.get_json(); raw=base64.b64decode(data.pop('keyframe_b64'))
        ident=f'{time.time_ns()}'
        (storage/f'{ident}.jpg').write_bytes(raw)
        data.update(id=ident,image=f'/keyframes/{ident}.jpg')
        with lock:
            alerts.append(data)
            (storage/'alerts.json').write_text(json.dumps(alerts,indent=2))
        return jsonify(ok=True),201
    @app.post('/api/metrics')
    def update():
        with lock:metrics.update(request.get_json())
        return jsonify(ok=True)
    @app.post('/api/reset')
    def reset():
        # A replayed demo starts from a clean alert feed, matching a restart.
        with lock:
            alerts.clear()
            (storage/'alerts.json').write_text('[]')
        return jsonify(ok=True)
    @app.get('/keyframes/<name>')
    def image(name):return send_from_directory(storage,name)
    return app
