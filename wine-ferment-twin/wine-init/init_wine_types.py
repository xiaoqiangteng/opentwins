#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from typing import Dict, Any
import requests

TYPES = [
    {"id":"wine:Winery","name":"Winery","description":"Wine production site root type","features":["status","risk_level"]},
    {"id":"wine:Workshop","name":"Workshop","description":"Fermentation workshop type","features":["status","tank_count","risk_level"]},
    {"id":"wine:FermentationTank","name":"FermentationTank","description":"Wine fermentation tank type","features":["temperature","ph","brix","specific_gravity","co2","pressure","liquid_level","alcohol_estimation","fermentation_progress","fermentation_stage","quality_score","risk_level","recommendation"]},
]

def try_post(base: str, payload: Dict[str, Any]) -> bool:
    paths = ["/api/types", "/api/v1/types", "/api/2/types", "/types"]
    for p in paths:
        try:
            r = requests.post(base.rstrip('/') + p, json=payload, timeout=5)
            if r.status_code in (200,201,204,409):
                print(f"type {payload['id']} accepted at {p}: {r.status_code}")
                return True
        except requests.RequestException:
            pass
    return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--extended-api', required=True)
    ap.add_argument('--ditto-url', required=True)
    ap.add_argument('--username', default='ditto')
    ap.add_argument('--password', default='ditto')
    args=ap.parse_args()
    ok=0
    for t in TYPES:
        if try_post(args.extended_api, t): ok+=1
        else: print(f"warning: Extended API type registration skipped for {t['id']} (endpoint not detected)")
    print(f"wine type initialization completed; accepted={ok}, total={len(TYPES)}")
if __name__ == '__main__': main()
