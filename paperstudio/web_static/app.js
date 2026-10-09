const $ = id => document.getElementById(id);
const token=document.querySelector('meta[name="csrf-token"]').content;
const form=$('upload-form');let selected=[],poller=null,activeJob=null,mdSource='',activeDoc=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const bytes=n=>n>1048576?(n/1048576).toFixed(1)+' MB':(n/1024).toFixed(1)+' KB';
function showFiles(files){selected=Array.from(files||[]);$('file-list').textContent=selected.length?selected.map(f=>`${f.name} (${bytes(f.size)})`).join(' · '):'尚未选择文件';}
$('files').addEventListener('change',e=>showFiles(e.target.files));
for(const name of ['dragenter','dragover']) $('dropzone').addEventListener(name,e=>{e.preventDefault();$('dropzone').classList.add('dragover')});
for(const name of ['dragleave','drop']) $('dropzone').addEventListener(name,e=>{e.preventDefault();$('dropzone').classList.remove('dragover')});
$('dropzone').addEventListener('drop',e=>showFiles([...e.dataTransfer.files].filter(f=>f.name.toLowerCase().endsWith('.pdf'))));
const engineInfo={
 none:['','','无需翻译服务。',false,false],
 ollama:['qwen2.5:3b','http://127.0.0.1:11434','免费本地 LLM；先执行 ollama pull qwen2.5:3b。',true,false],
 argos:['','','离线免费；需 pip install -r requirements-free.txt 并安装 en→zh 语言包。',false,false],
 libretranslate:['','http://127.0.0.1:5000','自建服务可免费使用；官方托管服务需要 API Key。',false,true],
 deepseek:['deepseek-flash','https://api.deepseek.com','DeepSeek 商业 API，当前推荐 deepseek-flash；使用量可能收费。',true,true],
 openai:['gpt-4.1-mini','https://api.openai.com/v1','OpenAI 商业 API，会上传待翻译文本。',true,true],
 deepl:['','','DeepL API 使用对应密钥；免费额度由账户方案决定。',false,true]
};
let lastEngine='';
function updateEngine(){
 const e=$('engine').value, i=engineInfo[e];
 if(e!==lastEngine){$('model').value=i[0];$('api_url').value=i[1];$('api_key').value='';lastEngine=e;}
 $('model-row').classList.toggle('hidden',!i[3]);$('endpoint-row').classList.toggle('hidden',e==='none'||e==='argos');
 $('key-row').classList.toggle('hidden',!i[4]);$('test-engine').disabled=e==='none';
 $('engine-help').textContent=i[2];$('privacy').textContent=(['none','ollama','argos'].includes(e)?'ⓘ 本机模式：':'⚠ 远程翻译：')+i[2];
 $('engine-test-result').textContent='';
}
$('engine').addEventListener('change',updateEngine);updateEngine();
$('test-engine').addEventListener('click',async()=>{
 const btn=$('test-engine');btn.disabled=true;$('engine-test-result').textContent='连接中…';
 try{let cfg={engine:$('engine').value,model:$('model').value,api_url:$('api_url').value,api_key:$('api_key').value};
 const data=await fetchJson('/api/engines/test',{method:'POST',headers:{'X-CSRF-Token':token,'Content-Type':'application/json'},body:JSON.stringify(cfg)});
 $('engine-test-result').textContent='✓ 已连接，测试译文：'+data.sample.slice(0,100);
 }catch(e){$('engine-test-result').textContent='✕ '+e.message;}finally{btn.disabled=false;}
});
async function fetchJson(url,options={}){const r=await fetch(url,options);const d=await r.json().catch(()=>({error:'服务器返回了非 JSON 响应'}));if(!r.ok)throw new Error(d.error||'请求失败');return d;}
form.addEventListener('submit',async e=>{e.preventDefault();$('feedback').textContent='';if(!selected.length){$('feedback').textContent='请先选择至少一个 PDF。';return;}if(selected.length>12||selected.reduce((s,f)=>s+f.size,0)>80*1024*1024){$('feedback').textContent='单次最多 12 个文件，总大小不超过 80 MB。';return;}const fd=new FormData(form);fd.delete('files');for(const f of selected)fd.append('files',f,f.name);for(const id of ['vector_figures','stitch_tables','snapshots']){let el=form.elements.namedItem(id);fd.set(id,el?.checked?'true':'false');}
$('submit').disabled=true;$('submit').firstElementChild.textContent='正在提交...';try{let j=await fetchJson('/api/jobs',{method:'POST',headers:{'X-CSRF-Token':token},body:fd});activeJob=j.id;$('empty-state').classList.add('hidden');$('task-state').classList.remove('hidden');$('results').innerHTML='';$('preview-wrap').classList.add('hidden');mdSource='';poll();clearInterval(poller);poller=setInterval(poll,1200);}catch(err){$('feedback').textContent=err.message;$('submit').disabled=false;$('submit').firstElementChild.textContent='开始转换';}});
async function poll(){if(!activeJob)return;try{let d=await fetchJson('/api/jobs/'+encodeURIComponent(activeJob));$('state-badge').textContent={queued:'排队中',running:'处理中',done:'已完成',warning:'完成（有警告）',error:'处理失败'}[d.status]||d.status;$('state-badge').className='state-badge '+(d.status==='done'?'done':d.status==='error'?'error':'');$('job-id').textContent='#'+d.id.slice(0,8);$('percent').textContent=d.progress+'%';$('progress').style.width=d.progress+'%';$('current-step').textContent=d.current||'';$('logs').textContent=(d.logs||[]).slice(-50).join('\n');if(d.status==='error')$('feedback').textContent=d.error||'任务失败';if(['done','warning','error'].includes(d.status)){clearInterval(poller);poller=null;$('submit').disabled=false;$('submit').firstElementChild.textContent='开始转换';renderResult(d);}}
catch(e){clearInterval(poller);poller=null;$('feedback').textContent='无法获取任务状态：'+e.message;$('submit').disabled=false;$('submit').firstElementChild.textContent='开始转换';}}
function renderResult(d){let warningBox=$('warnings');if(d.warnings?.length){warningBox.classList.remove('hidden');warningBox.textContent='注意：'+d.warnings.slice(0,5).join('；');}else warningBox.classList.add('hidden');const parent=$('results');parent.replaceChildren();if(d.zip_url){let a=document.createElement('a');a.href=d.zip_url;a.className='download main';a.textContent='↓ 下载全部结果 ZIP';parent.append(a);}for(const [i,file] of (d.files||[]).entries()){let card=document.createElement('div');card.className='result-card';let header=document.createElement('div');header.className='result-top';let title=document.createElement('strong');title.textContent=file.name;let pages=document.createElement('span');pages.textContent=file.pages?`${file.pages} 页`:'未成功';header.append(title,pages);card.append(header);let links=document.createElement('div');links.className='download-row';for(const fmt of ['md','pdf','txt']){if(file.urls?.[fmt]){let a=document.createElement('a');a.href=file.urls[fmt];a.className='download';a.textContent=fmt.toUpperCase()+' 下载';a.setAttribute('download','');links.append(a);}}if(file.urls?.md){let b=document.createElement('button');b.className='download';b.textContent='预览 Markdown';b.onclick=()=>loadPreview(i);links.append(b);}card.append(links);parent.append(card);}if(d.files?.some(f=>f.urls?.md))loadPreview(d.files.findIndex(f=>f.urls?.md));}
async function loadPreview(i){activeDoc=i;try{let r=await fetch('/api/jobs/'+encodeURIComponent(activeJob)+'/preview?file='+i);if(!r.ok)throw new Error('预览内容读取失败');mdSource=await r.text();$('preview-wrap').classList.remove('hidden');$('preview-source').textContent=mdSource;$('preview-render').innerHTML=toPreview(mdSource,i);showTab('render');}catch(e){$('feedback').textContent=e.message;}}
function inlineFmt(s,i){s=esc(s);s=s.replace(/!\[([^\]]*)\]\(assets\/([^\s)]+)\)/g,(_,alt,path)=>`<img alt="${alt}" loading="lazy" src="/api/jobs/${encodeURIComponent(activeJob)}/assets?file=${i}&path=${encodeURIComponent('assets/'+path)}"/>`);s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');s=s.replace(/`([^`]+)`/g,'<code>$1</code>');return s;}
function toPreview(text,i){let lines=text.slice(0,180000).split('\n'),out=[],listOpen=false,code=false;for(let line of lines){if(/^```/.test(line)){if(listOpen){out.push('</ul>');listOpen=false;}out.push(code?'</pre>':'<pre>');code=!code;continue;}if(code){out.push(esc(line)+'\n');continue;}if(!line.trim()){if(listOpen){out.push('</ul>');listOpen=false;}continue;}if(/^#{1,6} /.test(line)){if(listOpen){out.push('</ul>');listOpen=false;}const n=line.match(/^#+/)[0].length;out.push(`<h${n}>${inlineFmt(line.slice(n+1),i)}</h${n}>`);continue;}if(/^\s*[-*] /.test(line)){if(!listOpen){out.push('<ul>');listOpen=true;}out.push('<li>'+inlineFmt(line.replace(/^\s*[-*] /,''),i)+'</li>');continue;}if(listOpen){out.push('</ul>');listOpen=false;}if(/^\|/.test(line)){out.push('<pre>'+esc(line)+'</pre>');continue;}if(/^!\[/.test(line)){out.push('<p>'+inlineFmt(line,i)+'</p>');continue;}out.push('<p>'+inlineFmt(line,i)+'</p>');}if(listOpen)out.push('</ul>');if(code)out.push('</pre>');return out.join('');}
function showTab(tab){let rendered=tab==='render';$('preview-render').classList.toggle('hidden',!rendered);$('preview-source').classList.toggle('hidden',rendered);$('tab-render').classList.toggle('active',rendered);$('tab-source').classList.toggle('active',!rendered);}
$('tab-render').onclick=()=>showTab('render');$('tab-source').onclick=()=>showTab('source');$('copy-md').onclick=async()=>{try{await navigator.clipboard.writeText(mdSource);$('copy-md').textContent='已复制 ✓';setTimeout(()=>$('copy-md').textContent='复制完整 Markdown',1600);}catch(e){$('feedback').textContent='浏览器不允许自动复制，请切换源码视图手动复制。';}};
