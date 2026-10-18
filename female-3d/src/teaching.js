// Fixed-view teaching boards. Marks belong to a snapshot, not to 3D anatomy.
const $=s=>document.querySelector(s);
const clone=v=>JSON.parse(JSON.stringify(v));
const uid=()=>Array.from(crypto.getRandomValues(new Uint8Array(12)),n=>n.toString(16).padStart(2,'0')).join('');
const finite=n=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<100000;
const colorOK=s=>typeof s==='string'&&/^#[0-9a-f]{6}$/i.test(s);
const tools=['select','pen','highlighter','arrow','rectangle','ellipse','text','eraser'];
const dist=(p,a,b)=>{const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy);};
function bounds(m){
 if(m.points){const xs=m.points.map(p=>p[0]),ys=m.points.map(p=>p[1]);return [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];}
 if(m.tool==='text'){return [m.x,m.y,m.x+m.text.split('\n').reduce((a,t)=>Math.max(a,t.length),0)*m.fontSize,m.y+m.text.split('\n').length*m.fontSize*1.25];}
 return [Math.min(m.x,m.x2),Math.min(m.y,m.y2),Math.max(m.x,m.x2),Math.max(m.y,m.y2)];
}
function drawMark(ctx,m){
 ctx.save();ctx.strokeStyle=m.color;ctx.fillStyle=m.color;ctx.lineWidth=m.width;ctx.lineCap='round';ctx.lineJoin='round';
 ctx.globalAlpha=m.tool==='highlighter'?.3:1;
 const [x,y,x2,y2]=bounds(m);
 if(m.tool==='text'){
  ctx.font=`${m.fontSize}px "Microsoft YaHei",sans-serif`;ctx.textBaseline='top';
  m.text.split('\n').forEach((line,i)=>ctx.fillText(line,m.x,m.y+i*m.fontSize*1.25));
 }else if(m.points){
  ctx.beginPath();m.points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));
  if(m.points.length===1)ctx.lineTo(m.points[0][0]+.01,m.points[0][1]);ctx.stroke();
 }else if(m.tool==='rectangle'){ctx.strokeRect(x,y,x2-x,y2-y);}
 else if(m.tool==='ellipse'){ctx.beginPath();ctx.ellipse((x+x2)/2,(y+y2)/2,Math.max(.1,(x2-x)/2),Math.max(.1,(y2-y)/2),0,0,Math.PI*2);ctx.stroke();}
 else if(m.tool==='arrow'){
  ctx.beginPath();ctx.moveTo(m.x,m.y);ctx.lineTo(m.x2,m.y2);ctx.stroke();
  const a=Math.atan2(m.y2-m.y,m.x2-m.x),l=Math.max(12,m.width*4);
  ctx.beginPath();ctx.moveTo(m.x2,m.y2);ctx.lineTo(m.x2-l*Math.cos(a-.4),m.y2-l*Math.sin(a-.4));ctx.lineTo(m.x2-l*Math.cos(a+.4),m.y2-l*Math.sin(a+.4));ctx.closePath();ctx.fill();
 }
 ctx.restore();
}
function excalidrawScene(board){
 const common=(type,x,y,width,height,mark={})=>({id:uid(),type,x,y,width:Math.max(.1,width),height:Math.max(.1,height),angle:0,strokeColor:mark.color||'#1e1e1e',backgroundColor:'transparent',fillStyle:'solid',strokeWidth:mark.width||1,strokeStyle:'solid',roughness:0,opacity:mark.tool==='highlighter'?30:100,groupIds:[],frameId:null,roundness:null,seed:Math.floor(Math.random()*2e9),version:1,versionNonce:Math.floor(Math.random()*2e9),isDeleted:false,boundElements:null,updated:Date.now(),link:null,locked:false});
 const fileId=uid()+uid().slice(0,16);
 const image={...common('image',0,0,board.width,board.height),fileId,scale:[1,1],status:'saved',crop:null,locked:true};
 const elements=[image];
 for(const m of board.marks){
  const [x,y,x2,y2]=bounds(m);
  if(m.points){elements.push({...common('freedraw',x,y,x2-x,y2-y,m),points:m.points.map(p=>[p[0]-x,p[1]-y]),pressures:[],simulatePressure:true,lastCommittedPoint:null});}
  else if(m.tool==='arrow'){elements.push({...common('arrow',m.x,m.y,Math.abs(m.x2-m.x),Math.abs(m.y2-m.y),m),points:[[0,0],[m.x2-m.x,m.y2-m.y]],startBinding:null,endBinding:null,startArrowhead:null,endArrowhead:'arrow',elbowed:false});}
  else if(m.tool==='text'){
   const ctx=document.createElement('canvas').getContext('2d');ctx.font=`${m.fontSize}px Arial,sans-serif`;
   const width=Math.max(...m.text.split('\n').map(l=>ctx.measureText(l).width),1);
   elements.push({...common('text',m.x,m.y,width,m.text.split('\n').length*m.fontSize*1.25,m),text:m.text,originalText:m.text,fontSize:m.fontSize,fontFamily:2,textAlign:'left',verticalAlign:'top',containerId:null,lineHeight:1.25,autoResize:true,baseline:m.fontSize});
  }else elements.push(common(m.tool,x,y,x2-x,y2-y,m));
 }
 return {type:'excalidraw',version:2,source:'https://github.com/chenjie1977z-del/sxdw20261018',elements,appState:{viewBackgroundColor:'#f5f4ef',gridSize:null},files:{[fileId]:{id:fileId,mimeType:'image/png',dataURL:board.background,created:Date.now(),lastRetrieved:Date.now()}}};
}
function validateProject(value){
 if(value?.format!=='female-3d-teaching'||value.version!==1||!Array.isArray(value.boards)||value.boards.length<1||value.boards.length>20)throw Error('不是受支持的教学课件文件。');
 const seen=new Set();
 for(const b of value.boards){
  if(typeof b.id!=='string'||seen.has(b.id)||typeof b.name!=='string'||b.name.length>100||!finite(b.width)||!finite(b.height)||b.width<100||b.height<100||b.width>5000||b.height>5000)throw Error('课件页面信息无效。');seen.add(b.id);
  if(typeof b.background!=='string'||b.background.length>12e6||!/^data:image\/png;base64,[a-z0-9+/]+=*$/i.test(b.background))throw Error('课件背景图无效。');
  const head=Uint8Array.from(atob(b.background.split(',')[1].slice(0,44)),c=>c.charCodeAt(0));
  if(head.length<24||head[0]!==137||head[1]!==80)throw Error('背景不是 PNG。');
  const dv=new DataView(head.buffer);if(dv.getUint32(16)>8192||dv.getUint32(20)>8192)throw Error('背景图片尺寸过大。');
  if(!Array.isArray(b.marks)||b.marks.length>1000)throw Error('标注数量超过限制。');
  for(const m of b.marks){
   if(!tools.includes(m.tool)||['select','eraser'].includes(m.tool)||typeof m.id!=='string'||!colorOK(m.color)||!finite(m.width)||m.width<1||m.width>50)throw Error('标注格式无效。');
   if(['pen','highlighter'].includes(m.tool)){
    if(!Array.isArray(m.points)||m.points.length<1||m.points.length>10000||m.points.some(p=>!Array.isArray(p)||p.length!==2||!p.every(finite)))throw Error('笔迹坐标无效。');
   }else if(!finite(m.x)||!finite(m.y))throw Error('标注位置无效。');
   if(m.tool==='text'&&(typeof m.text!=='string'||m.text.length>2000||!finite(m.fontSize)||m.fontSize<10||m.fontSize>100))throw Error('文字格式无效。');
   if(['arrow','rectangle','ellipse'].includes(m.tool)&&(!finite(m.x2)||!finite(m.y2)))throw Error('形状坐标无效。');
  }
 }
 return clone(value.boards);
}
export function createTeachingTools(api){
 const canvas=$('#annotation-canvas'),ctx=canvas.getContext('2d');
 let active=false,boards=[],index=-1,image=null,tool='pen',draft=null,action=null,selection=null,frame={x:0,y:0,scale:1},busy=false;
 const history=new Map();
 const current=()=>boards[index];
 const stack=()=>{const id=current().id;if(!history.has(id))history.set(id,{undo:[],redo:[]});return history.get(id);};
 const setButtons=()=>{
  $('#undo-mark').disabled=!current()||!stack().undo.length;$('#redo-mark').disabled=!current()||!stack().redo.length;
  $('#resume-annotations').disabled=!boards.length;
  $('#annotation-pages').replaceChildren(...boards.map((b,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. ${b.name}`;o.selected=i===index;return o;}));
 };
 function remember(){const h=stack();h.undo.push(clone(current().marks));if(h.undo.length>60)h.undo.shift();h.redo=[];}
 function changed(){selection=null;setButtons();render();}
 function fit(){
  const rect=canvas.getBoundingClientRect(),b=current();if(!b)return;
  frame.scale=Math.min(rect.width/b.width,rect.height/b.height);frame.x=(rect.width-b.width*frame.scale)/2;frame.y=(rect.height-b.height*frame.scale)/2;
 }
 function render(){
  const rect=canvas.getBoundingClientRect();if(!active||!rect.width||!rect.height||!current())return;
  const ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(rect.width*ratio);canvas.height=Math.round(rect.height*ratio);ctx.setTransform(ratio,0,0,ratio,0,0);
  ctx.fillStyle='#e8ece5';ctx.fillRect(0,0,rect.width,rect.height);fit();
  ctx.translate(frame.x,frame.y);ctx.scale(frame.scale,frame.scale);
  const b=current();if(image)ctx.drawImage(image,0,0,b.width,b.height);
  for(const m of b.marks)drawMark(ctx,m);if(draft)drawMark(ctx,draft);
  if(selection){const m=b.marks.find(m=>m.id===selection);if(m){const [x,y,x2,y2]=bounds(m);ctx.strokeStyle='#19796b';ctx.lineWidth=1/frame.scale;ctx.setLineDash([5/frame.scale,4/frame.scale]);ctx.strokeRect(x-5,y-5,x2-x+10,y2-y+10);ctx.setLineDash([]);}}
 }
 const resizeObserver=new ResizeObserver(()=>{if(active)render();});resizeObserver.observe(canvas.parentElement);
 async function openBoard(i){
  const next=boards[i];if(!next)return;
  const nextImage=await new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error('课件图片无法读取。'));im.src=next.background;});
  index=i;image=nextImage;selection=null;draft=null;action=null;active=true;
  $('.stage').classList.add('teaching');$('#annotation-tools').hidden=false;$('#model-controls').hidden=true;
  $('#return-3d').hidden=false;$('#annotate-view').hidden=true;canvas.style.display='block';$('#annotation-help').textContent='当前为固定视角标注。返回 3D 后可转动模型，再新建另一页。';
  api.setActive(true);setButtons();render();
 }
 function leave(){active=false;draft=null;action=null;selection=null;canvas.style.display='none';$('.stage').classList.remove('teaching');$('#annotation-tools').hidden=true;$('#model-controls').hidden=false;$('#return-3d').hidden=true;$('#annotate-view').hidden=false;api.setActive(false);setButtons();}
 async function createBoard(){
  if(busy)return;if(boards.length>=20){api.message('每份课件最多 20 页，请先保存。');return;}
  busy=true;$('#annotate-view').disabled=true;api.message('正在准备 4K 视角快照…');
  try{
   await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
   const shot=api.capture();const width=1000,height=1000*shot.height/shot.width;
   boards.push({id:uid(),name:api.getViewName(),width,height,background:shot.dataURL,marks:[],view:api.getView()});await openBoard(boards.length-1);
  }catch(e){api.message(e.message);}finally{busy=false;$('#annotate-view').disabled=false;}
 }
 $('#annotate-view').onclick=createBoard;
 $('#resume-annotations').onclick=()=>openBoard(index<0?0:index).catch(e=>api.message(e.message));
 $('#return-3d').onclick=leave;
 $('#annotation-pages').onchange=e=>openBoard(Number(e.target.value)).catch(e=>api.message(e.message));
 function setTool(name){tool=name;selection=null;canvas.style.cursor=name==='text'?'text':name==='select'?'default':'crosshair';document.querySelectorAll('[data-annotation-tool]').forEach(b=>b.classList.toggle('active',b.dataset.annotationTool===name));render();}
 document.querySelectorAll('[data-annotation-tool]').forEach(b=>b.onclick=()=>setTool(b.dataset.annotationTool));
 function point(e){const r=canvas.getBoundingClientRect();const p=[(e.clientX-r.left-frame.x)/frame.scale,(e.clientY-r.top-frame.y)/frame.scale];return p[0]>=0&&p[1]>=0&&p[0]<=current().width&&p[1]<=current().height?p:null;}
 function hit(p){
  for(let i=current().marks.length-1;i>=0;i--){const m=current().marks[i],pad=Math.max(7,m.width);
   if(m.points){if(m.points.length===1&&Math.hypot(p[0]-m.points[0][0],p[1]-m.points[0][1])<pad)return i;for(let j=1;j<m.points.length;j++)if(dist(p,m.points[j-1],m.points[j])<pad)return i;}
   else if(m.tool==='arrow'){if(dist(p,[m.x,m.y],[m.x2,m.y2])<pad)return i;}
   else {const [x,y,x2,y2]=bounds(m);if(p[0]>=x-pad&&p[0]<=x2+pad&&p[1]>=y-pad&&p[1]<=y2+pad)return i;}
  }return -1;
 }
 function erase(p){const i=hit(p);if(i>=0){remember();current().marks.splice(i,1);changed();}}
 canvas.addEventListener('pointerdown',e=>{
  if(!active||e.button!==0)return;const p=point(e);if(!p)return;e.preventDefault();canvas.setPointerCapture(e.pointerId);
  if(tool==='eraser'){erase(p);action={type:'erase'};return;}
  if(tool==='select'){const i=hit(p);selection=i>=0?current().marks[i].id:null;action=i>=0?{type:'move',i,start:p,original:clone(current().marks[i]),remembered:false}:null;render();return;}
  if(current().marks.length>=1000){api.message('本页已达到 1000 条标注，请新建一页。');return;}
  const m={id:uid(),tool,color:$('#annotation-color').value,width:tool==='highlighter'?18:Number($('#annotation-width').value)};
  if(tool==='text'){
   const text=$('#annotation-text').value.trim();if(!text){api.message('请先在文字框输入内容，再点击图像放置。');$('#annotation-text').focus();return;}
   remember();current().marks.push({...m,x:p[0],y:p[1],text,fontSize:Number($('#annotation-font').value)});changed();return;
  }
  draft=['pen','highlighter'].includes(tool)?{...m,points:[p]}:{...m,x:p[0],y:p[1],x2:p[0],y2:p[1]};action={type:'draw'};render();
 });
 canvas.addEventListener('pointermove',e=>{
  if(!active||!action)return;const p=point(e);if(!p)return;
  if(action.type==='erase'){erase(p);return;}
  if(action.type==='move'){
   const dx=p[0]-action.start[0],dy=p[1]-action.start[1];if(!action.remembered&&Math.hypot(dx,dy)<1)return;
   if(!action.remembered){remember();action.remembered=true;}
   const m=clone(action.original);if(m.points)m.points=m.points.map(q=>[q[0]+dx,q[1]+dy]);else {m.x+=dx;m.y+=dy;if(m.x2!==undefined){m.x2+=dx;m.y2+=dy;}}
   current().marks[action.i]=m;render();return;
  }
  if(draft?.points){if(draft.points.length<10000)draft.points.push(p);}else if(draft){draft.x2=p[0];draft.y2=p[1];}render();
 });
 function finish(){
  if(action?.type==='draw'&&draft){const [x,y,x2,y2]=bounds(draft);if(draft.points||Math.hypot(x2-x,y2-y)>2){remember();current().marks.push(draft);}}
  draft=null;action=null;setButtons();render();
 }
 canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',finish);
 $('#undo-mark').onclick=()=>{const h=stack();if(h.undo.length){h.redo.push(clone(current().marks));current().marks=h.undo.pop();changed();}};
 $('#redo-mark').onclick=()=>{const h=stack();if(h.redo.length){h.undo.push(clone(current().marks));current().marks=h.redo.pop();changed();}};
 $('#clear-marks').onclick=()=>{if(current().marks.length){remember();current().marks=[];changed();}};
 document.addEventListener('keydown',e=>{
  if(!active||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();$(e.shiftKey?'#redo-mark':'#undo-mark').click();}
  else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();$('#redo-mark').click();}
  else if(['Delete','Backspace'].includes(e.key)&&selection){e.preventDefault();remember();current().marks=current().marks.filter(m=>m.id!==selection);changed();}
  else if(!e.ctrlKey&&!e.metaKey){const key={v:'select',p:'pen',h:'highlighter',a:'arrow',r:'rectangle',o:'ellipse',t:'text',e:'eraser'}[e.key.toLowerCase()];if(key){e.preventDefault();setTool(key);}}
 });
 function download(blob,name){const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),10000);}
 $('#export-marked').onclick=()=>{
  if(!current()||!image)return;const b=current(),out=document.createElement('canvas');out.width=4096;out.height=Math.round(4096*b.height/b.width);
  const c=out.getContext('2d');c.scale(out.width/b.width,out.height/b.height);c.drawImage(image,0,0,b.width,b.height);b.marks.forEach(m=>drawMark(c,m));
  out.toBlob(blob=>{if(blob)download(blob,'female-teaching-4K.png');else api.message('图片导出失败。');},'image/png');
 };
 $('#export-excalidraw').onclick=()=>download(new Blob([JSON.stringify(excalidrawScene(current()))],{type:'application/json'}),'female-teaching.excalidraw');
 $('#save-lessons').onclick=()=>{if(!boards.length){api.message('请先建立一页标注。');return;}download(new Blob([JSON.stringify({format:'female-3d-teaching',version:1,boards})],{type:'application/json'}),'female-teaching-project.json');};
 $('#load-lessons').onclick=()=>$('#lesson-file').click();
 $('#lesson-file').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
   if(file.size>60e6)throw Error('课件超过 60 MB，请拆分保存。');
   const next=validateProject(JSON.parse(await file.text()));
   if(boards.length+next.length>20)throw Error('导入后将超过 20 页，请在新窗口打开查看器后导入。');
   // Merge rather than overwrite existing work, assigning fresh IDs to imported pages.
   const start=boards.length;next.forEach(b=>{b.id=uid();boards.push(b);});await openBoard(start);api.message(`已导入 ${next.length} 页，原有课件页已保留。`);
  }catch(error){api.message(error instanceof SyntaxError?'文件不是有效的 JSON 课件。':error.message);}finally{e.target.value='';}
 };
 setTool('pen');setButtons();
 return {get active(){return active;},get boardCount(){return boards.length;},get currentBoard(){return current();},get tool(){return tool;},leave,createBoard,excalidrawScene:()=>excalidrawScene(current())};
}
