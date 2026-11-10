(() => {
 let templates={},bound=null;
 const panel=document.createElement('details');panel.open=true;
 const heading=node('summary','Report template & source excerpts',panel);
 node('label','Template',panel);const select=node('select','',panel);select.id='reportTemplate';
 node('p','Optional: copy exact passages from the selected transcript into the matching sections. Blank sections stay unspecified. These excerpts are not saved; download the report to keep it.',panel);
 const fields=node('div','',panel);fields.id='reportFields';$('report').before(panel);
 function render(){fields.replaceChildren();bound=selected()?{id:selected().id,revision:selected().revision}:null;const spec=templates[select.value];if(!spec)return;for(const [key,label] of Object.entries(spec.fields)){const l=node('label',label,fields);l.htmlFor='reportField_'+key;const input=node('textarea','',fields);input.id='reportField_'+key;input.dataset.field=key;input.maxLength=4000;input.placeholder='Exact source excerpt, or leave blank';}if(bound)node('small','Source revision '+bound.revision,fields);$('reportResult').replaceChildren();}
 select.onchange=render;$('source').addEventListener('change',render);
 // Reset unexported excerpts when refresh changes the selected source/revision.
 const previous=refresh;refresh=async()=>{await previous();const s=selected();if(!s||!bound||s.id!==bound.id||s.revision!==bound.revision)render();};
 $('report').onclick=()=>run($('report'),async()=>{const s=selected();if(!s)throw Error('Save a source first.');if(!bound||bound.id!==s.id||bound.revision!==s.revision){render();throw Error('Source changed. Review report excerpts again.');}const values={};for(const el of fields.querySelectorAll('textarea'))values[el.dataset.field]=el.value;const r=await api('report',{source_id:s.id,revision:bound.revision,template:select.value,fields:values});$('reportResult').replaceChildren();node('pre',r.report,$('reportResult'));const b=node('button','Download Markdown',$('reportResult'));b.onclick=()=>{const url=URL.createObjectURL(new Blob([r.report],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='voicebridge-'+select.value+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};notice('Report built from current source and reviewed tasks.');});
 api('templates').then(t=>{templates=t;for(const [key,spec] of Object.entries(t)){const option=node('option',spec.name,select);option.value=key;}render();}).catch(e=>notice(e.message));
})();
