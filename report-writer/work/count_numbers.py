import json, collections
m=json.load(open("work/report_KR.provenance.json"))
n=m["numbers"]
print("numbers in provenance:", len(n))
print("distinct source names:", len({x["source"]["name"] for x in n}))
print("scenario-sourced:", sum(1 for x in n if x["source"]["scenario"]))
print("rounding_footnote:", m["rounding_footnote"], "draft:", m["draft"])
c=collections.Counter((u.get("claim"),u["directive"]) for u in m["claims_used"])
for k,v in sorted(c.items(), key=str): print(k, v)
