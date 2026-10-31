/** Distinguish native HTTP/WASM startup from page and worker request reporting. */
import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const {chromium}=createRequire(import.meta.url)('playwright');
const base=process.argv[2], phase=process.argv[3];
const out=path.resolve('docs/review/dialogue-acceptance-20261031',phase);
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.BO_BROWSER_EXECUTABLE});
const context=await browser.newContext();
const pending=new Map(), failures=[], requests=[];
context.on('request',request=>pending.set(request,{path:new URL(request.url()).pathname,start:Date.now()}));
context.on('requestfinished',request=>{const item=pending.get(request);if(item)requests.push({...item,duration_ms:Date.now()-item.start});pending.delete(request);});
context.on('requestfailed',request=>{failures.push({path:new URL(request.url()).pathname,error:request.failure()?.errorText});pending.delete(request);});
const page=await context.newPage();
const report={base};
try{
 await page.goto(base+'/graph?lang=en');
 await page.waitForFunction(()=>window.graphDebug?.graph&&!graphDebug.layoutBusy);
 report.streaming=await page.evaluate(async()=>{
  const start=performance.now();
  const response=await fetch('/libavoid.wasm');
  const type=response.headers.get('Content-Type');
  try{const module=await WebAssembly.compileStreaming(response);return{ok:true,type,ms:performance.now()-start,exports:WebAssembly.Module.exports(module).length};}
  catch(error){return{ok:false,type,error:String(error),ms:performance.now()-start};}
 });
 report.route=await page.evaluate(()=>({text:document.querySelector('#route-status')?.textContent,hidden:document.querySelector('#route-status')?.hidden}));
 report.passed=report.streaming.ok;
}catch(error){report.passed=false;report.error=String(error.stack);}
Object.assign(report,{pending:[...pending.values()],failures,requests});
await writeFile(path.join(out,'transport.json'),JSON.stringify(report,null,2));
await browser.close();
console.log(JSON.stringify({passed:report.passed,streaming:report.streaming,route:report.route,failures}));
if(!report.passed)process.exitCode=1;
