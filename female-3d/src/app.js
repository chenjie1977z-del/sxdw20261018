import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createTeachingTools } from './teaching.js';
import { createSurfaceAnnotations } from './anchors.js';

const $=s=>document.querySelector(s);
const viewport=$('#viewport'),scene=new THREE.Scene();
scene.background=new THREE.Color('#f5f4ef');
let renderer;
try{renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});}
catch(error){$('#load-text').textContent='此浏览器无法启用 WebGL。请在 Chrome / Edge 中启用硬件加速后重新打开。';throw error;}
renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
viewport.append(renderer.domElement);
const ortho=new THREE.OrthographicCamera(-1.05,1.05,1.05,-1.05,.01,30);
const perspective=new THREE.PerspectiveCamera(35,1,.01,30);
let camera=ortho,controls,model,materials=[],body,teaching,anchors,annotationActive=false,theme='ivory';
function setupControls(){
 if(controls)controls.dispose();
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.09;
 controls.target.set(0,.85,0);controls.minDistance=.22;controls.maxDistance=8;
 controls.minZoom=.65;controls.maxZoom=10;controls.autoRotateSpeed=.7;
 controls.addEventListener('start',()=>{$('[data-view].active')?.classList.remove('active');});
}
camera.position.set(0,.85,3.4);setupControls();
scene.add(new THREE.HemisphereLight(0xf6f3e9,0x596860,2.05));
const key=new THREE.DirectionalLight(0xffeee0,3.0);key.position.set(-2,3.4,3.5);scene.add(key);
const fill=new THREE.DirectionalLight(0xdfeaff,1.4);fill.position.set(2,1.8,-2);scene.add(fill);
const rim=new THREE.DirectionalLight(0xfff8ec,1.0);rim.position.set(0,2.7,-3);scene.add(rim);
const softFront=new THREE.DirectionalLight(0xfff4ec,.65);softFront.position.set(0,.8,4);scene.add(softFront);
const floor=new THREE.Mesh(new THREE.CircleGeometry(.66,96),new THREE.MeshBasicMaterial({color:0xe2e7de}));floor.rotation.x=-Math.PI/2;floor.position.y=-.006;scene.add(floor);
const grid=new THREE.GridHelper(2,20,0xc5d1c8,0xe2e6dd);grid.position.y=-.004;scene.add(grid);
const themes={ivory:{background:'#f5f4ef',floor:'#e2e7de',grid:'#c5d1c8'},slate:{background:'#29343d',floor:'#36454e',grid:'#566975'},mist:{background:'#46525a',floor:'#536269',grid:'#788b93'}};
function setTheme(name){if(!themes[name])return;theme=name;const p=themes[name];scene.background.set(p.background);floor.material.color.set(p.floor);grid.material.color.set(p.grid);$('.stage').dataset.theme=name;document.querySelectorAll('[data-theme]').forEach(b=>b.classList.toggle('active',b.dataset.theme===name));}
document.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>setTheme(b.dataset.theme));
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();
const landmarkGroup=new THREE.Group();scene.add(landmarkGroup);landmarkGroup.visible=false;
const labels=[];
const landmarks=[
 {name:'左肩峰区 · 示意',p:[.165,1.326,.005],n:[0,1,0]},
 {name:'右肩峰区 · 示意',p:[-.165,1.326,.005],n:[0,1,0]},
 {name:'左肩胛区 · 示意',p:[.088,1.285,-.077],n:[0,0,-1]},
 {name:'右肩胛区 · 示意',p:[-.088,1.285,-.077],n:[0,0,-1]},
 {name:'左髌前区 · 示意',p:[.137,.457,.082],n:[0,0,1]},
];
for(const l of landmarks){
 const marker=new THREE.Mesh(new THREE.SphereGeometry(.006,12,8),new THREE.MeshBasicMaterial({color:0x2d8271}));marker.position.set(...l.p);landmarkGroup.add(marker);
 const el=document.createElement('div');el.className='landmark';el.textContent=l.name;el.hidden=true;$('#labels').append(el);labels.push({el,marker,normal:new THREE.Vector3(...l.n)});
}
function resize(){
 const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h,false);
 const a=w/h;ortho.left=-1.01*a;ortho.right=1.01*a;ortho.top=1.01;ortho.bottom=-1.01;ortho.updateProjectionMatrix();
 perspective.aspect=a;perspective.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);resize();
const views={front:{p:[0,.85,3.4],t:[0,.85,0],n:'正面观察'},back:{p:[0,.85,-3.4],t:[0,.85,0],n:'背面观察'},
 left:{p:[3.4,.85,0],t:[0,.85,0],n:'左侧观察'},right:{p:[-3.4,.85,0],t:[0,.85,0],n:'右侧观察'},
 shoulder:{p:[.48,1.45,-1.1],t:[0,1.29,0],z:3.0,n:'肩背局部观察'},
 face:{p:[0,1.54,1.1],t:[0,1.54,0],z:6.5,n:'面部与发丝观察'},
 neck:{p:[.18,1.40,1.4],t:[0,1.36,0],z:4.2,n:'锁骨与颈部观察'},
 thighs:{p:[.15,.63,1.8],t:[0,.63,.04],z:2.8,n:'大腿与膝部观察'},
 abdomen:{p:[0,1.013,2],t:[0,1.013,.10],z:5,n:'肚脐与腹部观察'},
 kneeback:{p:[0,.445,-2],t:[0,.445,0],z:5,n:'腘窝与横纹观察'},
 wrist:{p:[.50,1.01,-1.2],t:[.431,1.01,.16],z:7,n:'掌侧腕横纹观察'}};
function setView(name){
 const v=views[name];camera.position.set(...v.p);controls.target.set(...v.t);ortho.zoom=v.z||1;ortho.updateProjectionMatrix();
 if(camera===perspective&&v.z)camera.position.copy(controls.target).add(new THREE.Vector3(...v.p).sub(new THREE.Vector3(...v.t)).normalize().multiplyScalar(name==='face'?.38:name==='neck'?.65:.85));
 controls.update();$('#view-name').textContent=v.n;
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
$('#reset').onclick=()=>{setView('front');clearMeasure();};
$('#grid').onchange=e=>{grid.visible=e.target.checked;};
$('#rotate').onchange=e=>{controls.autoRotate=e.target.checked;};
$('#markers').onchange=e=>{landmarkGroup.visible=e.target.checked;};
$('#perspective').onchange=e=>{
 const p=camera.position.clone(),t=controls.target.clone();camera=e.target.checked?perspective:ortho;
 camera.position.copy(p);setupControls();controls.target.copy(t);controls.autoRotate=$('#rotate').checked;controls.update();
};
function applyMode(mode){
 for(const m of materials){
  if(mode==='clay'&&m.map&&!m.clayMap&&m.material.name.includes('flush sportswear')){
   const image=m.map.image,canvas=document.createElement('canvas');canvas.width=Math.min(image.width,2048);canvas.height=Math.round(image.height*canvas.width/image.width);
   const c=canvas.getContext('2d');c.filter='grayscale(1) brightness(1.25)';c.drawImage(image,0,0,canvas.width,canvas.height);m.clayMap=m.map.clone();m.clayMap.image=canvas;m.clayMap.needsUpdate=true;
  }
  m.material.color.copy(mode==='clay'?new THREE.Color('#d9d3be'):m.color);m.material.map=mode==='clay'?(m.clayMap||null):m.map;m.material.normalMap=mode==='clay'?null:m.normalMap;m.material.roughness=mode==='clay'?.85:m.roughness;m.material.needsUpdate=true;
 }
 document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>applyMode(b.dataset.mode));
$('#wire').onchange=e=>{for(const m of materials)m.material.wireframe=e.target.checked;};
function message(text){$('#message').textContent=text;$('#message').style.display='block';clearTimeout(message.timer);message.timer=setTimeout(()=>$('#message').style.display='none',3500);}
let measuring=false,points=[],measurementObjects=[];
function clearMeasure(){for(const o of measurementObjects){scene.remove(o);o.geometry.dispose();o.material.dispose();}measurementObjects=[];points=[];$('#measurement').textContent='点击表面选取两点；数值仅属于这个合成模型。';}
function captureSnapshot(){
 const size=renderer.getSize(new THREE.Vector2()),ratio=renderer.getPixelRatio();
 controls.autoRotate=false;$('#rotate').checked=false;
 const width=4096,height=Math.round(width/size.x*size.y);
 if(height>renderer.capabilities.maxTextureSize)throw Error('窗口过窄，请放宽窗口后建立标注页。');
 try{anchors?.update();renderer.setPixelRatio(1);renderer.setSize(width,height,false);renderer.render(scene,camera);return {width,height,dataURL:renderer.domElement.toDataURL('image/png')};}
 finally{renderer.setPixelRatio(ratio);renderer.setSize(size.x,size.y,false);}
}
$('#measure').onclick=()=>{anchors?.setTool('rotate');measuring=!measuring;clearMeasure();$('#measure').classList.toggle('active',measuring);renderer.domElement.style.cursor=measuring?'crosshair':'';message(measuring?'依次点击两个体表位置，计算空间直线距离':'测距已关闭');};
let down;
renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
renderer.domElement.addEventListener('pointerup',e=>{
 if(!measuring||anchors?.tool!=='rotate'||!body||!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
 const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);
 const hits=raycaster.intersectObject(model,true);if(!hits.length)return;
 if(points.length===2)clearMeasure();points.push(hits[0].point.clone());
 const dot=new THREE.Mesh(new THREE.SphereGeometry(.004,12,8),new THREE.MeshBasicMaterial({color:0xb44932}));dot.position.copy(hits[0].point);scene.add(dot);measurementObjects.push(dot);
 if(points.length===1)$('#measurement').textContent='已选第一点，请点击第二点。';
 if(points.length===2){const geometry=new THREE.BufferGeometry().setFromPoints(points);const line=new THREE.Line(geometry,new THREE.LineBasicMaterial({color:0xb44932,depthTest:false}));scene.add(line);measurementObjects.push(line);$('#measurement').textContent=`空间直线距离：${(points[0].distanceTo(points[1])*1000).toFixed(1)} mm（模型值，非体表弧长）`;}
});
$('#export').onclick=()=>{
 if(!model)return;const button=$('#export');button.disabled=true;
 const size=renderer.getSize(new THREE.Vector2()),ratio=renderer.getPixelRatio();
 try{const width=4096,height=Math.round(width/size.x*size.y);if(height>renderer.capabilities.maxTextureSize)throw Error('当前窗口过窄，请放宽窗口后导出');
 anchors?.update();renderer.setPixelRatio(1);renderer.setSize(width,height,false);renderer.render(scene,camera);
 renderer.domElement.toBlob(blob=>{if(blob){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='asian-female-3d-4K.png';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),10000);message('已导出 4096 像素截图，包含当前可见三维标注；不含侧栏与示意观察点文字。');}else message('导出失败，请重试');},'image/png');
 }catch(error){message(error.message);}finally{renderer.setPixelRatio(ratio);renderer.setSize(size.x,size.y,false);button.disabled=false;}
};
function animate(){requestAnimationFrame(animate);if(annotationActive)return;controls.update();anchors?.update();renderer.render(scene,camera);
 for(const {el,marker,normal} of labels){
  if(!landmarkGroup.visible){el.hidden=true;continue;}
  const projected=marker.position.clone().project(camera);const to=camera.position.clone().sub(marker.position).normalize();
  el.hidden=projected.z>1||projected.z< -1||Math.abs(projected.x)>1||Math.abs(projected.y)>1||normal.dot(to)<.02;
  el.style.left=`${(projected.x*.5+.5)*viewport.clientWidth}px`;el.style.top=`${(-projected.y*.5+.5)*viewport.clientHeight}px`;
 }
}
animate();
try{
 const binary=atob(window.__MODEL_BASE64__);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);delete window.__MODEL_BASE64__;
 new GLTFLoader().parse(bytes.buffer,'',gltf=>{
  model=gltf.scene;scene.add(model);let triangles=0;
  model.traverse(o=>{if(o.isMesh){o.frustumCulled=false;if(o.name==='Female_Surface')body=o;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;for(const m of Array.isArray(o.material)?o.material:[o.material]){if(!materials.some(x=>x.material===m))materials.push({material:m,color:m.color.clone(),map:m.map,normalMap:m.normalMap,roughness:m.roughness});}}});
  $('#loading').style.display='none';$('#status').textContent=`${Math.round(triangles/1000)}k 三角面 · 合成身高 165 cm`;setView('front');
  model.updateMatrixWorld(true);
  anchors=createSurfaceAnnotations({scene,body,canvas:renderer.domElement,getCamera:()=>camera,getControls:()=>controls,message,getTheme:()=>theme,setTheme,stopRotate(){controls.autoRotate=false;$('#rotate').checked=false;measuring=false;$('#measure').classList.remove('active');clearMeasure();const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;}});
  teaching=createTeachingTools({capture:captureSnapshot,message,getViewName:()=>$('#view-name').textContent,
   getView:()=>({projection:camera===ortho?'orthographic':'perspective',position:camera.position.toArray(),target:controls.target.toArray(),zoom:camera.zoom}),
   setActive(active){annotationActive=active;anchors.setSuspended(active);controls.enabled=!active;if(active){controls.autoRotate=false;$('#rotate').checked=false;measuring=false;$('#measure').classList.remove('active');clearMeasure();}}
  });$('#annotate-view').disabled=false;
  window.__viewer={scene,get camera(){return camera;},get controls(){return controls;},renderer,model,setView,applyMode,teaching,anchors,setTheme,get theme(){return theme;},get triangleCount(){return triangles;},ready:true};
 },error=>{console.error(error);$('#load-text').textContent='模型读取失败，请重新下载完整文件。';});
}catch(error){console.error(error);$('#load-text').textContent='文件不完整或浏览器内存不足，请重新下载并用桌面版 Chrome / Edge 打开。';}
