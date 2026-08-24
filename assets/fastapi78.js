(()=>{
  const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];

  const problemOut=q('#problemOut');
  if(problemOut){
    const scenarios={
      validation:{status:422,code:'validation_error',title:'Request validation failed',detail:'One or more request fields are invalid.',source:'RequestValidationError',errors:['body.objective · Value error','body.admin · Extra inputs are not permitted']},
      auth:{status:401,code:'authentication_required',title:'Authentication required',detail:'bearer authentication required',source:'HTTPException + WWW-Authenticate',errors:[]},
      forbidden:{status:403,code:'forbidden',title:'Forbidden',detail:'missing permission: runs:cancel',source:'permission dependency',errors:[]},
      missing:{status:404,code:'not_found',title:'Resource not found',detail:'run not found',source:'tenant-scoped lookup',errors:[]},
      conflict:{status:409,code:'conflict',title:'Request conflict',detail:'Idempotency-Key was already used for a different command',source:'idempotency registry',errors:[]},
      stale:{status:412,code:'precondition_failed',title:'Precondition failed',detail:'Run revision changed: expected 7, current 9',source:'If-Match precondition',errors:[]},
      unavailable:{status:503,code:'service_unavailable',title:'Service unavailable',detail:'Run queue is temporarily unavailable.',source:'domain/infrastructure adapter',errors:[]},
      crash:{status:500,code:'internal_error',title:'Internal server error',detail:'An unexpected server error occurred.',source:'RuntimeError("private-checkpoint-secret")',errors:[]}
    };
    const render=()=>{
      const key=q('#problemScenario').value, x=scenarios[key];
      qa('[data-problem-chip]').forEach(el=>el.classList.toggle('active',el.dataset.problemChip===key));
      const req='req-7a2f…';
      problemOut.textContent=JSON.stringify({type:`urn:research-assistant:problem:${x.code}`,title:x.title,status:x.status,detail:x.detail,instance:key==='validation'?'/runs':'/runs/run-42',code:x.code,request_id:req,...(x.errors.length?{errors:x.errors}: {})},null,2);
      q('#problemSource').textContent=x.source;
      q('#problemStatus').textContent=String(x.status);
      q('#problemCode').textContent=x.code;
      q('#problemRequest').textContent=req;
      q('#problemSafety').className=key==='crash'?'safe-box':'problem-field';
      q('#problemSafety').innerHTML=key==='crash'?'<strong>500 安全检查</strong>客户端只看到 generic detail；`private-checkpoint-secret` 只应进入带 request_id 的私有日志。':'<strong>公开 detail</strong>保留客户端完成下一步所需的信息，但不回显 stack trace / request body / Graph state。';
    };
    q('#problemScenario').addEventListener('change',render);render();
  }

  const testOut=q('#testOut');
  if(testOut){
    const modes={
      unit:{title:'Endpoint unit',real:['FastAPI routing','Pydantic response','exception handlers'],fake:['get_current_principal','get_bridge / external adapter'],goal:'快速验证 HTTP contract；不为每个测试启动真实身份提供商或整条 Agent runtime。'},
      integration:{title:'Integration',real:['Bearer demo authenticator','RunStore + Queue','ProductionGraphBridge','LangGraph teaching runtime'],fake:['外部云 provider（本课程仍 provider-free）'],goal:'验证组件真正接起来后的 tenant、revision、queue、interrupt 行为。'},
      contract:{title:'OpenAPI contract',real:['create_app()','FastAPI dependency graph','generated OpenAPI'],fake:['不需要执行 Worker'],goal:'锁 routes / securitySchemes / headers / response schemas，防客户端契约静默漂移。'}
    };
    const render=()=>{
      const key=q('#testMode').value,m=modes[key];
      qa('[data-test-layer]').forEach(el=>el.classList.toggle('active',el.dataset.testLayer===key));
      q('#testReal').innerHTML=m.real.map(x=>`<div>✅ ${x}</div>`).join('');
      q('#testFake').innerHTML=m.fake.map(x=>`<div>↪ ${x}</div>`).join('');
      testOut.textContent=`${m.title}\n\n目的：${m.goal}\n\n`+(key==='unit'?`app.dependency_overrides[get_current_principal] = fake_principal\napp.dependency_overrides[get_bridge] = fake_bridge\n\nGET /runs/run-unit\n→ 200 + ETag \"7\"`:(key==='integration'?`POST /runs\n→ real RunStore + Queue\n→ QUEUED\n\nworker tick / approval tests\n→ real revision + Graph boundary`:`GET /openapi.json\n→ BearerAuth\n→ ProblemDetails\n→ If-Match / Idempotency-Key\n→ documented 409 / 412 / 428`));
      q('#testWarning').textContent=key==='unit'?'如果把 Queue/revision/LangGraph 也全部 fake 掉，这个测试不能证明 durable control-plane 正确。':key==='integration'?'Integration 更慢，但这里必须保留真正想验的系统边界；只替换昂贵/外部依赖。':'OpenAPI 测试锁的是“外部协议”，不是实现细节；不要 snapshot 整份无关字段造成脆弱测试。';
    };
    q('#testMode').addEventListener('change',render);render();

    q('#overMock')?.addEventListener('click',()=>{
      q('#testWarning').textContent='⚠️ 你把 auth、RunStore、Queue、revision、Graph、event store 全 mock 了：测试当然很快，但现在只能证明 Python 函数返回了你预设的 dict。';
      q('#testOut').textContent='OVER-MOCKED\n\nroute → fake everything → expected response\n\n❌ tenant isolation 未验证\n❌ stale revision 未验证\n❌ duplicate queue delivery 未验证\n❌ interrupt/resume 未验证';
    });
  }
})();