import json
from pathlib import Path
from app.config import settings
from app.rag import retrieve

def evaluate(k=None):
    path=Path(__file__).resolve().parents[1]/"data"/"evaluation"/"questions.json"
    cases=json.loads(path.read_text(encoding="utf-8"))
    k=k or settings.top_k
    recalls=[];rr=[]
    for case in cases:
        hits=retrieve(case["question"],k)
        expected=[x.lower() for x in case["expected_terms"]]
        relevant=[any(term in (h["title"]+" "+h["text"]).lower() for term in expected) for h in hits]
        recalls.append(float(any(relevant)))
        rr.append(1/(relevant.index(True)+1) if any(relevant) else 0.0)
    n=max(len(cases),1)
    return {"questions":len(cases),"top_k":k,"recall_at_k":round(sum(recalls)/n,4),"mrr":round(sum(rr)/n,4)}
if __name__=="__main__":
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
