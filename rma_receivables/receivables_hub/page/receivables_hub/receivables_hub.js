frappe.pages['receivables_hub'] = { on_page_load(wrapper){ _rma_receivables_onload(wrapper); } };
frappe.pages['receivables-hub'] = { on_page_load(wrapper){ _rma_receivables_onload(wrapper); } };
function rmaDebounce(fn, wait){ let t; return function(...args){ clearTimeout(t); t=setTimeout(()=>fn.apply(this,args), wait||250); } }
window.__rma_age_class = function(ag){
  if (!ag || (ag.total||0) <= 0) return {cls:'', badge:''};
  if ((ag.b90p||0) > 0) return {cls:'rma-age-bad', badge:'<span class="rma-badge bad">90+</span>'};
  if ((ag.b61_90||0) > 0) return {cls:'rma-age-hot', badge:'<span class="rma-badge hot">61–90</span>'};
  if ((ag.b31_60||0) > 0) return {cls:'rma-age-warn', badge:'<span class="rma-badge warn">31–60</span>'};
  return {cls:'rma-age-ok', badge:'<span class="rma-badge ok">0–30</span>'};
};
function _rma_receivables_onload(wrapper){
  const $body = $('#rma-body'); const $search = $('#rma-search'); const $overdue=$('#rma-overdue-only'); const $refresh=$('#rma-refresh');
  const $status=$('#rma-status'); const $tTotal=$('#rma-total'); const $tCount=$('#rma-count'); const $tDate=$('#rma-date');
  const $sendAll=$('#rma-send-all'); const $sendAllM=$('#rma-send-all-mobile'); const $prog=$('#rma-prog'); const $progM=$('#rma-prog-mobile');
  const $cg=$('#rma-cg'); const $fySel=$('#rma-fy-range'); const $from=$('#rma-from'); const $to=$('#rma-to'); const $fyChip=$('#rma-fy-chip');
  let fyCache=[];
  async function loadFY(){ try{ const rows=await frappe.db.get_list('Fiscal Year',{fields:['name','year_start_date','year_end_date','is_fiscal_year_closed'],order_by:'year_start_date desc',limit:6}); fyCache=rows||[]; updateFYUI(); }catch(e){} }
  function getSelectedRange(){ const sel=$fySel.val(); if(sel==='custom'){const s=$from.val(),e=$to.val(); return (s&&e)?{from:s,to:e,label:`${s} → ${e}`} : null;}
    if(!fyCache.length) return null; const cur=fyCache.find(x=>!x.is_fiscal_year_closed)||fyCache[0];
    if(sel==='current') return {from:cur.year_start_date,to:cur.year_end_date,label:cur.name};
    if(sel==='last'){ const idx=fyCache.indexOf(cur); const last=fyCache[(idx>=0?idx+1:1)]; return last?{from:last.year_start_date,to:last.year_end_date,label:last.name}:{from:cur.year_start_date,to:cur.year_end_date,label:cur.name};}
    if(sel==='last2'){ let list=[]; const curIdx=fyCache.indexOf(cur); list.push(cur); if(fyCache[curIdx+1]) list.push(fyCache[curIdx+1]); const from=list[list.length-1].year_start_date; const to=list[0].year_end_date; return {from,to,label:list.map(x=>x.name).join(' + ')};}
    return null; }
  function updateFYUI(){ const sel=$fySel.val(); if(sel==='custom'){ $from.show(); $to.show(); } else { $from.hide(); $to.hide(); } const r=getSelectedRange(); $fyChip.text('FY Range: ' + (r ? r.label : 'Auto')); }
  async function loadSummary(){ try{ const s=await frappe.call({method:'rma_receivables.ui.get_dashboard_summary'}); const m=s.message||{}; $tTotal.text(format_currency(m.total_outstanding||0,m.currency||undefined)); $tCount.text(m.customers_with_outstanding||0); $tDate.text(m.as_on||frappe.datetime.get_today()); }catch(e){} }
  function renderSkeleton(n=5){ $body.empty(); for(let i=0;i<n;i++){ $body.append(`<tr><td data-label="Customer"><div class="rma-skel" style="width:60%"></div></td><td data-label="Outstanding" class="text-right"><div class="rma-skel" style="width:40%"></div></td><td data-label="Aging"><div class="rma-skel" style="width:90%"></div></td><td data-label="Actions"><div class="rma-skel" style="width:90%"></div></td></tr>`);} }
  function renderAgingBar(data){ const total=data.total||0; if(total<=0) return `<div class="text-muted small">—</div>`; const p=(v)=>Math.max(0,Math.round((v/total)*100)); return `<div class="rma-aging"><div class="seg a0" style="width:${p(data.b0_30||0)}%"></div><div class="seg a1" style="width:${p(data.b31_60||0)}%"></div><div class="seg a2" style="width:${p(data.b61_90||0)}%"></div><div class="seg a3" style="width:${p(data.b90p||0)}%"></div></div>`; }
  async function fetchAging(rows){ const customers=rows.map(r=>r.customer); if(!customers.length) return {}; const res=await frappe.call({method:'rma_receivables.aging_api.get_customer_aging_many',args:{customers,as_on:frappe.datetime.get_today()}}); return res.message||{}; }
  async function fetchRows(){ await loadSummary(); renderSkeleton(6); const res=await frappe.call({method:'rma_receivables.ui.list_customers',args:{search:$search.val()||'',limit:100,overdue_only:$overdue.is(':checked')?1:0,customer_group:$cg.val()||''}}); const rows=res.message||[]; const agingMap=await fetchAging(rows); $body.empty();
    if(!rows.length){ $body.append(`<tr><td data-label="Customer" colspan="4" class="text-muted">No rows.</td></tr>`); } else {
      for(const r of rows){ const ag=agingMap[r.customer]||{total:0}; const color=window.__rma_age_class(ag); const amtHTML=`<b class="${color.cls}">${format_currency(r.outstanding||0)}</b> ${color.badge}`;
        const tr = $(`<tr><td data-label="Customer"><b>${frappe.utils.escape_html(r.customer_name||r.customer)}</b><div class="text-muted small">${frappe.utils.escape_html(r.customer)}</div></td>
          <td data-label="Outstanding" class="text-right">${amtHTML}</td><td data-label="Aging">${renderAgingBar(ag)}</td>
          <td data-label="Actions"><div class="dropdown rma-row-menu"><button class="btn btn-sm btn-primary dropdown-toggle" data-toggle="dropdown">Actions</button>
            <ul class="dropdown-menu"><li><a class="dropdown-item rma-send" href="javascript:void(0)">Send</a></li><li><a class="dropdown-item rma-ledger" href="javascript:void(0)">Send + Ledger (FY)</a></li><li><a class="dropdown-item rma-preflight" href="javascript:void(0)">Preflight</a></li><li><a class="dropdown-item rma-followup" href="javascript:void(0)">Add Follow-up</a></li><li class="divider"></li><li><a class="dropdown-item rma-preview" href="javascript:void(0)">Preview Receivables PDF</a></li></ul></div><span class="small text-muted rma-row-status" style="margin-left:8px;"></span></td></tr>`);
        tr.find('.rma-send').on('click', async()=>{ await sendFor(r.customer, null, null, 0, tr); });
        tr.find('.rma-ledger').on('click', async()=>{ const sel=getSelectedRange(); if(!sel){ frappe.msgprint('FY range not ready.'); return; } await sendFor(r.customer, null, {from: sel.from, to: sel.to}, 1, tr); });
        tr.find('.rma-preflight').on('click', async()=>{ await preflightFor(r.customer, frappe.datetime.get_today()); });
        tr.find('.rma-followup').on('click', async()=>{ await addFollowup(r.customer); });
        tr.find('.rma-preview').on('click', async()=>{ await previewReceivables(r.customer, frappe.datetime.get_today()); });
        $body.append(tr);
      }
    }
    $status.text(`${rows.length} row(s)`);
  }
  async function preflightFor(customer, as_on){ const d=new frappe.ui.Dialog({title:`Preflight: ${frappe.utils.escape_html(customer)}`,fields:[{fieldname:'as_on',fieldtype:'Date',label:'As On',default:as_on||frappe.datetime.get_today(),reqd:1},{fieldname:'html',fieldtype:'HTML',options:'<div id="rma-preflight-body" class="small">Running checks…</div>'}],primary_action_label:'Close',primary_action:()=>d.hide()}); d.show();
    try{ const res=await frappe.call({method:'rma_receivables.diagnostics.preflight',args:{customer,as_on:d.get_value('as_on')}}); const m=res.message||{}; const ok=m.ok; const rows=m.checks||[]; const html=[`<ul style="margin:0;padding-left:16px">`]; for(const c of rows){ const ic=c.ok?'✔':'✖'; const col=c.ok?'#16a34a':'#dc2626'; const detail=typeof c.detail==='object'?JSON.stringify(c.detail):(c.detail||''); html.push(`<li><span style="color:${col};font-weight:600">${ic}</span> <b>${frappe.utils.escape_html(c.name)}</b> — <span class="text-muted">${frappe.utils.escape_html(detail)}</span></li>`);} html.push(`</ul><div class="mt-2 ${ok?'text-success':'text-danger'}">${ok? 'All good to send.' : 'Fix the failing checks and retry.'}</div>`); d.get_field('html').$wrapper.html(html.join('')); }catch(e){ d.get_field('html').$wrapper.html(`<div class="text-danger">Error: ${frappe.utils.escape_html(e.message||e)}</div>`); } }
  async function previewReceivables(customer, as_on){ try{ const res=await frappe.call({method:'rma_receivables.pdfs.make_receivables_pdf',args:{customer,as_on:as_on||frappe.datetime.get_today()}}); const f=res.message||{}; if(f.file_url){ window.open(f.file_url,'_blank'); } else { frappe.msgprint('Could not open PDF.'); } }catch(e){ frappe.msgprint({title:'Preview failed',message:e.message||e,indicator:'red'}); } }
  async function sendFor(customer, as_on, range, include_ledger, tr){ const $rowStatus=$(tr).find('.rma-row-status'); $rowStatus.text('Sending...'); try{ const payload={ customer:customer, as_on: as_on||frappe.datetime.get_today(), include_ledger: include_ledger?1:0 }; if(range && range.from && range.to){ payload.from_date=range.from; payload.to_date=range.to; } await frappe.call({method:'rma_receivables.ui.send_for_customer', args: payload}); $rowStatus.text('Sent ✔'); frappe.show_alert({message:`Sent to ${customer}`, indicator: 'green'}); }catch(e){ $rowStatus.text('Failed ✖'); frappe.msgprint({title:'Send failed', message: e.message||e, indicator:'red'}); } }
  async function sendAllVisible(){ const rows=Array.from(document.querySelectorAll('#rma-body tr')); if(!rows.length){ frappe.msgprint('No rows to send for current filter.'); return; }
    let done=0, ok=0, fail=0; const sel=getSelectedRange();
    for(const tr of rows){ const cust = tr.querySelector('td .text-muted.small')?.textContent || tr.querySelector('td b')?.textContent;
      try{ await sendFor(cust, null, sel?{from:sel.from,to:sel.to}:null, sel?1:0, $(tr)); ok++; }catch(e){ fail++; } finally{ done++; } }
    frappe.show_alert({message:`Completed: OK ${ok}, Fail ${fail}`, indicator: fail? 'orange':'green'});
  }
  async function addFollowup(customer){ const d=new frappe.ui.Dialog({title:`Add Follow-up: ${frappe.utils.escape_html(customer)}`,
      fields:[{fieldname:'promise_text',fieldtype:'Data',label:'Promise (eg. "pay on 7 Dec 2025" or "within 7 days")',reqd:1},
              {fieldname:'amount',fieldtype:'Currency',label:'Amount (optional)'},
              {fieldname:'notes',fieldtype:'Small Text',label:'Notes'},
              {fieldname:'assign_to',fieldtype:'Link',options:'User',label:'Assign To'},
              {fieldname:'remind_before_days',fieldtype:'Int',label:'Remind Before (days)',description:'0 = same day',default:0}],
      primary_action_label:'Create',
      primary_action: async (v)=>{ try{ await frappe.call({method:'rma_receivables.followups.create_followup', args:{customer, promise_text:v.promise_text, amount:v.amount, notes:v.notes, assign_to:v.assign_to, remind_before_days:v.remind_before_days}}); frappe.show_alert({message:'Follow-up created', indicator:'green'}); d.hide(); }catch(e){ frappe.msgprint({title:'Failed', message:e.message||e, indicator:'red'}); } }
    }); d.show(); }
  $refresh.on('click', fetchRows); $search.on('input', rmaDebounce(fetchRows, 300)); $sendAll.on('click', sendAllVisible); if($sendAllM.length) $sendAllM.on('click', sendAllVisible);
  frappe.db.get_list('Customer Group',{fields:['name'],limit:500}).then(r=>{ const $cg=$('#rma-cg'); $cg.empty().append(`<option value="">All Groups</option>`); (r||[]).forEach(it=> $cg.append(`<option>${frappe.utils.escape_html(it.name)}</option>`)); });
  (async ()=>{ await loadFY(); await fetchRows(); })();
}
