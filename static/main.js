let app_state=null, selected_timeframe=localStorage.getItem('tf')||'H1';
const open_events=new Set();
const signal_class=t=>/Compra|Alta/.test(t)?'buy':/Venda|Baixa/.test(t)?'sell':'neu';
const $=id=>document.getElementById(id);
const escape_html=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function load_state(){
  try{const response=await fetch('/api/state');if(!response.ok) throw new Error('API indisponível');app_state=await response.json();$('connection-status').textContent='Painel conectado';$('connection-status').parentElement.classList.remove('offline');render_dashboard();}catch(e){$('connection-status').textContent='Painel desconectado';$('connection-status').parentElement.classList.add('offline')}
}
function render_dashboard(){
  $('sym').textContent=app_state.symbol;
  $('price').textContent=app_state.price?app_state.price.toFixed(2):'--';
  const technical_data=app_state.tech||{}, timeframes=Object.keys(technical_data);
  if(!timeframes.includes(selected_timeframe)&&timeframes.length) selected_timeframe=timeframes[0];
  $('tabs').innerHTML=timeframes.map(k=>`<button aria-pressed="${k==selected_timeframe}" onclick="selected_timeframe='${k}';localStorage.setItem('tf',selected_timeframe);render_dashboard()">${k}<small class="${signal_class(technical_data[k].label)}">${technical_data[k].label}</small></button>`).join('');
  const current_analysis=technical_data[selected_timeframe];
  if(current_analysis){
    $('tfn').textContent=selected_timeframe;
    $('verdict').textContent=current_analysis.label;$('verdict').className='verdict '+signal_class(current_analysis.label);
    $('pa-tf').textContent=selected_timeframe;
    const patterns=current_analysis.price_action||[];
    $('price-action').innerHTML=patterns.length?patterns.map(p=>`<div class="ev"><div><b class="${signal_class(p.direction)}">Possível reversão de ${escape_html(p.direction.toLowerCase())} em ${Number(p.price).toFixed(2)}</b><div class="mut">${escape_html(p.pattern)} · ${new Date(p.time*1000).toLocaleString('pt-BR')}</div></div></div>`).join(''):'Nenhum padrão de reversão identificado nos últimos 40 candles fechados.';
    $('ind').innerHTML=current_analysis.indicators.map(i=>`<tr><td>${escape_html(i.name)}</td><td>${i.value}</td><td class="${signal_class(i.signal)}">${i.signal}</td></tr>`).join('');
  }
  const a=app_state.ai;
  const status=app_state.ai_status?.state||'starting';
  const messages={starting:'Carregando dados para a análise...',loading:'Atualizando previsões e análise...',disabled:'Configure OPENAI_API_KEY para ativar as previsões.',error:'Não foi possível atualizar a análise. Nova tentativa em alguns minutos.',ready:'Previsões atualizadas periodicamente.'};
  $('ai-status').innerHTML=`${['starting','loading'].includes(status)?'<span class="spinner" aria-hidden="true"></span>':''}${messages[status]||''}`;
  if(!a) $('ai').textContent=status==='disabled'?'Análise de IA desativada.':status==='error'?'Análise indisponível no momento.':'Aguardando análise.';
  if(a){
    $('bias').textContent=`${a.vies} (${a.confianca}%)`;$('bias').className='verdict '+signal_class(a.vies);
    $('ai').innerHTML=`<p style="margin:0 0 6px">${escape_html(a.resumo)}</p><div class="mut">${escape_html(a.motivo)}</div><div class="mut">Análise atualizada em ${app_state.updated?.ai?new Date(app_state.updated.ai*1000).toLocaleString('pt-BR'):'--'} · inclui notícias e eventos USD disponíveis no momento da análise.</div>`;
  }
  const items=(a&&a.itens)||[], analyzed_news=(a&&a.noticias_base)||[];
  $('news').innerHTML=(app_state.news||[]).map((n,i)=>{
    const news_index=analyzed_news.findIndex(x=>x.title===n.title && x.link===n.link);
    const it=items.find(x=>x.n===news_index+1);
    return `<li><a href="${escape_html(n.link)}" target="_blank" rel="noopener">${escape_html(n.title)}</a>
      <div class="mut">${escape_html(n.src)}${it?` · <span class="${signal_class(it.impacto)}">${escape_html(it.impacto)}</span>: ${escape_html(it.nota)}`:''}</div></li>`}).join('');
  render_events();
}
function render_events(){
  if(!app_state) return;
  const status=app_state.ai_status?.state||'starting';
  const now=Date.now(), all=app_state.events||[];
  const recent=all.filter(e=>e.ts>=now-48*3600000&&e.ts<=now).slice(-8).reverse();
  const upcoming=all.filter(e=>e.ts>now&&e.ts<=now+72*3600000).slice(0,8);
  const next=all.find(e=>e.ts>now);
  $('next-event').textContent=next?next.title:'Nenhum evento disponível';
  $('next-event-time').textContent=next?`${new Date(next.ts).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})} · impacto ${next.impact==='High'?'alto':'médio'}`:'Acompanhe o calendário';
  const render_event=e=>{
    const d=e.ts-now, m=Math.floor(Math.abs(d)/60000), h=Math.floor(m/60);
    const when=d<0?(h?`há ${h}h ${m%60}min`:`há ${m} min`):h>=24?`em ${Math.floor(h/24)}d ${h%24}h`:`em ${h?h+'h ':''}${m%60}min`;
    const hr=new Date(e.ts).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
    const base=(app_state.ai?.eventos_base||[]), index=base.findIndex(x=>x.title===e.title && x.ts===e.ts);
    const analysis=(app_state.ai?.eventos||[]).find(x=>x.id===index+1);
    const unchanged=index>=0 && ['actual','forecast','previous'].every(k=>(base[index][k]||'')===(e[k]||''));
    const scenarios=unchanged&&Array.isArray(analysis?.cenarios)?analysis.cenarios:[];
    const id=JSON.stringify([e.title,e.ts]);
    return `<div class="ev ${e.impact==='High'?'high':'med'}"><div class="event-head"><div><b class="event-title">${escape_html(e.title)}</b><div class="mut">${hr} · impacto ${e.impact==='High'?'alto':'médio'} · previsto ${escape_html(e.forecast||'não disponível')} · anterior ${escape_html(e.previous||'não disponível')} · resultado ${escape_html(e.actual||'não disponível')}</div></div><div class="cd ${d>0&&d<3600000?'soon':''}">${when}</div></div>
      <details data-event="${escape_html(id)}" ${open_events.has(id)?'open':''}><summary>Ver análise e cenários</summary>
      ${unchanged&&analysis?`<div class="mut">${escape_html(analysis.leitura)}</div>`:''}
      ${scenarios.length?`<div class="scenarios">${scenarios.map(c=>`<div class="scenario"><b>${escape_html(c.resultado)}</b> → <span class="${signal_class(c.impacto)}">${escape_html(c.impacto)}</span>: ${escape_html(c.explicacao)}</div>`).join('')}</div>`:`<div class="mut">${status==='loading'||status==='starting'?'Carregando cenários...':status==='error'?'Não foi possível atualizar os cenários.':status==='disabled'?'Ative a análise de IA para ver os cenários.':'Aguardando atualização da análise deste evento.'}</div>`}</details></div>`;
  };
  const scroll_top=$('events').scrollTop;
  $('events').innerHTML=(recent.length||upcoming.length)?`${recent.length?'<h3>Recentes</h3>'+recent.map(render_event).join(''):''}${upcoming.length?'<h3>Próximos</h3>'+upcoming.map(render_event).join(''):''}`:'<div class="mut">Nenhum evento disponível neste período.</div>';
  $('events').scrollTop=scroll_top;
  if(app_state.updated?.cal_error) $('events').insertAdjacentHTML('afterbegin','<p class="mut">Não foi possível atualizar o calendário; os dados exibidos podem estar desatualizados.</p>');
}
$('events').addEventListener('toggle',e=>{if(e.target.matches('details[data-event]')){if(e.target.open) open_events.add(e.target.dataset.event); else open_events.delete(e.target.dataset.event);}},true);
load_state();setInterval(load_state,10000);setInterval(render_events,30000);
