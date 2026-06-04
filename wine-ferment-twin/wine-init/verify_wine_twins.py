#!/usr/bin/env python3
import argparse
from urllib.parse import quote
import requests
IDS=['wine:winery_01','wine:workshop_01','wine:tank_01','wine:tank_02','wine:tank_03']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ditto-url',required=True); ap.add_argument('--username',default='ditto'); ap.add_argument('--password',default='ditto'); args=ap.parse_args()
    ok=True
    for thing_id in IDS:
        url=args.ditto_url.rstrip()+'/api/2/things/'+quote(thing_id,safe='')
        r=requests.get(url,auth=(args.username,args.password),timeout=8)
        if r.status_code==200:
            d=r.json(); attrs=d.get('attributes',{}); features=sorted((d.get('features') or {}).keys()); parents=attrs.get('_parents',[])
            print(f"FOUND {thing_id} type={attrs.get('type')} parents={parents} features={features}")
        else:
            ok=False; print(f"MISSING {thing_id}: {r.status_code} {r.text[:160]}")
    raise SystemExit(0 if ok else 1)
if __name__ == '__main__': main()
