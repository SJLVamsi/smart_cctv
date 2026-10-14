"""Small greedy tracker and two explainable rules; times use source-video seconds."""
import math

class RuleEngine:
    def __init__(self, zone=(.42,.10,.92,.96), dwell=4.0, radius=24.0):
        self.zone, self.dwell, self.radius = zone, dwell, radius
        self.tracks = {}; self.next_id = 1

    def update(self, boxes, now, width, height):
        self.tracks = {k:v for k,v in self.tracks.items() if now-v['last'] < 1.0}
        free=set(self.tracks); results=[]; events=[]
        for box in boxes:
            x1,y1,x2,y2,confidence=box
            center=((x1+x2)/2,(y1+y2)/2)
            candidates=[(math.dist(center,self.tracks[k]['center']), k) for k in free]
            distance, ident=min(candidates,default=(float('inf'),None))
            if distance>85:
                ident=self.next_id; self.next_id+=1
                self.tracks[ident]={'center':center,'anchor':center,'since':now,'last':now,'inside':False,'loitered':False}
            else:free.remove(ident)
            t=self.tracks[ident]
            if math.dist(center,t['anchor'])>self.radius:
                t.update(anchor=center,since=now,loitered=False)
            a,b,c,d=self.zone
            inside=a*width <= center[0] <= c*width and b*height <= center[1] <= d*height
            if inside and not t['inside']:
                events.append({'type':'Intrusion','track_id':ident,'reason':'Person center entered the configured restricted zone'})
            if now-t['since']>=self.dwell and not t['loitered']:
                events.append({'type':'Loitering','track_id':ident,'reason':f'Person center remained within {self.radius:g}px for {self.dwell:g}s'})
                t['loitered']=True
            t.update(center=center,last=now,inside=inside)
            results.append({'id':ident,'box':box,'inside':inside,'loitering':t['loitered']})
        return results,events
