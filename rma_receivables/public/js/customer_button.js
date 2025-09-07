frappe.ui.form.on('Customer', {
  refresh(frm){
    if (!frm.doc.__islocal) {
      frm.add_custom_button(__('Send WhatsApp Statement'), async function(){
        const d = new frappe.ui.Dialog({
          title: 'Send WhatsApp Statement',
          fields: [
            {fieldname:'as_on', fieldtype:'Date', label:'As On', reqd:1, default: frappe.datetime.get_today()},
            {fieldname:'include_ledger', fieldtype:'Check', label:'Include FY Ledger'},
            {fieldname:'from_date', fieldtype:'Date', label:'From Date', depends_on:'eval:doc.include_ledger'},
            {fieldname:'to_date', fieldtype:'Date', label:'To Date', depends_on:'eval:doc.include_ledger'},
            {fieldname:'html', fieldtype:'HTML', options:'<div class="text-muted small">Run Preflight to check config & phone.</div>'}
          ],
          primary_action_label: 'Send',
          primary_action: async (vals)=>{
            if (vals.include_ledger && (!vals.from_date || !vals.to_date)) {
              frappe.msgprint('Please select From/To dates for FY ledger.'); return;
            }
            try{
              await frappe.call({
                method: 'rma_receivables.ui.send_for_customer',
                args: {
                  customer: frm.doc.name,
                  as_on: vals.as_on,
                  include_ledger: vals.include_ledger ? 1 : 0,
                  from_date: vals.from_date,
                  to_date: vals.to_date
                }
              });
              frappe.show_alert({message:'Sent ✔', indicator:'green'});
              d.hide();
            }catch(e){
              frappe.msgprint({title:'Send failed', message: e.message || e, indicator:'red'});
            }
          }
        });
        d.set_secondary_action_label('Preflight');
        d.set_secondary_action(async ()=>{
          try{
            const res = await frappe.call({method:'rma_receivables.diagnostics.preflight', args:{customer: frm.doc.name, as_on: d.get_value('as_on')}});
            const m = res.message || {}; const ok = m.ok; const rows = m.checks || [];
            const html = ['<ul style="margin:0;padding-left:16px">'];
            rows.forEach(c=>{
              const ic = c.ok ? '✔' : '✖';
              const col = c.ok ? '#16a34a' : '#dc2626';
              const detail = typeof c.detail === 'object' ? JSON.stringify(c.detail) : (c.detail||'');
              html.push(`<li><span style="color:${col};font-weight:600">${ic}</span> <b>${frappe.utils.escape_html(c.name)}</b> — <span class="text-muted">${frappe.utils.escape_html(detail)}</span></li>`);
            });
            html.push(`</ul><div class="mt-2 ${ok?'text-success':'text-danger'}">${ok? 'All good to send.' : 'Fix the failing checks and retry.'}</div>`);
            d.get_field('html').$wrapper.html(html.join(''));
          }catch(e){
            d.get_field('html').$wrapper.html(`<div class="text-danger">Error: ${frappe.utils.escape_html(e.message||e)}</div>`);
          }
        });
        d.show();
      }, __('Actions'));

      frm.add_custom_button(__('Add Follow-up'), async function(){
        const d=new frappe.ui.Dialog({title:'Add Follow-up', fields:[
          {fieldname:'promise_text', fieldtype:'Data', label:'Promise (e.g. "pay on 7 Dec 2025" or "within 7 days")', reqd:1},
          {fieldname:'amount', fieldtype:'Currency', label:'Amount'},
          {fieldname:'notes', fieldtype:'Small Text', label:'Notes'},
          {fieldname:'assign_to', fieldtype:'Link', options:'User', label:'Assign To'},
          {fieldname:'remind_before_days', fieldtype:'Int', label:'Remind Before (days)', default:0}
        ], primary_action_label:'Create', primary_action: async (v)=>{
          try{ await frappe.call({ method:'rma_receivables.followups.create_followup', args:{ customer: frm.doc.name, promise_text: v.promise_text, amount: v.amount, notes: v.notes, assign_to: v.assign_to, remind_before_days: v.remind_before_days } }); frappe.show_alert({message:'Follow-up created', indicator:'green'}); d.hide(); }
          catch(e){ frappe.msgprint({title:'Failed', message:e.message||e, indicator:'red'}); }
        }}); d.show();
      }, __('Actions'));

      frm.add_custom_button(__('View Follow-ups'), async function(){
        const res = await frappe.call({ method:'rma_receivables.followups.list_followups', args:{ customer: frm.doc.name, status: 'Open' }});
        const rows = res.message || [];
        const dlg = new frappe.ui.Dialog({ title:'Open Follow-ups', fields:[{fieldname:'html', fieldtype:'HTML'}], primary_action_label:'Close', primary_action: ()=> dlg.hide() });
        const html = ['<div class="small"><table class="table table-bordered"><thead><tr><th>Due</th><th>Promise</th><th>Amount</th><th>Assigned</th><th>Actions</th></tr></thead><tbody>'];
        rows.forEach(r=>{ html.push(`<tr><td>${r.due_date||''}</td><td>${frappe.utils.escape_html(r.promise_text||'')}</td><td>${format_currency(r.amount||0)}</td><td>${frappe.utils.escape_html(r.assigned_to||'')}</td><td><a href="#" data-n="${r.name}" class="rma-done">Mark Done</a> | <a href="#" data-n="${r.name}" class="rma-sz">Snooze 3d</a></td></tr>`); });
        html.push('</tbody></table></div>');
        dlg.show(); dlg.get_field('html').$wrapper.html(html.join(''));
        dlg.$wrapper.find('a.rma-done').on('click', async (e)=>{ e.preventDefault(); const n=e.currentTarget.getAttribute('data-n'); await frappe.call({ method:'rma_receivables.followups.mark_followup_done', args:{ name:n }}); frappe.show_alert('Marked done'); $(e.currentTarget).closest('tr').remove(); });
        dlg.$wrapper.find('a.rma-sz').on('click', async (e)=>{ e.preventDefault(); const n=e.currentTarget.getAttribute('data-n'); await frappe.call({ method:'rma_receivables.followups.snooze_followup', args:{ name:n, days:3 }}); frappe.show_alert('Snoozed'); });
      }, __('Actions'));
    }
  }
});
