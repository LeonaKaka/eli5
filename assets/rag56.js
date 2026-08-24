(()=>{
const $=s=>document.querySelector(s);const $$=s=>Array.from(document.querySelectorAll(s));
const datasets={
semantic:{label:'自然语言：无序如何影响矫顽场？',dense:[['cA','Random-field disorder lowers coercive field',.94],['cB','Domain-wall pinning and depinning',.88],['cC','Finite-size scaling of Ec',.81]],bm25:[['cC','Finite-size scaling of Ec',7.8],['cA','Random-field disorder lowers coercive field',5.1],['cD','Coercive-field measurement protocol',4.7]]},
id:{label:'精确标识：DOI 10.1103/PhysRevLett.136.206202',dense:[['cP','Shear-mode Raman imaging of sliding ferroelectrics',.78],['cQ','Raman spectroscopy of layered materials',.74],['cR','Sliding ferroelectric domain walls',.71]],bm25:[['cX','DOI: 10.1103/PhysRevLett.136.206202',16.4],['cP','Shear-mode Raman imaging of sliding ferroelectrics',3.1],['cQ','Raman spectroscopy of layered materials',1.9]]},
error:{label:'错误码：CUDA_ERROR_700',dense:[['cM','GPU memory access failures',.72],['cN','CUDA debugging guide',.70],['cO','Driver compatibility notes',.66]],bm25:[['cZ','CUDA_ERROR_700: illegal memory access',18.2],['cN','CUDA debugging guide',4.0],['cM','GPU memory access failures',2.8]]},
model:{label:'型号：RTX 4060 Ti 16GB',dense:[['cG','Mid-range GPU for local inference',.84],['cH','VRAM requirements for inference',.82],['cI','Consumer GPU comparison',.79]],bm25:[['cJ','RTX 4060 Ti 16GB specifications',14.7],['cI','Consumer GPU comparison',6.2],['cH','VRAM requirements for inference',3.3]]}
};
function rrf(a,b,k=60){const m=new Map();[a,b].forEach(list=>list.forEach((x,i)=>{const v=m.get(x[0])||{id:x[0],text:x[1],score:0};v.score+=1/(k+i+1);m.set(x[0],v)}));return [...m.values()].sort((x,y)=>y.score-x.score).slice(0,4)}
function panel(title,items,type){return `<div class="rank-panel"><h4>${title}</h4>${items.map((x,i)=>`<div class="rank-item ${i===0?'win':''}"><span class="rank-pos">${i+1}</span><span>${x.text||x[1]}</span><span class="rank-score">${type==='rrf'?x.score.toFixed(4):x[2]}</span></div>`).join('')}</div>`}
function renderHybrid(key='semantic'){const d=datasets[key];const out=$('#hybridRanks');if(!out)return;out.innerHTML=panel('Dense / Semantic',d.dense)+panel('BM25 / Lexical',d.bm25)+panel('RRF Hybrid',rrf(d.dense,d.bm25),'rrf');const q=$('#hybridQuery');if(q)q.textContent=d.label;$$('[data-query-kind]').forEach(b=>b.classList.toggle('active',b.dataset.queryKind===key))}
$$('[data-query-kind]').forEach(b=>b.addEventListener('click',()=>renderHybrid(b.dataset.queryKind)));renderHybrid();
const tf=$('#bmTf'),idf=$('#bmIdf'),len=$('#bmLen');function bm(){if(!tf)return;const t=+tf.value,i=+idf.value,L=+len.value,k1=1.2,b=.75,avg=100;const score=i*((t*(k1+1))/(t+k1*(1-b+b*L/avg)));$('#bmTfVal').textContent=t;$('#bmIdfVal').textContent=i.toFixed(1);$('#bmLenVal').textContent=L;$('#bmScore').textContent=score.toFixed(2)}[tf,idf,len].filter(Boolean).forEach(x=>x.addEventListener('input',bm));bm();
const candidates=[
{id:'A',text:'Overview of ferroelectric switching',first:.93,rerank:.54},
{id:'B',text:'Random-field disorder lowers coercive field Ec',first:.88,rerank:.97,rel:true},
{id:'C',text:'Domain-wall imaging protocol',first:.86,rerank:.61},
{id:'D',text:'Finite-size scaling near depinning',first:.82,rerank:.78},
{id:'E',text:'Unrelated dielectric measurement',first:.79,rerank:.19},
{id:'F',text:'Exact evidence: Ec decreases as disorder sigma increases',first:.74,rerank:.99,rel:true},
{id:'G',text:'Supplementary fabrication details',first:.70,rerank:.31},
{id:'H',text:'Background on 2D materials',first:.67,rerank:.26}
];
function rerank(){const slider=$('#candidateK');if(!slider)return;const k=+slider.value;$('#candidateKVal').textContent=k;const first=candidates.slice(0,k);const ranked=[...first].sort((a,b)=>b.rerank-a.rerank);const box=$('#rerankCandidates');box.innerHTML=ranked.map((x,i)=>`<div class="candidate ${x.rel?'relevant':''}"><b>#${i+1}</b><span>${x.text}<br><small>first-stage #${candidates.indexOf(x)+1} · ${x.first.toFixed(2)}</small></span><span class="move">${x.rerank.toFixed(2)}</span></div>`).join('');const hidden=candidates.filter(x=>x.rel&&!first.includes(x));const msg=$('#rerankMessage');msg.className=hidden.length?'warning-band':'success-band';msg.innerHTML=hidden.length?`⚠️ 候选只取 top-${k}：相关证据 ${hidden.map(x=>x.id).join(', ')} 根本没进入 reranker，所以无法被“救回”。`:`✅ top-${k} 已覆盖两条关键证据；reranker 可以重新判断 query-document 相关性。`;const rr=Math.min(65,8+k*6),gen=27;$('#rerankLatency').innerHTML=`<span class="latency-retrieve" style="width:18%">retrieve</span><span class="latency-rerank" style="width:${rr}%">rerank ↑</span><span class="latency-generate" style="width:${gen}%">LLM</span>`}
const ck=$('#candidateK');if(ck){ck.addEventListener('input',rerank);rerank()}
})();