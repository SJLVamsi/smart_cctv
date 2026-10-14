import base64, collections, datetime, json, threading, time
from pathlib import Path
import cv2, psutil, requests, torch
from flask import Flask, Response, render_template
from ultralytics import YOLO
from rules import RuleEngine

ROOT=Path(__file__).resolve().parent

def mjpeg_stream(fetch_frame,stop,interval=0.08):
    """Yield the latest JPEG as multipart/x-mixed-replace so the browser shows smooth motion."""
    while not stop.is_set():
        frame=fetch_frame()
        if frame:
            yield (b'--edgeframe\r\nContent-Type: image/jpeg\r\nContent-Length: '
                   +str(len(frame)).encode()+b'\r\n\r\n'+frame+b'\r\n')
        time.sleep(interval)

class EdgeNode:
    def __init__(self,video,cloud,pace=True,device='cpu'):
        self.video=Path(video);self.cloud=cloud;self.pace=pace;self.device=device
        self.latest=None;self.done=False;self.error=None;self.sent=0;self.post_failures=0
        self.stats={};self.alert_count=0
        self.session=requests.Session();self.stop=threading.Event();self.replay=threading.Event()
        self.app=Flask('edge');self.proc=psutil.Process();self.proc.cpu_percent()
        @self.app.get('/')
        def home():return render_template('edge.html')
        @self.app.get('/frame.jpg')
        def frame():return Response(self.latest or b'',mimetype='image/jpeg',headers={'Cache-Control':'no-store'})
        @self.app.get('/stream.mjpg')
        def stream():return Response(mjpeg_stream(lambda:self.latest,self.stop),mimetype='multipart/x-mixed-replace; boundary=edgeframe')
        @self.app.get('/api/health')
        def health():return {'done':self.done,'error':self.error,'post_failures':self.post_failures,'stats':self.stats}
        @self.app.post('/api/replay')
        def replay():
            if not self.request_replay():return {'started':False,'reason':'Processing is still running'},409
            return {'started':True},202
    def post(self,path,data):
        raw=json.dumps(data,separators=(',',':')).encode()
        try:
            response=self.session.post(self.cloud+path,data=raw,headers={'Content-Type':'application/json'},timeout=5)
            response.raise_for_status()
        except requests.RequestException:
            # A dropped cloud link must never stop the edge processor mid-demo.
            self.post_failures+=1
            return False
        self.sent+=len(raw)
        return True
    def request_replay(self):
        """Queue another pass; only valid once the current pass has finished."""
        if not self.done:return False
        self.replay.set();return True
    def run(self):
        try:
            torch.set_num_threads(2)
            model=YOLO(str(ROOT/'assets/yolov8n.pt'))
            while not self.stop.is_set():
                self.done=False
                self._process(model)
                if self.stop.is_set():break
                self.done=True
                # Stay alive so the operator can replay without touching the terminal.
                while not self.stop.is_set() and not self.replay.is_set():time.sleep(0.2)
                self.replay.clear()
            self.done=True
        except Exception as exc:
            self.error=str(exc);self.done=True;print('EDGE ERROR:',exc,flush=True)
    def _process(self,model):
        cap=cv2.VideoCapture(str(self.video))
        try:
            if not cap.isOpened():raise RuntimeError('Cannot open video: '+str(self.video))
            source_fps=cap.get(cv2.CAP_PROP_FPS) or 10
            total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));duration=total/source_fps
            rules=RuleEngine(); ring=collections.deque(maxlen=max(1,int(source_fps*3)))
            local=ROOT/'output/edge';local.mkdir(parents=True,exist_ok=True)
            # Each pass starts from a clean slate, so a replay reads the same as a fresh run.
            count=0;latencies=[];start=time.perf_counter();last_metrics=0;last_alert={};last_type={}
            self.sent=0;self.post_failures=0;self.alert_count=0;self.stats={}
            self.post('/api/reset',{'reason':'pass start'})
            def metrics(status):
                elapsed=time.perf_counter()-start
                video_seconds=count/source_fps
                baseline=self.video.stat().st_size*min(video_seconds/duration,1)
                data={'status':status,'frames':count,'video_seconds':round(video_seconds,1),'fps':round(count/max(elapsed,.001),2),'latency_ms':round(sum(latencies)/max(len(latencies),1)*1000,2),'upload_kb':round(self.sent/1024,2),'baseline_kb':round(baseline/1024,2),'saved_percent':round((1-self.sent/max(baseline,1))*100,2),'cpu_percent':self.proc.cpu_percent(),'rss_mb':round(self.proc.memory_info().rss/1024**2,2),'device':self.device}
                # Include this telemetry body's bytes in its own reported counter.
                for _ in range(3):
                    predicted=self.sent+len(json.dumps(data,separators=(',',':')).encode())
                    data['upload_kb']=round(predicted/1024,2);data['saved_percent']=round((1-predicted/max(baseline,1))*100,2)
                self.post('/api/metrics',data)
                (local/'metrics.json').write_text(json.dumps(data,indent=2))
            while not self.stop.is_set():
                ok,image=cap.read()
                if not ok:break
                count+=1;now=count/source_fps;t0=time.perf_counter()
                pred=model.predict(image,imgsz=416,classes=[0],conf=.35,device=self.device,verbose=False)[0]
                boxes=[[float(v) for v in b] for b in pred.boxes.data.cpu().tolist()]
                boxes=[b[:5] for b in boxes]
                h,w=image.shape[:2]; tracks,events=rules.update(boxes,now,w,h)
                latencies.append(time.perf_counter()-t0)
                self.stats={'frames':count,'video_seconds':round(now,1),'fps':round(count/max(time.perf_counter()-start,.001),1),'latency_ms':round(latencies[-1]*1000,1),'alerts':self.alert_count}
                a,b,c,d=rules.zone;cv2.rectangle(image,(int(a*w),int(b*h)),(int(c*w),int(d*h)),(170,205,100),2)
                for tr in tracks:
                    x1,y1,x2,y2,conf=tr['box'];color=(0,150,255) if tr['loitering'] else ((50,50,240) if tr['inside'] else (100,220,100))
                    cv2.rectangle(image,(int(x1),int(y1)),(int(x2),int(y2)),color,2)
                    label=f"ID {tr['id']} {conf:.2f}"+(' LOITER' if tr['loitering'] else '')
                    cv2.putText(image,label,(int(x1),max(18,int(y1)-6)),0,.5,color,2)
                recent=[k[0] for k,v in last_alert.items() if now-v<2]
                cv2.rectangle(image,(0,h-50),(w,h),(25,25,25),-1)
                cv2.putText(image,f'EDGE | frame {count} | video {now:.1f}s | {latencies[-1]*1000:.0f}ms',(10,h-29),0,.55,(255,255,255),1)
                cv2.putText(image,'Alerts: '+(', '.join(e['type'] for e in events) or ', '.join(set(recent)) or 'none'),(10,h-9),0,.5,(100,200,255),1)
                ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,70])
                self.latest=jpeg.tobytes();ring.append(self.latest)
                for event in events:
                    key=(event['type'],event['track_id'])
                    if now-last_alert.get(key,-100)<10 or now-last_type.get(event['type'],-100)<5:continue
                    last_alert[key]=now;last_type[event['type']]=now;self.alert_count+=1
                    event.update(video_seconds=round(now,1),wall_time=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),keyframe_b64=base64.b64encode(self.latest).decode())
                    self.post('/api/alerts',event)
                    # Three-second ring buffer is persisted only on edge; no clip upload.
                    with open(local/f"buffer-{count}-{event['type']}.mjpeg",'wb') as f:
                        for frame in ring:f.write(frame)
                if time.perf_counter()-last_metrics>=1:
                    metrics('Processing');last_metrics=time.perf_counter()
                if self.pace:self.stop.wait(max(0,start+now-time.perf_counter()))
            metrics('Complete - press Replay, or restart the demo')
        finally:
            cap.release()
