/** Details and analysis steps are shared across both renderers, with no native effects. */
import assert from "node:assert/strict";
import {behaviorRecords, behaviorDetailElement} from "../skills/vibelens/assets/stategraph-viewer/behavior-details.js";
import {logicalStep, logicalTimeline} from "../skills/vibelens/assets/stategraph-viewer/logical-trace.js";
import {buildTraceIndex} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import {setLocale} from "../skills/vibelens/assets/stategraph-viewer/i18n.js";

class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.dataset={}; this.listeners={}; }
  append(...children) { this.children.push(...children); }
  addEventListener(name, callback) { this.listeners[name]=callback; }
  texts() { return [this.textContent || "", ...this.children.map((child)=>child.texts())].join(" "); }
}
const document = {createElement:(tag)=>new Element(tag), createTextNode:(text)=>Object.assign(new Element("text"),{textContent:text})};
const view={behavior_context:{schema:"bo-behavior-details/v1",definition_sha256:"one",nodes:{share:["action/grant"]},
  records:{"action/grant":{id:"grant",kind:"action",completion:{kind:"commit",meaning:"Save <script>"},
    binding:{entry:{node:"f"}},transition:{source:"inactive",dest:"active"}}},unresolved:[],exclusions:[],last_verification:null}};
const original=structuredClone(view);
for (const [locale,label] of [["en","Behavior details"],["zh-CN","行为定义"]]) {
  setLocale(locale);
  const element=behaviorDetailElement({id:"share"},view,{document,open:new Set(["action/grant"])});
  assert.ok(element.texts().includes(label));
  if(locale==='zh-CN') {
    assert.ok(element.texts().includes('动作'));
    assert.ok(element.texts().includes('绑定'));
    assert.ok(!element.texts().includes('Binding:'));
  }
  assert.ok(element.texts().includes("Save <script>"));
  assert.equal(element.children[1].open,true,"Definition expansion survives live refresh");
  assert.equal(element.innerHTML,undefined,"Model text is not inserted as HTML");
}
assert.deepEqual(view,original);
let highlighted;
const focus = behaviorDetailElement({id:"share"},view,{document,onHighlight:ids=>highlighted=ids});
focus.children[1].children.find(child=>child.tagName==='button').listeners.click();
assert.deepEqual(highlighted,['share']);
assert.equal(behaviorRecords({id:"occurrence",referenceOf:"share"},view).length,1);
assert.equal(behaviorDetailElement({id:"other"},view,{document}),null);
assert.ok(behaviorDetailElement({id:"other"}, {behavior_context:{status:"unavailable",error:"Draft revision changed"}}, {document}).texts().includes("Draft revision changed"));
const all=new Map([['b',{id:'b',kind:'action',layer:'business'}],['s',{id:'s',kind:'state',layer:'state'}]]);
const edges=[{id:'bs',from:'b',to:'s',type:'action_requests_event'}];
const trace={schema:'bo-analysis-trace/v1',origin:'model_analysis',subject:'design_model',axis:'logical_step',analysis_id:'run',definition_sha256:'one',
  states:[{v:0},{v:1},{v:1}],projected_steps:[{action:'act',nodes:['b','s'],edges:['bs'],changes:[{variable:'v',before:0,after:1}]},
    {action:null,nodes:[],edges:[],changes:[]}],loop_back:1};
const step=logicalStep(trace,1,all,edges), timeline=logicalTimeline(trace,all,edges,['business','state']);
assert.deepEqual(step.nodes,['b','s']); assert.equal(timeline.rows.length,2);
assert.equal(timeline.links[0].edge,'bs'); assert.equal(timeline.loopBack,1);
assert.equal(logicalStep(trace,2,all,edges).loopBack,1);
assert.deepEqual(logicalStep(trace,1,new Map([['b',all.get('b')]]),edges).hidden,['s']);
assert.ok(!JSON.stringify(timeline).includes('duration'));
assert.throws(()=>logicalStep(trace,100,all,edges),/outside/);
assert.throws(()=>buildTraceIndex({...trace,context:{model:{edges:[]}}},[],all),/logical trace/);
assert.throws(()=>logicalTimeline({...trace,origin:'runtime'},all,edges),/logical/);
console.log('PASS: bilingual details, retained expansion, safe text, shared logical steps, original edges and runtime separation.');
