"""The board as one standalone, interactive web page a client can open without signing in (idea from
Archify's "deliver", Roger, 18 Oct 2026). Built from the graph with no model call; one file, no scripts
from elsewhere. Every id (F1, FL1, S2, B3, A1) is an anchor, so "see S2" links to the screen."""

from html import escape as _e
from typing import Any, Dict

from src.core.brief import short_ids
from src.core.check import plan_check
from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus

_CSS = """
:root{--bg:#f7f7f5;--panel:#fff;--line:#e6e5e1;--strong:#cfcdc7;--text:#111110;--muted:#64635f;--accent:#f5b301;--soft:#fff6d6;--ok:#12805c;--bad:#c0301e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header b{font-size:16px}header nav{display:flex;gap:10px;flex-wrap:wrap;font-size:13px}header a{color:var(--muted);text-decoration:none}header a:hover{color:var(--text)}
#q{margin-left:auto;border:1px solid var(--strong);border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;min-width:180px}
main{max-width:1100px;margin:0 auto;padding:16px 20px 60px}h2{font-size:18px;margin:28px 0 10px}
.id{display:inline-block;font:600 11px ui-monospace,monospace;border:1px solid var(--strong);border-radius:5px;padding:1px 5px;margin-right:6px;color:var(--muted);background:var(--panel);text-decoration:none}
a.id:hover{border-color:var(--text);color:var(--text)}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0}
.row{display:flex;gap:10px;overflow-x:auto;padding:4px 0 8px}.step{flex:0 0 210px;background:var(--panel);border:1px solid var(--strong);border-radius:10px;padding:9px 11px;font-size:13px}
.step b{display:block;font-size:13.5px}.branch{margin-left:22px;border-left:2px dashed var(--strong);padding-left:12px}.muted{color:var(--muted)}
.tag{display:inline-block;font-size:11.5px;font-weight:600;border-radius:999px;padding:1px 8px;background:var(--soft)}.tag.bad{background:#fdebe8;color:var(--bad)}.tag.ok{background:#e4f4ed;color:var(--ok)}
ul{margin:6px 0;padding-left:20px}li{margin:3px 0}.check li.blocker{color:var(--bad)}.hide{display:none}
@media (max-width:640px){main{padding:12px 16px 40px}#q{min-width:0;width:100%}}
"""

_JS = """document.getElementById('q').addEventListener('input',e=>{const t=e.target.value.toLowerCase();
document.querySelectorAll('[data-s]').forEach(n=>n.classList.toggle('hide',!!t&&!n.textContent.toLowerCase().includes(t)))});"""


def build_share_html(g: BuildingBeesEngine) -> str:
    """Writes the board (features, flows with their splits, screens, decisions, open questions, the plan check)
    as one self-contained HTML page with anchors on every id and a filter box."""
    ids = short_ids(g)
    idlink = lambda i: f'<a class="id" href="#{ids[i]}">{ids[i]}</a>' if i in ids else ""  # noqa: E731
    anchor = lambda i: f' id="{ids[i]}"' if i in ids else ""  # noqa: E731
    title = getattr(g, "product_name", "") or "Product plan"
    qs = [n for n in g.nodes.values() if isinstance(n, QuestionNode)]
    decided = [q for q in qs if q.question_status == QuestionStatus.ANSWERED and not q.metadata.get("vague")]
    still = [q for q in qs if q.question_status == QuestionStatus.OPEN]
    check = plan_check(g)
    who = "you" if getattr(g, "mode", "solo") != "team" else "the team"  # a solo founder's answers are theirs
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{_e(title)}: product plan</title><style>{_CSS}</style></head><body>"
           f"<header><b>{_e(title)}</b><nav><a href='#check'>Plan check</a><a href='#features'>Features</a><a href='#flows'>Flows</a>"
           f"<a href='#screens'>Screens</a><a href='#decisions'>Decisions</a><a href='#open'>Still open</a></nav>"
           f"<input id='q' placeholder='Filter: a word or an id like S2' aria-label='Filter the plan'></header><main>"]
    add = out.append
    add(f"<p class='muted'>Planned with BuildingBees: the bees asked, the team decided. Anything marked not decided must be asked, not assumed. Round {getattr(g, 'round', 1)}.</p>")

    add("<h2 id='check'>Plan check</h2>")
    add(f"<p><span class='tag {'ok' if check['passed'] else 'bad'}'>{'Ready for a builder' if check['passed'] else 'Not ready yet'}</span> "
        f"{len(check['issues'])} thing{'s' if len(check['issues']) != 1 else ''} to settle.</p>")
    if check["issues"]:
        rows = []
        for i in check["issues"]:
            link = f"<a class='id' href='#{i['id']}'>{i['id']}</a>" if i["id"] else ""
            rows.append(f"<li class='{i['level']}' data-s>{link}{_e(i['text'])}</li>")
        add("<ul class='check'>" + "".join(rows) + "</ul>")

    feats = getattr(g, "features", [])
    add("<h2 id='features'>Features</h2>" + ("" if feats else "<p class='muted'>None listed yet.</p>"))
    for f in feats:
        flows = " ".join(idlink(i) for i in f.get("flow_ids", []))
        add(f"<div class='card' id='{_e(f['id'])}' data-s><span class='id'>{_e(f['id'])}</span><b>{_e(f['name'])}</b> "
            f"<span class='tag'>{_e(f['priority'])}</span> {flows}<div class='muted'>{_e(f.get('why', ''))}</div></div>")

    add("<h2 id='flows'>Flows</h2>")
    for f in (n for n in g.nodes.values() if n.layer.value == "FLOW"):
        steps = f.metadata.get("steps", [])
        add(f"<div class='card'{anchor(f.id)} data-s>{idlink(f.id)}<b>{_e(f.title)}</b> <span class='muted'>{_e(f.goal or '')}</span><div class='row'>")
        for i, st in enumerate(steps, 1):
            t, _, rest = st.partition(":")
            add(f"<div class='step'><span class='muted'>{i}</span> <b>{_e(t if rest else '')}</b>{_e(rest.strip() or st)}</div>")
        add("</div>")
        for b in f.metadata.get("branches", []):
            path = "; ".join(_e(x) for x in b.get("steps", [])) or "<span class='tag bad'>not decided yet</span>"
            end = f"back to step {b['rejoin_step']}" if b.get("rejoin_step") else "ends here"
            add(f"<div class='branch'>After step {b['at_step']}, <b>{_e(b['decision'])}</b> {_e(b['label'])}: {path} <span class='muted'>({end})</span></div>")
        add("</div>")

    screens = [n for n in g.nodes.values() if n.layer.value == "SCREEN"]
    add("<h2 id='screens'>Screens</h2>" + ("" if screens else "<p class='muted'>Not drawn yet: the flows come first.</p>"))
    for s in screens:
        ready = g.evaluate_branch_readiness(s.id).is_build_ready
        add(f"<div class='card'{anchor(s.id)} data-s>{idlink(s.id)}<b>{_e(s.title)}</b> <span class='tag {'ok' if ready else ''}'>{'ready to build' if ready else 'not ready'}</span> "
            f"<span class='muted'>in</span> {idlink(s.flow_id)}<div class='muted'>{_e(s.description or '')}</div><ul>")
        for el in s.metadata.get("elements", []):
            add(f"<li>{_e(el.get('kind', ''))} <b>{_e(el.get('label', ''))}</b>{(': ' + _e(el['detail'])) if el.get('detail') else ''}</li>")
        for c in (g.nodes[i] for i in sorted(g.forward_edges.get(s.id, [])) if i in g.nodes and g.nodes[i].layer.value == "CTA"):
            apis = [g.nodes[a] for a in sorted(g.forward_edges.get(c.id, [])) if a in g.nodes and g.nodes[a].layer.value == "API"]
            add(f"<li{anchor(c.id)}>{idlink(c.id)}button <b>{_e(c.label)}</b>" + "".join(f" calls {idlink(a.id)}<code>{_e(a.method)} {_e(a.path)}</code>" for a in apis) + "</li>")
        add("</ul></div>")

    add("<h2 id='decisions'>Decisions</h2><ul>" + "".join(
        f"<li data-s><b>{_e(q.question_text)}</b> {_e(q.answer_text or '')} <span class='muted'>({_e(q.metadata.get('answered_by') or who)}{', a default' if q.metadata.get('default') else ''})</span></li>"
        for q in decided) + "</ul>")
    notes = getattr(g, "comments", [])
    if notes:  # what people wrote on the board itself (Ravi's note was missing from the page)
        add("<h2 id='notes'>Notes on the board</h2><ul>" + "".join(
            f"<li data-s>{idlink(c['target'])}{_e(c['text'])} <span class='muted'>({_e(c.get('by') or who)}; {'applied' if c.get('status') == 'applied' else 'waiting'})</span></li>"
            for c in notes) + "</ul>")
    need = "<span class='tag bad'>needed before building</span> "
    add("<h2 id='open'>Still open</h2><ul>" + ("".join(
        f"<li data-s>{need if q.is_blocking else ''}{_e(q.question_text)} {idlink(q.target_node_id)}</li>" for q in still)
        or "<li>Nothing.</li>") + "</ul>")
    add(f"</main><script>{_JS}</script></body></html>")
    return "".join(out)
