#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from urllib.parse import quote
import requests

POLICY = {
  "entries": {
    "DEFAULT": {
      "subjects": {"nginx:ditto": {"type": "nginx basic auth user"}, "ditto:ditto": {"type":"basic auth user"}},
      "resources": {"thing:/": {"grant": ["READ","WRITE"], "revoke": []}, "policy:/": {"grant": ["READ","WRITE"], "revoke": []}, "message:/": {"grant": ["READ","WRITE"], "revoke": []}}
    }
  }
}

def put_json(url, auth, payload):
    r=requests.put(url, auth=auth, json=payload, timeout=10)
    if r.status_code not in (200,201,204):
        raise RuntimeError(f"PUT {url} -> {r.status_code}: {r.text[:300]}")
    return r.status_code

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--schema', required=True)
    ap.add_argument('--ditto-url', required=True)
    ap.add_argument('--username', default='ditto')
    ap.add_argument('--password', default='ditto')
    args=ap.parse_args()
    data=json.loads(Path(args.schema).read_text(encoding='utf-8'))
    auth=(args.username,args.password)
    policy_id=data.get('policyId','opentwins:basic_policy')
    policy_url=args.ditto_url.rstrip() + '/api/2/policies/' + quote(policy_id, safe='')
    try:
        put_json(policy_url, auth, POLICY)
        print(f"policy upserted: {policy_id}")
    except Exception as e:
        print(f"warning: policy upsert skipped: {e}")
    for tw in data.get('twins',[]):
        thing_id=tw['thingId']
        payload={"policyId":tw.get('policyId',policy_id),"attributes":tw.get('attributes',{}),"features":tw.get('features',{})}
        url=args.ditto_url.rstrip() + '/api/2/things/' + quote(thing_id, safe='')
        code=put_json(url, auth, payload)
        print(f"{thing_id}: upserted ({code})")
if __name__ == '__main__': main()
