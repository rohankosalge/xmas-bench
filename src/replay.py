"""Generate a turn-by-turn replay of an XMAS solve as a self-contained HTML file.

    python src/replay.py --variant baseline --puzzle mini-2026-07-05

Re-runs the solve with tracing (LLM calls) and writes replays/<variant>/<puzzle>.{json,html}.
Open the .html in any browser: step/play through the grid filling in, with an event log.
"""

import argparse
import glob
import json
import os

import puz

import benchmark
import config
import engine


def build(variant, puzzle_name):
    """Run the variant on a puzzle with tracing; return the replay trace dict."""
    spec = config.XMAS_VARIANTS[variant]
    puzzle = puz.read(os.path.join(config.OUTPUT_DIR, puzzle_name + ".puz"))
    ctx = engine._run(puzzle, spec)
    return {
        "puzzle": puzzle_name,
        "variant": variant,
        "width": ctx.grid.width,
        "height": ctx.grid.height,
        "solution": puzzle.solution,
        "slots": [{"id": s.id, "dir": s.direction, "cells": s.cells, "clue": s.clue}
                  for s in ctx.grid.slots],
        "events": ctx.trace,
        "score": benchmark.score(ctx.grid, puzzle),
    }


def render_html(trace):
    data = json.dumps(trace, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__TRACE_JSON__", data)


def save(variant, puzzle_name):
    trace = build(variant, puzzle_name)
    out_dir = os.path.join(config.REPLAYS_DIR, variant)
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, puzzle_name)
    with open(stem + ".json", "w") as f:
        json.dump(trace, f)
    with open(stem + ".html", "w") as f:
        f.write(render_html(trace))
    return stem + ".html"


_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>XMAS replay</title>
<style>
  body{font:14px/1.4 system-ui,sans-serif;margin:20px;color:#222}
  #wrap{display:flex;gap:24px;align-items:flex-start}
  #grid{display:grid;gap:2px;background:#222;padding:2px;width:max-content}
  .cell{width:40px;height:40px;background:#fff;display:flex;align-items:center;
        justify-content:center;font-weight:700;font-size:20px;text-transform:uppercase}
  .cell.black{background:#222}
  .cell.hl{outline:3px solid #f5a623;outline-offset:-3px}
  .cell.ok{color:#1a7f37}.cell.bad{color:#cf222e}
  #log{max-height:520px;overflow:auto;width:420px;border:1px solid #ddd;border-radius:6px}
  .ev{padding:6px 10px;border-bottom:1px solid #eee;cursor:pointer}
  .ev.cur{background:#fff8e1}
  .ev .tag{font-weight:700;font-size:11px;padding:1px 6px;border-radius:4px;color:#fff;margin-right:6px}
  .place .tag{background:#1a7f37}.guess .tag{background:#6f42c1}.propose .tag{background:#0969da}
  .chip{display:inline-block;font-size:12px;padding:1px 6px;margin:2px 3px 0 0;border-radius:10px;
        background:#eee;color:#555}
  .chip.fit{background:#dafbe1;color:#1a7f37}
  #bar{margin:12px 0}button{font:inherit;padding:4px 10px;margin-right:6px}
  #slider{width:320px;vertical-align:middle}
</style></head><body>
<h2 id="title"></h2>
<div id="bar">
  <button id="prev">◀ Prev</button><button id="play">▶ Play</button><button id="next">Next ▶</button>
  <input id="slider" type="range" min="0" value="0"><span id="count"></span>
  <label style="margin-left:12px"><input id="correct" type="checkbox"> show correctness</label>
</div>
<div id="wrap"><div id="grid"></div><div id="log"></div></div>
<script>
const TRACE = __TRACE_JSON__;
const W=TRACE.width, H=TRACE.height, SOL=TRACE.solution, EV=TRACE.events;
let cur = Math.max(0, EV.length-1), timer=null;

document.getElementById("title").textContent =
  `${TRACE.puzzle} — ${TRACE.variant}  (cell ${(TRACE.score.cell_acc*100).toFixed(0)}%, `+
  `word ${(TRACE.score.word_acc*100).toFixed(0)}%, ${TRACE.score.solved?"solved":"unsolved"})`;

const gridEl=document.getElementById("grid");
gridEl.style.gridTemplateColumns=`repeat(${W}, 40px)`;
const cells=[];
for(let i=0;i<W*H;i++){const d=document.createElement("div");d.className="cell";
  if(SOL[i]===".")d.classList.add("black");gridEl.appendChild(d);cells.push(d);}

// event log (built once)
const logEl=document.getElementById("log");
EV.forEach((e,k)=>{const d=document.createElement("div");d.className="ev "+e.type;d.dataset.k=k;
  let body="";
  if(e.type==="propose")body=`<b>${e.slot}</b> ${e.clue} <code>${e.pattern}</code><br>`+
    e.candidates.map(c=>`<span class="chip ${c.fits?'fit':''}">${c.word} ${c.conf}</span>`).join("");
  else if(e.type==="place")body=`<b>${e.slot}</b> = <b>${e.word}</b> (${e.conf}) — ${e.clue}`;
  else body=`cell ${e.cell} = <b>${e.letter}</b>`;
  d.innerHTML=`<span class="tag">${e.type.toUpperCase()} r${e.round}</span>${body}`;
  d.onclick=()=>{cur=k;render();};logEl.appendChild(d);});

const slider=document.getElementById("slider");slider.max=EV.length-1;

function stateAt(i){const L={};for(let k=0;k<=i;k++){const e=EV[k];
  if(e.type==="place")for(let j=0;j<e.cells.length;j++)L[e.cells[j]]=e.word[j];
  else if(e.type==="guess")L[e.cell]=e.letter;}return L;}

function render(){
  const L=stateAt(cur), e=EV[cur];
  const changed=new Set(e.type==="place"?e.cells:e.type==="guess"?[e.cell]:[]);
  const showC=document.getElementById("correct").checked;
  for(let i=0;i<W*H;i++){const d=cells[i];if(SOL[i]===".")continue;
    const ch=L[i]||"";d.textContent=ch;
    d.classList.remove("hl","ok","bad");
    if(changed.has(i))d.classList.add("hl");
    if(showC&&ch)d.classList.add(ch===SOL[i]?"ok":"bad");}
  document.querySelectorAll(".ev").forEach(x=>x.classList.remove("cur"));
  const cd=logEl.children[cur];if(cd){cd.classList.add("cur");cd.scrollIntoView({block:"nearest"});}
  slider.value=cur;document.getElementById("count").textContent=` ${cur+1} / ${EV.length}`;
}
function go(i){cur=Math.max(0,Math.min(EV.length-1,i));render();}
document.getElementById("prev").onclick=()=>go(cur-1);
document.getElementById("next").onclick=()=>go(cur+1);
slider.oninput=()=>go(+slider.value);
document.getElementById("correct").onchange=render;
document.getElementById("play").onclick=function(){
  if(timer){clearInterval(timer);timer=null;this.textContent="▶ Play";return;}
  this.textContent="⏸ Pause";if(cur>=EV.length-1)cur=0;
  timer=setInterval(()=>{if(cur>=EV.length-1){clearInterval(timer);timer=null;
    document.getElementById("play").textContent="▶ Play";return;}go(cur+1);},450);};
render();
</script></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default=config.DEFAULT_VARIANT)
    ap.add_argument("--puzzle", default=None, help="puzzle name without .puz (default: newest)")
    args = ap.parse_args()
    name = args.puzzle
    if not name:
        newest = sorted(glob.glob(os.path.join(config.OUTPUT_DIR, "*.puz")))[-1]
        name = os.path.splitext(os.path.basename(newest))[0]
    path = save(args.variant, name)
    print("wrote", path)
