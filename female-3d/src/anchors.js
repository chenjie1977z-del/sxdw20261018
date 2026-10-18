import * as THREE from 'three';
import { computeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';

const $=s=>document.querySelector(s),copy=x=>JSON.parse(JSON.stringify(x));
const uid=()=>crypto.getRandomValues(new Uint32Array(3)).join('-');
const colorOK=x=>typeof x==='string'&&/^#[0-9a-f]{6}$/i.test(x);
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const vec=a=>new THREE.Vector3(...a);

export function createSurfaceAnnotations(api){
 const {scene,body,canvas}=api,geometry=body.geometry;
 // Indirect construction preserves source triangle order in saved barycentric anchors.
 computeBoundsTree.call(geometry,{indirect:true});body.raycast=acceleratedRaycast;
 const positions=geometry.attributes.position,index=geometry.index;
 let hash=2166136261;const bytes=new Uint8Array(positions.array.buffer,positions.array.byteOffset,positions.array.byteLength);
 for(const array of [bytes,new Uint8Array(index.array.buffer,index.array.byteOffset,index.array.byteLength)])for(const b of array)hash=Math.imul(hash^b,16777619);
 const modelKey=`female-surface-${positions.count}-${index.count}-${(hash>>>0).toString(16)}`;
 const root=new THREE.Group();root.name='Surface_Annotations';scene.add(root);
 const pendingRoot=new THREE.Group();root.add(pendingRoot);
 const ray=new THREE.Raycaster();ray.firstHitOnly=true;
 let marks=[],selected=null,tool='rotate',suspended=false,pending=null,drag=null,draft=null,undo=[],redo=[],dirty=true,lastCamera='',lastBody='';
 const groups=new Map(),snap=()=>copy(marks),current=()=>marks.find(m=>m.id===selected);
 function remember(){undo.push(snap());if(undo.length>50)undo.shift();redo=[];}
 function controls(enabled){api.getControls().enabled=enabled&&!suspended;}
 function pointFromAnchor(a){
  const p=new THREE.Vector3(),n=new THREE.Vector3(),normals=geometry.attributes.normal;
  for(let i=0;i<3;i++){const v=index.getX(a.face*3+i);p.addScaledVector(new THREE.Vector3().fromBufferAttribute(positions,v),a.bary[i]);n.addScaledVector(new THREE.Vector3().fromBufferAttribute(normals,v),a.bary[i]);}
  body.updateWorldMatrix(true,false);p.applyMatrix4(body.matrixWorld);n.transformDirection(body.matrixWorld).normalize();return {point:p,normal:n};
 }
 function anchorAtLocal(p,face){
  const vertices=[0,1,2].map(i=>new THREE.Vector3().fromBufferAttribute(positions,index.getX(face*3+i)));
  const bary=new THREE.Triangle(...vertices).getBarycoord(p,new THREE.Vector3());
  return {face,bary:bary.toArray()};
 }
 function fromHit(hit){return anchorAtLocal(body.worldToLocal(hit.point.clone()),hit.faceIndex);}
 function nearest(world){
  const local=body.worldToLocal(world.clone()),hit=geometry.boundsTree.closestPointToPoint(local);
  return {anchor:anchorAtLocal(hit.point,hit.faceIndex),distance:hit.distance};
 }
 function surfaceAt(clientX,clientY){
  const rect=canvas.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((clientX-rect.left)/rect.width*2-1,-(clientY-rect.top)/rect.height*2+1),api.getCamera());
  return ray.intersectObject(body,false)[0]||null;
 }
 const offset=a=>{const p=pointFromAnchor(a);return p.point.addScaledVector(p.normal,.0015);};
 function dispose(group){group.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose();}});group.removeFromParent();}
 function basic(color){return new THREE.MeshBasicMaterial({color,depthTest:$('#anchor-occlude').checked,depthWrite:false,toneMapped:false});}
 function sphere(group,p,r,color,id,part){const haloMat=basic('#10232c');haloMat.side=THREE.FrontSide;const halo=new THREE.Mesh(new THREE.SphereGeometry(r*1.35,12,8),haloMat);halo.position.copy(p);halo.userData={id,part};halo.renderOrder=1;group.add(halo);const o=new THREE.Mesh(new THREE.SphereGeometry(r,12,8),basic(color));o.position.copy(p);o.userData={id,part};o.renderOrder=2;group.add(o);return o;}
 function tube(group,points,r,color,id,part='body'){
  if(points.length<2||points.every(p=>p.distanceToSquared(points[0])<1e-12))return;
  const curve=new THREE.CatmullRomCurve3(points,false,'centripetal');
  const segments=Math.max(12,Math.min(160,points.length*2)),haloMat=basic('#10232c');haloMat.side=THREE.FrontSide;const halo=new THREE.Mesh(new THREE.TubeGeometry(curve,segments,r*1.8,6,false),haloMat);halo.userData={id,part};halo.renderOrder=1;group.add(halo);
  const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,segments,r,6,false),basic(color));mesh.userData={id,part};mesh.renderOrder=2;group.add(mesh);return curve;
 }
 function labelTexture(text,color){
  const c=document.createElement('canvas'),ctx=c.getContext('2d');const lines=text.match(/.{1,20}/gu)||[''];
  ctx.font='52px "Microsoft YaHei",sans-serif';const width=Math.ceil(Math.max(...lines.map(l=>ctx.measureText(l).width),32))+40;
  c.width=width;c.height=lines.length*66+24;
  ctx.fillStyle='rgba(18,31,38,.90)';ctx.beginPath();ctx.roundRect(2,2,c.width-4,c.height-4,14);ctx.fill();
  ctx.strokeStyle='#e5ecef';ctx.lineWidth=3;ctx.stroke();ctx.fillStyle=color;ctx.font='52px "Microsoft YaHei",sans-serif';ctx.textBaseline='top';
  lines.forEach((l,i)=>ctx.fillText(l,20,14+i*66));const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;tex.userData.lines=lines.length;return tex;
 }
 function curvePoints(m){
  const a=pointFromAnchor(m.anchors[0]),b=pointFromAnchor(m.anchors[1]),start=offset(m.anchors[0]),end=offset(m.anchors[1]);
  const chord=end.clone().sub(start),normal=a.normal.clone().add(b.normal).normalize();if(normal.lengthSq()<.1)normal.copy(a.normal);
  let sideways=chord.clone().cross(normal).normalize();if(sideways.lengthSq()<.1)sideways.set(1,0,0);
  const middle=start.clone().add(end).multiplyScalar(.5).addScaledVector(sideways,chord.length()*m.bend*2);
  if(!m.follow)middle.addScaledVector(normal,Math.abs(m.bend)*chord.length()*.45);
  const curve=new THREE.QuadraticBezierCurve3(start,middle,end),raw=curve.getPoints(64);
  if(!m.follow)return {points:raw,fallback:false};
  let failed=false;const projected=raw.map(p=>{const h=nearest(p);if(h.distance>.06)failed=true;return offset(h.anchor);});
  for(let i=1;i<projected.length;i++)if(projected[i].distanceTo(projected[i-1])>Math.max(.025,chord.length()/8))failed=true;
  return {points:failed?raw:projected,fallback:failed};
 }
 function rebuild(){
  for(const g of groups.values())dispose(g);groups.clear();
  for(const m of marks){
   const g=new THREE.Group();g.name=`Annotation_${m.id}`;root.add(g);groups.set(m.id,g);const r=.0009*m.size;
   let pts=m.kind==='curve'?curvePoints(m).points:m.anchors.map(offset);
   if(m.closed&&pts.length>2)pts=[...pts,pts[0].clone()];
   if(m.kind==='curve'){
    const result=curvePoints(m);pts=result.points;m.fallback=result.fallback;
    const curve=tube(g,pts,r,m.color,m.id);
    if(curve&&m.ticks){
     curve.arcLengthDivisions=512;curve.updateArcLengths();
     for(let j=1;j<m.divisions;j++){
      const t=j/m.divisions,p=curve.getPointAt(t),tangent=curve.getTangentAt(t),n=pointFromAnchor(nearest(p).anchor).normal;
      let across=tangent.clone().cross(n).normalize();if(across.lengthSq()<.1)across.set(0,1,0);
      tube(g,[p.clone().addScaledVector(across,-.004*m.size),p.clone().addScaledVector(across,.004*m.size)],r*.8,m.color,m.id);
      sphere(g,p,.0017*m.size,m.color,m.id,'body');
     }
    }
    if(curve&&m.arrow){
     const tangent=curve.getTangentAt(1),tip=pts.at(-1),cone=new THREE.Mesh(new THREE.ConeGeometry(.0035*m.size,.010*m.size,12),basic(m.color));
     cone.position.copy(tip).addScaledVector(tangent,-.005*m.size);cone.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),tangent);cone.userData={id:m.id,part:'body'};g.add(cone);
    }
   }else if(m.kind==='pen')tube(g,pts,r,m.color,m.id);
   const handleAnchors=m.kind==='pen'?[m.anchors[0],m.anchors.at(-1)]:m.anchors;
   handleAnchors.forEach((a,i)=>sphere(g,offset(a),m.kind==='label'?.0035*m.size:(m.id===selected?.005:.0028)*m.size,m.id===selected?'#46cde0':m.color,m.id,`anchor:${m.kind==='pen'?(i===0?0:m.anchors.length-1):i}`));
   if(m.text){
    const origin=m.kind==='label'?pts[0]:pts[Math.floor(pts.length/2)],labelPos=origin.clone().add(vec(m.labelOffset));
    tube(g,[origin,labelPos],r*.60,m.color,m.id,'label');
    // Occlusion is decided at surface anchors; keep the full caption readable.
    const map=labelTexture(m.text,m.color),sprite=new THREE.Sprite(new THREE.SpriteMaterial({map,depthTest:false,depthWrite:false,toneMapped:false}));sprite.renderOrder=3;
    sprite.position.copy(labelPos);sprite.userData={id:m.id,part:'label',label:true,size:m.size,lines:map.userData.lines,aspect:map.image.width/map.image.height};g.add(sprite);
   }
  }
  dirty=true;sync();
 }
 function defaults(kind,anchors){
  const camera=api.getCamera(),p=pointFromAnchor(anchors[0]).point,rect=canvas.getBoundingClientRect();
  const units=camera.isOrthographicCamera?(camera.top-camera.bottom)/(camera.zoom*rect.height):2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*camera.position.distanceTo(p)/rect.height;
  const sign=p.clone().project(camera).x<0?-1:1;
  const labelOffset=new THREE.Vector3(1,0,0).applyQuaternion(camera.quaternion).multiplyScalar(units*140*sign).add(new THREE.Vector3(0,1,0).applyQuaternion(camera.quaternion).multiplyScalar(units*45)).toArray();
  return {id:uid(),kind,anchors,text:$('#anchor-text').value.trim()||(kind==='label'?`标注 ${marks.length+1}`:''),color:$('#anchor-color').value,size:Number($('#anchor-size').value),bend:Number($('#anchor-bend').value),ticks:$('#anchor-ticks').checked,divisions:Number($('#anchor-divisions').value),follow:$('#anchor-follow').checked,arrow:$('#anchor-arrow').checked,closed:$('#anchor-closed').checked,visible:true,labelOffset};
 }
 function sync(){
  const m=current(),list=$('#anchor-list');list.replaceChildren(new Option('选择已有三维标注',''));
  for(const item of marks)list.add(new Option(`${item.visible?'':'[隐藏] '}${item.text||({label:'定位标注',curve:'两点连线',pen:'体表描线'}[item.kind])}`,item.id));
  list.value=selected||'';$('#anchor-count').textContent=`${marks.length} 条三维标注${pending?' · 请选第二个端点':''}`;
  $('#anchor-undo').disabled=!undo.length;$('#anchor-redo').disabled=!redo.length;$('#anchor-delete').disabled=!m;
  $('#anchor-bend-value').textContent=Number($('#anchor-bend').value).toFixed(2);$('#anchor-size-value').textContent=Number($('#anchor-size').value).toFixed(1);
  $('#anchor-warning').textContent=m?.fallback?'两点之间跨越空隙，当前显示为空间曲线；两个端点仍贴肤。':'';
  if(m){$('#anchor-text').value=m.text;$('#anchor-color').value=m.color;$('#anchor-size').value=m.size;$('#anchor-bend').value=m.bend;$('#anchor-ticks').checked=m.ticks;$('#anchor-divisions').value=m.divisions;$('#anchor-follow').checked=m.follow;$('#anchor-arrow').checked=m.arrow;$('#anchor-closed').checked=m.closed;$('#anchor-item-visible').checked=m.visible;$('#anchor-size-value').textContent=m.size.toFixed(1);$('#anchor-bend-value').textContent=m.bend.toFixed(2);}
 }
 function setTool(next){
  tool=next;pending=null;draft=null;drag=null;disposePending();controls(true);
  if(next!=='rotate')api.stopRotate();
  if(['label','curve','pen'].includes(next))selected=null;
  document.querySelectorAll('[data-anchor-tool]').forEach(b=>b.classList.toggle('active',b.dataset.anchorTool===next));
  canvas.style.cursor=next==='rotate'?'':next==='select'?'default':'crosshair';rebuild();
 }
 function disposePending(){for(const child of [...pendingRoot.children])dispose(child);}
 function select(id){selected=marks.some(m=>m.id===id)?id:null;rebuild();}
 function add(m){if(marks.length>=120){api.message('最多 120 条三维标注，请先保存并拆分课件。');return false;}remember();marks.push(m);selected=m.id;setTool('select');return true;}
 function pointerRay(e){const r=canvas.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),api.getCamera());}
 function pick(e){if(!root.visible)return null;pointerRay(e);const hits=ray.intersectObjects([...groups.values()].filter(g=>g.visible),true);return hits.find(h=>h.object.userData.part?.startsWith('anchor:'))||hits[0]||null;}
 function changed(){rebuild();}
 canvas.addEventListener('pointerdown',e=>{
  if(suspended||tool==='rotate'||e.button!==0)return;
  e.preventDefault();e.stopImmediatePropagation();canvas.setPointerCapture(e.pointerId);controls(false);api.stopRotate();
  if(tool==='select'){
   const hit=pick(e);if(!hit){selected=null;rebuild();return;}
   selected=hit.object.userData.id;const m=current();pointerRay(e);
   const plane=new THREE.Plane().setFromNormalAndCoplanarPoint(api.getCamera().getWorldDirection(new THREE.Vector3()),hit.point);
   const at=ray.ray.intersectPlane(plane,new THREE.Vector3());
   drag={id:m.id,part:e.shiftKey?'body':hit.object.userData.part,original:copy(m),plane,at,hitStart:surfaceAt(e.clientX,e.clientY)?.point.clone(),remembered:false,x:e.clientX,y:e.clientY};rebuild();return;
  }
  const hit=surfaceAt(e.clientX,e.clientY);if(!hit){api.message('请点在人体表面。');return;}
  if(tool==='pen')draft={anchors:[fromHit(hit)],x:e.clientX,y:e.clientY};
  else drag={create:tool,anchor:fromHit(hit),x:e.clientX,y:e.clientY};
 },true);
 canvas.addEventListener('pointermove',e=>{
  if(suspended)return;
  if(draft){
   const hit=surfaceAt(e.clientX,e.clientY);if(!hit)return;const a=fromHit(hit);
   if(offset(a).distanceTo(offset(draft.anchors.at(-1)))>.002&&draft.anchors.length<512){draft.anchors.push(a);disposePending();tube(pendingRoot,draft.anchors.map(offset),.001,$('#anchor-color').value,'draft');}return;
  }
  if(!drag||drag.create||Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<3)return;
  const m=current();if(!m)return;
  if(!drag.remembered){remember();drag.remembered=true;}
  if(drag.part==='label'){
   pointerRay(e);const p=ray.ray.intersectPlane(drag.plane,new THREE.Vector3());if(p&&drag.at){const delta=p.sub(drag.at);m.labelOffset=vec(drag.original.labelOffset).add(delta).clampScalar(-3,3).toArray();}
  }else{
   const hit=surfaceAt(e.clientX,e.clientY);
   if(drag.part.startsWith('anchor:')){if(hit)m.anchors[Number(drag.part.split(':')[1])]=fromHit(hit);}
   else{pointerRay(e);const planePoint=ray.ray.intersectPlane(drag.plane,new THREE.Vector3());const delta=drag.hitStart&&hit?hit.point.clone().sub(drag.hitStart):planePoint?.sub(drag.at);if(delta)m.anchors=drag.original.anchors.map(a=>nearest(pointFromAnchor(a).point.add(delta)).anchor);}
  }
  changed();
 },true);
 function finish(e,cancelled=false){
  if(suspended)return;
  if(draft){if(!cancelled&&draft.anchors.length>1)add(defaults('pen',draft.anchors));draft=null;disposePending();}
  if(drag?.create&&!cancelled&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<8){
   if(drag.create==='label')add(defaults('label',[drag.anchor]));
   else if(pending){if(offset(pending).distanceTo(offset(drag.anchor))>.002){add(defaults('curve',[pending,drag.anchor]));pending=null;disposePending();}}
   else{pending=drag.anchor;disposePending();sphere(pendingRoot,offset(pending),.005,$('#anchor-color').value,'draft','body');}
  }
  drag=null;controls(true);sync();
 }
 canvas.addEventListener('pointerup',e=>finish(e),true);
 canvas.addEventListener('pointercancel',e=>finish(e,true),true);
 canvas.addEventListener('lostpointercapture',e=>finish(e,true),true);
 canvas.addEventListener('wheel',e=>{
  if(!suspended&&e.altKey&&current()){e.preventDefault();e.stopImmediatePropagation();remember();current().size=THREE.MathUtils.clamp(current().size*(e.deltaY<0?1.1:.9),.3,3);rebuild();}
 },{capture:true,passive:false});
 document.querySelectorAll('[data-anchor-tool]').forEach(b=>b.onclick=()=>setTool(b.dataset.anchorTool));
 $('#anchor-list').onchange=e=>{const id=e.target.value;setTool('select');select(id);};
 const fields={text:'anchor-text',color:'anchor-color',size:'anchor-size',bend:'anchor-bend',ticks:'anchor-ticks',divisions:'anchor-divisions',follow:'anchor-follow',arrow:'anchor-arrow',closed:'anchor-closed',visible:'anchor-item-visible'};
 for(const [key,id] of Object.entries(fields)){
  const input=$('#'+id);input.addEventListener('change',()=>{const m=current();if(!m){sync();return;}remember();m[key]=input.type==='checkbox'?input.checked:['size','bend','divisions'].includes(key)?Number(input.value):input.value;changed();});
  if(input.type==='range')input.addEventListener('input',()=>{$('#'+(key==='size'?'anchor-size-value':'anchor-bend-value')).textContent=Number(input.value).toFixed(key==='size'?1:2);});
 }
 $('#anchor-delete').onclick=()=>{if(!current())return;remember();marks=marks.filter(m=>m.id!==selected);selected=null;changed();};
 for(const [id,factor] of [['anchor-grow',1.12],['anchor-shrink',1/1.12]])$('#'+id).onclick=()=>{
  const m=current();if(!m)return;remember();if(m.anchors.length===1)m.size=THREE.MathUtils.clamp(m.size*factor,.3,3);
  else{const pts=m.anchors.map(a=>pointFromAnchor(a).point),center=pts.reduce((a,p)=>a.add(p),new THREE.Vector3()).multiplyScalar(1/pts.length);m.anchors=pts.map(p=>nearest(p.sub(center).multiplyScalar(factor).add(center)).anchor);}
  changed();
 };
 $('#anchor-clear').onclick=()=>{if(!marks.length)return;remember();marks=[];selected=null;changed();};
 $('#anchor-undo').onclick=()=>{if(!undo.length)return;redo.push(snap());marks=undo.pop();selected=null;changed();};
 $('#anchor-redo').onclick=()=>{if(!redo.length)return;undo.push(snap());marks=redo.pop();selected=null;changed();};
 $('#anchor-visible').onchange=()=>{dirty=true;};$('#anchor-occlude').onchange=()=>rebuild();
 document.addEventListener('keydown',e=>{
  if(suspended||/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName))return;
  if(e.key==='Escape')setTool('rotate');
  if((e.key==='Delete'||e.key==='Backspace')&&current()){e.preventDefault();$('#anchor-delete').click();}
 });
 function project(){const result=copy(marks);result.forEach(m=>delete m.fallback);return {format:'female-3d-surface-annotations',version:1,modelKey,theme:api.getTheme(),annotations:result};}
 function validate(value){
  if(value?.format!=='female-3d-surface-annotations'||value.version!==1||value.modelKey!==modelKey)throw Error('不是本版模型的三维课件；不同模型版本不能直接复用锚点，以免错位。');
  if(!Array.isArray(value.annotations)||value.annotations.length>120)throw Error('三维标注数量无效。');
  const seen=new Set();
  for(const m of value.annotations){
   if(!m||typeof m.id!=='string'||m.id.length>100||seen.has(m.id)||!['label','curve','pen'].includes(m.kind)||typeof m.text!=='string'||m.text.length>80||!colorOK(m.color)||!finite(m.size)||m.size<.3||m.size>3||!finite(m.bend)||Math.abs(m.bend)>.8||!Number.isInteger(m.divisions)||m.divisions<2||m.divisions>20)throw Error('三维标注属性无效。');seen.add(m.id);
   if(!['ticks','follow','arrow','closed','visible'].every(k=>typeof m[k]==='boolean'))throw Error('显示属性无效。');
   if(!Array.isArray(m.labelOffset)||m.labelOffset.length!==3||m.labelOffset.some(n=>!finite(n)||Math.abs(n)>3))throw Error('标签位置无效。');
   if(!Array.isArray(m.anchors)||m.anchors.length<1||m.anchors.length>512||(m.kind==='label'&&m.anchors.length!==1)||(m.kind==='curve'&&m.anchors.length!==2)||(m.kind==='pen'&&m.anchors.length<2))throw Error('锚点数量无效。');
   for(const a of m.anchors)if(!Number.isInteger(a.face)||a.face<0||a.face>=index.count/3||!Array.isArray(a.bary)||a.bary.length!==3||a.bary.some(n=>!finite(n)||n<-.0001||n>1.0001)||Math.abs(a.bary.reduce((x,y)=>x+y,0)-1)>.0001)throw Error('表面锚点无效。');
  }
  return copy(value.annotations);
 }
 function importProject(value){const next=validate(value);if(marks.length+next.length>120)throw Error('导入后超过 120 条，请在新窗口打开课件。');remember();marks.push(...next.map(m=>({...m,id:uid()})));selected=null;if(['ivory','slate','mist'].includes(value.theme))api.setTheme(value.theme);changed();return next.length;}
 $('#anchor-save').onclick=()=>{const blob=new Blob([JSON.stringify(project())],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='female-3d-surface-annotations.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),10000);};
 $('#anchor-load').onclick=()=>$('#anchor-file').click();
 $('#anchor-file').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>8e6)throw Error('课件超过 8 MB。');const count=importProject(JSON.parse(await f.text()));api.message(`已导入 ${count} 条三维标注，原有标注保留。`);}catch(error){api.message(error.message);}finally{e.target.value='';}};
 function occluded(a){
  const world=pointFromAnchor(a).point,camera=api.getCamera(),from=camera.isOrthographicCamera?world.clone().add(camera.position.clone().sub(api.getControls().target)):camera.position.clone();
  const delta=world.clone().sub(from),length=delta.length();ray.set(from,delta.normalize());const hit=ray.intersectObject(body,false)[0];return !!hit&&hit.distance<length-.003;
 }
 function update(){
  body.updateWorldMatrix(true,false);const signatureBody=body.matrixWorld.elements.join(',');if(lastBody&&lastBody!==signatureBody)rebuild();lastBody=signatureBody;
  const camera=api.getCamera(),rect=canvas.getBoundingClientRect(),signature=[...camera.position.toArray(),...camera.quaternion.toArray(),camera.zoom,rect.height].join(',');
  if(signature===lastCamera&&!dirty)return;lastCamera=signature;dirty=false;
  root.visible=$('#anchor-visible').checked;
  for(const m of marks){const g=groups.get(m.id);const samples=m.anchors.filter((a,i)=>i===0||i===m.anchors.length-1||i%Math.max(1,Math.floor(m.anchors.length/6))===0);g.visible=m.visible&&(!$('#anchor-occlude').checked||!samples.every(occluded));
   g.traverse(o=>{if(!o.userData.label)return;const distance=camera.position.distanceTo(o.position),worldPerPixel=camera.isOrthographicCamera?(camera.top-camera.bottom)/(camera.zoom*rect.height):2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*distance/rect.height;const height=30*m.size*o.userData.lines*worldPerPixel;o.scale.set(height*o.userData.aspect,height,1);});
  }
 }
 function setSuspended(value){suspended=value;$('#anchor-panel').hidden=value;$('#background-controls').hidden=value;if(value){setTool('rotate');controls(false);}else controls(true);}
 sync();setTool('rotate');
 return {update,setSuspended,setTool,project,importProject,validate,pointFromAnchor,fromHit,nearest,surfaceAt,add,defaults,select,root,modelKey,get annotations(){return marks;},get selected(){return selected;},get tool(){return tool;}};
}
