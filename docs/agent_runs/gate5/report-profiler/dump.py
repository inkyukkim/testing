import json
e=json.load(open('work/report_extract.json')); m=json.load(open('work/matches.json'))
B=e['blocks']
last=None
for i,(t,c) in enumerate(zip(e['tokens'],m)):
    assert t['token']==c['token'] and t['block']==c['block']
    if t['block']!=last:
        b=B[t['block']]
        print(f"\n### B{t['block']} [{b['kind']}] {b.get('section')} | {b.get('subsection')}\n  {b['text'][:600]}")
        last=t['block']
    cs=' ; '.join(f"{x['name']}@{x['context']}" for x in c['candidates'])
    print(f"  T{i} '{t['token']}' [{c['status']}] {cs}")
