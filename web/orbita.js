'use strict';
(async()=>{
  const $=selector=>document.querySelector(selector);
  const svg=body=>`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  const ideas=[
    {name:'Memoria viva',category:'Cultura',tag:'RECORDAR',icon:svg('<path d="M4 23V8c5-2 8-1 12 2 4-3 7-4 12-2v15c-5-2-8-1-12 2-4-3-7-4-12-2Z"/><path d="M16 10v15M8 12l4 1M20 13l4-1M8 17l4 1M20 18l4-1"/>'),question:'¿Qué historias merecen sobrevivirnos?',description:'Un archivo que no guarda cosas: conecta recuerdos, voces y pequeños rituales para que alguien pueda continuarlos.',stages:['Una historia espera que alguien la escuche.','Una voz encontró a quien la escuche.','Los recuerdos empiezan a conversar.','Una comunidad ya puede recordar en conjunto.']},
    {name:'Tiempo recuperado',category:'Ritmo',tag:'RESPIRAR',icon:svg('<path d="M9 4h14M9 28h14M11 4c0 7 1 8 5 12-4 4-5 5-5 12M21 4c0 7-1 8-5 12 4 4 5 5 5 12M13 23h6M13 9h6"/>'),question:'¿Y si avanzar también fuera detenerse?',description:'Una tecnología que devuelve espacio al día. Menos urgencias inventadas; más tiempo para lo que no admite atajos.',stages:['Todavía hay un minuto que podría ser tuyo.','Aparece una pausa en medio del ruido.','La pausa se convierte en un ritmo propio.','El tiempo vuelve a sentirse habitable.']},
    {name:'Ciudades porosas',category:'Hábitat',tag:'HABITAR',icon:svg('<path d="M5 27V13h9v14M18 27V6h9v21M3 27h26M8 17h3M8 21h3M21 10h3M21 14h3M21 18h3M16 15V9M12 8c0-4 8-4 8 0-1 4-7 4-8 0Z"/>'),question:'¿Puede una ciudad aprender a escuchar?',description:'Barrios que dejan lugar al agua, a otras especies y a encuentros que no necesitan una compra para existir.',stages:['Entre dos edificios cabe otro modo de vivir.','Una esquina se abre a la vida compartida.','Los espacios públicos forman una red de cuidados.','La ciudad deja de ser fondo y empieza a ser hogar.']},
    {name:'Aprender jugando',category:'Asombro',tag:'DESCUBRIR',icon:svg('<path d="m16 3 3.4 8 8.6 1-6.5 6 1.8 9-7.3-4.7L8.7 27l1.8-9L4 12l8.6-1Z"/><path d="M16 10v8M12 14h8"/>'),question:'¿Qué pasa si equivocarse abre una puerta?',description:'Mundos donde aprender consiste en probar, fallar sin castigo y descubrir con otras personas algo que no estaba explicado.',stages:['Una pregunta todavía no encontró su juego.','La curiosidad tiene permiso para empezar.','El error se vuelve parte del descubrimiento.','Aprender ya no es una meta: es una forma de explorar.']},
    {name:'Crear en común',category:'Vínculo',tag:'COMPARTIR',icon:svg('<circle cx="9" cy="9" r="4"/><circle cx="23" cy="9" r="4"/><circle cx="9" cy="23" r="4"/><circle cx="23" cy="23" r="4"/><path d="M13 9h6M9 13v6M23 13v6M13 23h6M12 12l8 8M20 12l-8 8"/>'),question:'¿Y si la mejor idea todavía no es de nadie?',description:'Herramientas que hacen visibles las contribuciones. Una obra abierta donde sumar no exige borrar lo que otra persona dejó.',stages:['Hay una idea esperando compañía.','Dos miradas encuentran una pregunta en común.','La creación empieza a tener muchas manos.','Lo compartido es más grande que la suma de sus partes.']},
    {name:'Tecnología amable',category:'Cuidado',tag:'ACOMPAÑAR',icon:svg('<circle cx="16" cy="16" r="6"/><path d="M16 2v4M16 26v4M2 16h4M26 16h4M6 6l3 3M23 23l3 3M26 6l-3 3M9 23l-3 3M13 17c2 2 4 2 6 0"/>'),question:'¿Puede una herramienta pedir menos de vos?',description:'Sistemas que explican lo que hacen, respetan tus límites y se retiran cuando ya no los necesitás. La calma también es una función.',stages:['Lo útil puede empezar siendo menos invasivo.','Una herramienta aprende a dar un paso atrás.','Las decisiones vuelven a ser comprensibles.','La tecnología acompaña sin ocuparlo todo.']}
  ];
  const positions=[[[28,18],[70,15],[83,49],[68,81],[27,80],[14,48]],[[49,14],[79,28],[81,68],[49,84],[18,68],[18,28]],[[29,18],[69,18],[82,50],[69,81],[29,81],[16,50]]];
  const nodes=$('#idea-nodes'),list=$('#idea-list');
  for(const [index,idea] of ideas.entries()){
    const button=document.createElement('button');button.type='button';button.className='idea-node';button.dataset.idea=index;button.disabled=true;
    button.setAttribute('aria-pressed',String(index===0));button.setAttribute('aria-label',idea.name);
    button.innerHTML=`<span class="node-icon">${idea.icon}<span class="node-growth" hidden></span></span><span class="node-title">${idea.name}</span><span class="node-meta">${idea.tag}</span>`;
    button.style.setProperty('--x',positions[0][index][0]+'%');button.style.setProperty('--y',positions[0][index][1]+'%');
    nodes.append(button);
    const row=document.createElement('button');row.type='button';row.dataset.idea=index;row.textContent=String(index+1).padStart(2,'0')+' / '+idea.name;row.disabled=true;list.append(row);
  }
  const namespace='http://www.w3.org/2000/svg';
  for(let i=0;i<19;i++){
    const line=document.createElementNS(namespace,'ellipse');
    line.setAttribute('cx','120');line.setAttribute('cy',String(39+i*9));line.setAttribute('rx',String(Math.sqrt(Math.max(0,92**2-(81-i*9)**2))));line.setAttribute('ry','13');line.setAttribute('transform','rotate(-22 120 120)');$('#world-lines').append(line);
  }
  for(let i=0;i<7;i++){
    const line=document.createElementNS(namespace,'ellipse');line.setAttribute('cx','120');line.setAttribute('cy','120');line.setAttribute('rx',String(14+i*12));line.setAttribute('ry','92');line.setAttribute('transform','rotate(-22 120 120)');$('#world-lines').append(line);
  }
  for(let i=0;i<6;i++)$('#budget-dots').append(document.createElement('i'));
  for(const [trigger,dialog] of [['#about-open','#about'],['#engine-open','#engine']])$(trigger).addEventListener('click',()=>$(dialog).showModal());
  for(const button of document.querySelectorAll('[data-close]'))button.addEventListener('click',()=>button.closest('dialog').close());
  $('#list-toggle').addEventListener('click',()=>{list.hidden=!list.hidden;$('#list-toggle').setAttribute('aria-expanded',String(!list.hidden));});
  let exports,memory,manifest,noticeTimer;
  const read=(id,index=0)=>memory.getInt32(manifest.layout[id].offset+index*4,true);
  const announce=text=>{$('#notice').textContent=text;$('#notice').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{$('#notice').hidden=true;},3500);};
  const render=()=>{
    const selected=read('selected'),lens=read('lens'),spent=read('spent'),cursor=read('cursor'),length=read('length');
    const levels=ideas.map((_,i)=>read('levels',i)),idea=ideas[selected],level=levels[selected];
    for(const button of document.querySelectorAll('[data-idea]')){
      const i=Number(button.dataset.idea);button.disabled=false;button.setAttribute('aria-pressed',String(i===selected));
      if(button.classList.contains('idea-node')){
        const slot=lens===1?(i-selected+6)%6:i;
        button.style.setProperty('--x',positions[lens][slot][0]+'%');button.style.setProperty('--y',positions[lens][slot][1]+'%');
        button.querySelector('.node-growth').hidden=levels[i]===0;button.querySelector('.node-growth').textContent=levels[i];
      }
    }
    $('#space').dataset.lens=lens;
    document.querySelectorAll('[data-lens]').forEach(button=>{if(button.tagName==='BUTTON')button.setAttribute('aria-pressed',String(Number(button.dataset.lens)===lens));});
    $('#idea-number').textContent=String(selected+1).padStart(2,'0');$('#idea-title').textContent=idea.name;$('#idea-category').textContent=idea.category.toUpperCase();
    $('#detail-icon').innerHTML=idea.icon;$('#idea-question').textContent=idea.question;$('#idea-description').textContent=idea.description;
    $('#idea-level').textContent=level+' / 3';document.querySelectorAll('.growth-track i').forEach((bar,i)=>bar.classList.toggle('filled',i<level));
    $('#invest').disabled=spent===6||level===3;$('#release').disabled=level===0;
    $('#consequence').textContent=idea.stages[level];$('#remaining').textContent=6-spent;
    $('#budget-dots').setAttribute('aria-label',(6-spent)+' semillas disponibles');$('#budget-dots').querySelectorAll('i').forEach((dot,i)=>dot.classList.toggle('used',i<spent));
    $('#undo').disabled=cursor===0;$('#redo').disabled=cursor+1===length;
    $('#history-caption').textContent=length===1?'Todavía no escribiste el primero.':`Composición ${cursor+1} de ${length} · podés cambiar de rumbo.`;
    $('#world-label').textContent=spent===0?'TODO ESTÁ POR CRECER':spent===6?'UN MUNDO EN COMÚN':spent+' SEMILLAS EN ÓRBITA';
    $('#lens-caption').textContent=['No hay un camino correcto. Hay cosas que elegís cuidar.','Una posibilidad en primer plano. El resto sigue ahí.','Las ideas se vuelven más grandes cuando se encuentran.'][lens];
    const active=ideas.map((entry,i)=>({...entry,index:i,level:levels[i]})).filter(entry=>entry.level>0).sort((a,b)=>b.level-a.level||a.index-b.index);
    let title='Todo empieza prestando atención.',description='Seis posibilidades. Seis semillas. Ninguna decisión tiene que ser definitiva.';
    if(active.length===1){title=['','Algo pequeño empieza a cambiar.','Una posibilidad encuentra su lugar.','Lo que cuidás empieza a tener raíces.'][Math.min(3,spent)];description=active[0].stages[active[0].level];}
    if(active.length>=2){title=active.length>=4?'Un futuro no crece en una sola dirección.':spent===6?'La atención se convierte en un mundo.':'Entre dos ideas aparece algo nuevo.';description=`${active[0].name} y ${active[1].name.toLowerCase()} empiezan a compartir una órbita. ${active.length>2?'Otras '+(active.length-2)+' posibilidades amplían el horizonte.':'Todavía hay lugar para imaginar lo que pueden hacer juntas.'}`;}
    if($('#story-title').textContent!==title)$('#story-title').textContent=title;
    $('#story-description').textContent=description;
    $('#connections').replaceChildren();
    for(let i=0;i<6;i++){
      const slot=lens===1?(i-selected+6)%6:i,[x,y]=positions[lens][slot],line=document.createElementNS(namespace,'path');
      line.setAttribute('d',`M390 240 Q${x*8} 240 ${x*8} ${y*4.8}`);line.setAttribute('opacity',levels[i]>0?'1':'.2');line.setAttribute('stroke-width',String(1+levels[i]*.5));$('#connections').append(line);
      if(lens===2&&levels[i]>0){for(let j=i+1;j<6;j++){if(levels[j]===0)continue;const other=positions[2][j],link=document.createElementNS(namespace,'path');link.setAttribute('d',`M${x*8} ${y*4.8} Q390 240 ${other[0]*8} ${other[1]*4.8}`);$('#connections').append(link);}}
    }
  };
  const act=(name,...args)=>{
    if(!exports)return;
    try{exports[name](...args);render();}
    catch{announce('La acción no pudo completarse. Volvé al origen para empezar otra vez.');}
  };
  for(const button of document.querySelectorAll('[data-idea]')){
    button.addEventListener('click',()=>act('orbit.select',Number(button.dataset.idea)));
    button.addEventListener('keydown',event=>{if(!['ArrowRight','ArrowLeft','ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();const next=(Number(button.dataset.idea)+(['ArrowRight','ArrowDown'].includes(event.key)?1:5))%6;act('orbit.select',next);const group=button.closest('#idea-list')||nodes;group.querySelector(`[data-idea="${next}"]`).focus();});
  }
  for(const button of document.querySelectorAll('button[data-lens]'))button.addEventListener('click',()=>act('orbit.lens',Number(button.dataset.lens)));
  $('#invest').addEventListener('click',()=>{act('orbit.adjust',1);});
  $('#release').addEventListener('click',()=>act('orbit.adjust',-1));
  $('#undo').addEventListener('click',()=>act('orbit.undo'));$('#redo').addEventListener('click',()=>act('orbit.redo'));$('#reset').addEventListener('click',()=>{act('orbit.reset');announce('Todo vuelve a ser posible.');});
  document.addEventListener('keydown',event=>{if(!exports||document.querySelector('dialog[open]')||event.altKey||!(event.ctrlKey||event.metaKey)||event.key.toLowerCase()!=='z')return;event.preventDefault();act(event.shiftKey?'orbit.redo':'orbit.undo');});
  try{
    const artifact=JSON.parse($('#orbita-artifact').textContent);manifest=artifact.manifest;
    const bytes=Uint8Array.from(atob(artifact.wasm),char=>char.charCodeAt(0));
    const result=await WebAssembly.instantiate(bytes,{});exports=result.instance.exports;memory=new DataView(exports.memory.buffer);
    $('#engine-state').textContent='PACT → WebAssembly';$('#build-evidence').textContent=manifest.evidence.length+' casos ejecutados sobre WebAssembly; uno por cada acción pública.';
    render();document.body.dataset.ready='true';
  }catch{
    $('#engine-state').textContent='No se pudo iniciar PACT';$('#engine-dot').style.background='#777';
    announce('No se pudo iniciar el núcleo WebAssembly. Recargá la página o consultá el código PACT.');
  }
})();
