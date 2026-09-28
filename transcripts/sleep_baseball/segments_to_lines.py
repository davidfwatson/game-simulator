import json,sys
d=json.load(open(sys.argv[1]))
for i,s in enumerate(d['segments']):
    t=''.join(w['text'] for w in s['words']).strip()
    m=int(s['start']//60); sec=s['start']%60
    print(f"{i:04d} [{m:03d}:{sec:04.1f}] {t}")
