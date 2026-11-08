#!/usr/bin/env python3
"""Build an iPad-friendly standalone copy without changing simulation logic."""
from pathlib import Path
import sys

src = Path(sys.argv[1] if len(sys.argv)>1 else "Process_Simulator_Repaired.html")
dst = Path(sys.argv[2] if len(sys.argv)>2 else "Process_Simulator_iPad.html")
html = src.read_text(encoding="utf-8")
if 'id="psIpadCompatibility"' in html:
    raise SystemExit("Source already patched")
old = """function syncFullScreenUI(){
 const active=!!document.fullscreenElement;
 // Geometry has one implementation in both modes. The browser owns native fullscreen.
 document.body.classList.remove('appFullscreen');
 $('fullScreenBtn').textContent=active?'Exit Full Screen':'Full Screen';
 $('fullScreenBtn').setAttribute('aria-pressed',String(active));
 const exit=$('psExitWorkspace');if(exit)exit.hidden=!active;
 window.dispatchEvent(new Event('resize'));
}"""
new = """let psInPageFullscreen=false;
function syncFullScreenUI(){
 const active=!!document.fullscreenElement||psInPageFullscreen;
 document.body.classList.toggle('appFullscreen',psInPageFullscreen);
 $('fullScreenBtn').textContent=active?'Exit Full Screen':'Full Screen';
 $('fullScreenBtn').setAttribute('aria-pressed',String(active));
 const exit=$('psExitWorkspace');if(exit)exit.hidden=!active;
 window.dispatchEvent(new Event('resize'));
}"""
assert html.count(old)==1, "Fullscreen implementation changed; review manually"
html=html.replace(old,new)
old_enter="if(!document.fullscreenEnabled||!document.documentElement.requestFullscreen)throw new Error('Fullscreen is not available in this browser or embedding context');"
assert html.count(old_enter)==1
html=html.replace(old_enter,"if(!document.fullscreenEnabled||!document.documentElement.requestFullscreen)throw new Error('Native fullscreen unavailable');")
old_catch="}catch(err){$('status').textContent='Browser full screen unavailable: '+err.message+'. Use the browser full-screen command if available.'}"
assert html.count(old_catch)==1
html=html.replace(old_catch,"}catch(err){psInPageFullscreen=true;$('status').textContent='Expanded workspace (iPad-compatible view).';}")
old_exit="async function exitFullScreen(){\n try{if(document.fullscreenElement)await document.exitFullscreen()}"
assert html.count(old_exit)==1
html=html.replace(old_exit,"async function exitFullScreen(){\n psInPageFullscreen=false;\n try{if(document.fullscreenElement)await document.exitFullscreen()}")
old_toggle="function toggleFullScreen(){return document.fullscreenElement?exitFullScreen():enterFullScreen()}"
assert html.count(old_toggle)==1
html=html.replace(old_toggle,"function toggleFullScreen(){return (document.fullscreenElement||psInPageFullscreen)?exitFullScreen():enterFullScreen()}")
insert = r"""
<style id="psIpadCompatibility">
@media(pointer:coarse){
 #layoutCanvas{touch-action:none;-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}
 .menuDrop>summary,.menuPanel button,#layoutContextMenu button,.layoutToolbar button,.commandBand button{min-height:44px}
 #layoutContextMenu button{min-height:44px!important;font-size:15px!important}
 input,select,textarea{font-size:max(16px,1em)}
 .canvasWrap{-webkit-overflow-scrolling:touch}
 dialog{max-width:calc(100vw - 16px);max-height:calc(100dvh - 16px)}
}
@media(pointer:coarse) and (max-width:1100px){
 .wrap,.wrap.inspectorHidden{grid-template-columns:minmax(0,1fr)!important}
 #layoutPanel{min-width:0}
 .canvasWrap{height:min(68dvh,720px);min-height:320px}
 body.appFullscreen .canvasWrap{height:calc(100dvh - 210px);min-height:320px}
}
</style>
<script id="psIpadTouchHandlers">
(function(){
 const canvas=document.getElementById('layoutCanvas'),wrap=document.getElementById('canvasWrap');
 if(!canvas||!wrap)return;
 let timer=null,origin=null,pinch=null,center=null;
 function cancelHold(){clearTimeout(timer);timer=null;origin=null}
 canvas.addEventListener('touchstart',e=>{
   cancelHold();
   if(e.touches.length===2){
     const a=e.touches[0],b=e.touches[1];
     pinch=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
     center={x:(a.clientX+b.clientX)/2,y:(a.clientY+b.clientY)/2};
     return;
   }
   if(e.touches.length!==1)return;
   const t=e.touches[0],x=t.clientX,y=t.clientY;
   origin={x,y};
   timer=setTimeout(()=>{
     timer=null;origin=null;
     canvas.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,button:2,clientX:x,clientY:y}));
   },600);
 },{passive:true});
 canvas.addEventListener('touchmove',e=>{
   if(e.touches.length===2&&center){
     cancelHold();
     const a=e.touches[0],b=e.touches[1],x=(a.clientX+b.clientX)/2,y=(a.clientY+b.clientY)/2;
     wrap.scrollLeft-=x-center.x;wrap.scrollTop-=y-center.y;center={x,y};
     const next=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
     if(pinch&&Math.abs(next/pinch-1)>.08){
       if(typeof zoomBy==='function')zoomBy(Math.max(.85,Math.min(1.15,next/pinch)));
       pinch=next;
     }
     e.preventDefault();return;
   }
   if(!origin||e.touches.length!==1){cancelHold();return}
   const t=e.touches[0];
   if(Math.hypot(t.clientX-origin.x,t.clientY-origin.y)>12)cancelHold();
 },{passive:false});
 ['touchend','touchcancel'].forEach(name=>canvas.addEventListener(name,e=>{
   cancelHold();
   if(e.touches.length<2){pinch=null;center=null}
 },{passive:true}));
 canvas.setAttribute('aria-label','Plant layout: tap to select, drag to move, hold for actions, pinch to zoom.');
})();
</script>
"""
assert html.count("</body>")==1
html=html.replace("</body>",insert+"\n</body>")
dst.write_text(html,encoding="utf-8")
print(f"Created {dst} ({dst.stat().st_size} bytes)")
