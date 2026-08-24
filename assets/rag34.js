(()=>{
const byId=id=>document.getElementById(id);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));

const points=[
  {name:'domain-wall depinning',v:[.92,.34]},
  {name:'ferroelectric switching',v:[.79,.49]},
  {name:'random-field disorder',v:[.66,.62]},
  {name:'cooking recipe',v:[-.72,.42]},
  {name:'football score',v:[-.62,-.55]},
  {name:'query: coercive field disorder',v:[.86,.53],query:true},
];
function dot(a,b){return a[0]*b[0]+a[1]*b[1]}
function norm(a){return Math.sqrt(dot(a,a))||1}
function cosine(a,b){return dot(a,b)/(norm(a)*norm(b))}
function l2(a,b){return Math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)}
function renderEmbedding(){
  const plane=byId('vectorPlane'),list=byId('similarityList'); if(!plane||!list)return;
  const metric=byId('embedMetric')?.value||'cosine'; const normalize=!!byId('embedNormalize')?.checked;
  plane.querySelectorAll('.vector-dot').forEach(x=>x.remove());
  points.forEach(p=>{const v=normalize?[p.v[0]/norm(p.v),p.v[1]/norm(p.v)]:p.v; const el=document.createElement('div'); el.className='vector-dot'+(p.query?' query':''); el.textContent=p.name; el.style.left=`${50+v[0]*38}%`; el.style.top=`${50-v[1]*38}%`; plane.appendChild(el)});
  const q=points.find(x=>x.query).v;
  const rows=points.filter(x=>!x.query).map(p=>{let s; if(metric==='cosine')s=cosine(q,p.v); else if(metric==='dot')s=dot(q,p.v); else s=-l2(q,p.v); return {...p,s}}).sort((a,b)=>b.s-a.s);
  const raw=rows.map(x=>x.s),min=Math.min(...raw),max=Math.max(...raw); list.innerHTML=rows.map((r,i)=>{const pct=max===min?100:clamp((r.s-min)/(max-min)*100,5,100); const shown=metric==='l2'?Math.abs(r.s).toFixed(3):r.s.toFixed(3); return `<div class="sim-row"><div class="sim-head"><b>#${i+1} ${r.name}</b><span>${metric==='l2'?'distance ':'score '}${shown}</span></div><div class="sim-bar"><i style="width:${pct}%"></i></div></div>`}).join('');
  const note=byId('metricNote'); if(note)note.textContent=metric==='cosine'?'Cosine 看方向夹角，向量长度影响被归一化。':metric==='dot'?'Dot product 同时受方向和向量长度影响；只有在明确归一化语义时才可和 cosine 类比。':'L2 看欧氏距离；距离越小越近。';
}
['embedMetric','embedNormalize'].forEach(id=>byId(id)?.addEventListener('change',renderEmbedding)); renderEmbedding();

const graphPath=[['L2',[1,7]],['L1',[1,4,7]],['L0',[1,2,4,5,7,8,9]]];
function renderAnn(){
  if(!byId('efSearch'))return; const ef=Number(byId('efSearch').value),n=Number(byId('datasetSize').value); byId('efVal').textContent=ef; byId('datasetVal').textContent=Number(n).toLocaleString();
  const recall=clamp(72+Math.log2(ef)*4.2+(n<50000?3:0),74,99.6); const visited=Math.round(ef*(2.2+Math.log10(n))); const exactVisited=n; const annLatency=Math.max(.4,visited/120); const exactLatency=Math.max(1,n/18000);
  byId('annRecall').textContent=recall.toFixed(1)+'%'; byId('annVisited').textContent=visited.toLocaleString(); byId('annLatency').textContent=annLatency.toFixed(1)+' ms*'; byId('exactLatency').textContent=exactLatency.toFixed(1)+' ms*'; const bar=byId('recallBar'); if(bar)bar.style.width=recall+'%';
  const note=byId('annNote'); if(note)note.textContent=`教学模拟：Exact 检查 ${exactVisited.toLocaleString()} 个向量；ANN 只访问约 ${visited.toLocaleString()} 个候选。efSearch 增大会通常提高 recall，也增加访问量和延迟。`;
  document.querySelectorAll('[data-graph-layer]').forEach((layer,idx)=>{const arr=graphPath[idx][1]; layer.querySelector('.graph-nodes').innerHTML=arr.map((x,j)=>`<span class="graph-node ${j<Math.ceil(arr.length*ef/160)?'visited':''} ${x===8?'target':''}">${x}</span>`).join('')});
}
['efSearch','datasetSize'].forEach(id=>byId(id)?.addEventListener('input',renderAnn)); renderAnn();

const hnswBtn=byId('walkHnsw'); if(hnswBtn){hnswBtn.addEventListener('click',()=>{const levels=document.querySelectorAll('.hnsw-level'); levels.forEach(l=>l.querySelectorAll('.tiny-node').forEach(n=>n.classList.remove('path'))); let delay=0; levels.forEach((l,li)=>{const nodes=[...l.querySelectorAll('.tiny-node')]; nodes.slice(0,Math.min(nodes.length,li+2)).forEach(n=>{setTimeout(()=>n.classList.add('path'),delay);delay+=180})})})}

const exactBtn=byId('runExact'),annBtn=byId('runApprox');
function renderResults(mode){const box=byId('searchResults');if(!box)return; const exact=[['c17','domain-wall depinning',.96],['c04','coercive field vs disorder',.91],['c28','finite-size scaling',.86]]; const approx=Number(byId('efSearch')?.value||50)<35?[exact[0],exact[2],['c11','random-field switching',.82]]:exact; const rows=mode==='exact'?exact:approx; box.innerHTML=rows.map((r,i)=>`<div class="retrieval-result"><span class="rank">#${i+1}</span><div><b>${r[0]}</b><p>${r[1]}</p></div><span class="score">${r[2].toFixed(2)}</span></div>`).join('')}
exactBtn?.addEventListener('click',()=>renderResults('exact'));annBtn?.addEventListener('click',()=>renderResults('ann'));renderResults('exact');
})();