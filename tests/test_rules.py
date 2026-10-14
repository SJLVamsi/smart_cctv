import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rules import RuleEngine
from dashboard import create_app
import tempfile,base64

class RulesTests(unittest.TestCase):
    def test_intrusion_and_no_repeat(self):
        r=RuleEngine()
        _,e=r.update([[50,20,70,80,.9]],0,100,100)
        self.assertEqual(e[0]['type'],'Intrusion')
        self.assertEqual(r.update([[50,20,70,80,.9]],.2,100,100)[1],[])
    def test_loitering(self):
        r=RuleEngine()
        events=[]
        for i in range(51):events+=r.update([[50,20,70,80,.9]],i/10,100,100)[1]
        self.assertEqual(sum(e['type']=='Loitering' for e in events),1)
    def test_moving_person_not_loitering(self):
        r=RuleEngine(radius=3)
        events=[]
        for i in range(80):events+=r.update([[i,20,i+10,80,.9]],i/10,200,100)[1]
        self.assertFalse(any(e['type']=='Loitering' for e in events))
    def test_stale_track_expires(self):
        r=RuleEngine();a,_=r.update([[50,20,70,80,.9]],0,100,100)
        b,_=r.update([[50,20,70,80,.9]],2,100,100)
        self.assertNotEqual(a[0]['id'],b[0]['id'])
    def test_cloud_receives_alert_not_full_video(self):
        with tempfile.TemporaryDirectory() as t:
            c=create_app(t).test_client()
            data={'type':'Intrusion','track_id':1,'reason':'test','keyframe_b64':base64.b64encode(b'test-jpeg').decode()}
            self.assertEqual(c.post('/api/alerts',json=data).status_code,201)
            s=c.get('/api/state').json
            self.assertNotIn('keyframe_b64',s['alerts'][0])
            response=c.get(s['alerts'][0]['image'])
            self.assertEqual(response.data,b'test-jpeg')
            response.close()
            self.assertEqual(c.get('/frame.jpg').status_code,404)

class CloudResetTests(unittest.TestCase):
    def test_reset_clears_alerts(self):
        with tempfile.TemporaryDirectory() as t:
            client = create_app(t).test_client()
            client.post('/api/alerts', json={'type': 'Intrusion', 'track_id': 1, 'reason': 'x',
                                             'keyframe_b64': base64.b64encode(b'jpeg').decode()})
            self.assertEqual(len(client.get('/api/state').json['alerts']), 1)
            self.assertEqual(client.post('/api/reset').status_code, 200)
            self.assertEqual(client.get('/api/state').json['alerts'], [])


if __name__=='__main__':unittest.main()
