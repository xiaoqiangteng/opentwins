from urllib.parse import quote
import requests
class DittoClient:
    def __init__(self, base_url, username='ditto', password='ditto'):
        self.base=base_url.rstrip('/'); self.auth=(username,password)
    def get_thing(self, thing_id):
        r=requests.get(self.base+'/api/2/things/'+quote(thing_id,safe=''),auth=self.auth,timeout=6)
        if r.status_code==404: return None
        r.raise_for_status(); return r.json()
    def list_things(self, ids):
        out=[]
        for i in ids:
            try:
                d=self.get_thing(i)
                if d: out.append(d)
            except Exception as e: print('ditto read failed',i,e)
        return out
