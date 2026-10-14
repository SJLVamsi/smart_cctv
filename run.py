"""One command starts two loopback HTTP services and the video processor."""
import argparse, threading, time, sys, socket
from pathlib import Path
from werkzeug.serving import make_server
from dashboard import create_app
from edge import EdgeNode

ROOT=Path(__file__).resolve().parent

def port_is_free(port):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:
            probe.bind(('127.0.0.1',port))
        except OSError:
            return False
    return True

def bind(app,port):
    if port and not port_is_free(port):
        raise SystemExit(f'Port {port} is already in use. Stop the other demo (Control+C, or `pkill -f run.py`) and run python run.py again.')
    return make_server('127.0.0.1',port,app,threaded=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--video',default=str(ROOT/'assets/sample.mp4'));p.add_argument('--fast',action='store_true');p.add_argument('--exit-when-done',action='store_true');p.add_argument('--device',default='cpu',choices=['cpu','mps']);a=p.parse_args()
    cloud=create_app();edge=EdgeNode(a.video,'http://127.0.0.1:5050',not a.fast,a.device)
    servers=[]
    try:
        for app,port in [(cloud,5050),(edge.app,5051)]:
            s=bind(app,port);servers.append(s)
            threading.Thread(target=s.serve_forever,daemon=True).start()
        print('Dashboard: http://127.0.0.1:5050',flush=True)
        print('Local video overlay: http://127.0.0.1:5051',flush=True)
        t=threading.Thread(target=edge.run,daemon=True);t.start()
        while t.is_alive():
            time.sleep(.2)
            if edge.error:raise RuntimeError(edge.error)
            if a.exit_when_done and edge.done:break
        if edge.error:raise RuntimeError(edge.error)
    except KeyboardInterrupt:pass
    finally:
        edge.stop.set()
        for s in servers:s.shutdown()
    return 1 if edge.error else 0

if __name__=='__main__':sys.exit(main())
