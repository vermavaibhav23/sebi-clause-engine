"""Experimental query-scoped uncertainty gate; not a legal completeness proof."""
import re


def dependency_closure(selected, states):
    by_id={s["logical_id"]:s for s in states}
    by_label={}
    for s in states:
        by_label.setdefault((s["document_id"],s["label"]),[]).append(s["logical_id"])
    pending=[s["logical_id"] for s in selected]
    visited=set(); issues=[]
    while pending:
        key=pending.pop()
        if key in visited:
            continue
        visited.add(key)
        s=by_id[key]
        if s["status"]!="active":
            issues.append({"reason":"uncertain_selected_or_dependent_clause","target_clause_id":key})
        # Narrow explicit same-document references. Ranges remain unresolved.
        refs=re.findall(r"\b(?:para(?:graph)?s?|clauses?)\s+(\d+(?:\.\d+)*(?:\s*(?:/|,|and|to|-)\s*\d+(?:\.\d+)*)*)",s["text"],re.I)
        for ref in refs:
            if re.search(r"\bto\b|-",ref):
                issues.append({"reason":"unresolved_reference_range","target_clause_id":key})
                continue
            for label in re.findall(r"\d+(?:\.\d+)*",ref):
                matches=by_label.get((s["document_id"],label),[])
                if len(matches)!=1:
                    issues.append({"reason":"ambiguous_or_missing_clause_reference","target_clause_id":key,"label":label})
                elif matches[0] not in visited:
                    pending.append(matches[0])
    return visited,issues


def select_with_gate(result, query, ranker, events):
    states=result["clauses"]
    state_ids={s["logical_id"] for s in states}
    # Cannot localize an unknown target, document-wide effect, or missing base.
    global_issues=[i for i in result["issues"] if not i.get("target_clause_id")
                   or i["target_clause_id"] not in state_ids]
    if global_issues:
        return [],global_issues,[]
    candidates=[dict(s) for s in states if s["status"] in {"active","unresolved"}]
    # Include proposed wording in ranking uncertain targets to avoid hiding a relevant edit.
    for s in candidates:
        if s["status"]=="unresolved":
            extras=[e.new_text for e in events if e.target_clause_id==s["logical_id"]
                    and e.status!="rejected" and e.new_text]
            s["text"]+="\n"+"\n".join(extras)
    selected=ranker(query.question,candidates,query.top_k)
    closure,issues=dependency_closure(selected,states)
    issues.extend(i for i in result["issues"] if i.get("target_clause_id") in closure)
    ignored=[i for i in result["issues"] if i.get("target_clause_id") not in closure]
    return ([] if issues else selected),issues,ignored
