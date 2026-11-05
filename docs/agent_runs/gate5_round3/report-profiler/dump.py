import json
ex=json.load(open('work/report_extract.json'));m=json.load(open('work/matches.json'))
B={b['index']:b for b in ex['blocks']}
cells={}
for b in ex['blocks']:
    if b['kind']=='table_cell': cells[(b['table'],b['row'],b['col'])]=b['text']
for i,(t,mm) in enumerate(zip(ex['tokens'],m)):
    assert t['token']==mm['token'] and t['block']==mm['block']
    b=B[t['block']]
    if b['kind']=='table_cell':
        ctx=f"T{b['table']} r{b['row']}c{b['col']} row='{cells.get((b['table'],b['row'],0))}' col='{cells.get((b['table'],0,b['col']))}'"
    else:
        s=b['text'];ctx=s[max(0,t['start']-90):t['end']+40].replace('\n',' ')
    c=' | '.join(f"{x['name']}@{x['context']}" for x in mm['candidates'])
    print(f"#{i} b{t['block']} [{t['token']}] {mm['status']} :: {ctx}\n     -> {c}")
