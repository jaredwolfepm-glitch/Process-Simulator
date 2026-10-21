"""Browser tests for compact, spaced WIP/operator/coverage indicators.
Run: CHROMIUM_PATH=/usr/bin/chromium python tests/headcount_indicators.py
Requires Python Playwright. Serves the checked-out application on an ephemeral local port.
"""
import asyncio,copy,functools,http.server,json,os,subprocess,tempfile,threading
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parent.parent
APP=Path(os.environ.get('SIMULATOR_HTML',str(ROOT/'Process_Simulator_Repaired.html')))
RESULTS=Path(os.environ.get('INDICATOR_RESULTS',str(ROOT/'test-results/indicators')))
def fixture():
 stations=[]
 for id,x,demand,initial in [(1,180,5,8),(2,450,2,3),(3,730,0,0)]:
  stations.append(dict(id=id,name=['Prep','Assembly','Complete'][id-1],type='Sink' if id==3 else 'Process',x=x,y=200,ct=0 if id==3 else 2,servers=1,buffer=20,initial=initial,operators=demand,batch=1,uptime=100,fpy=100,setupTime=0,loadTime=0,manualTime=0,machineTime=0 if id==3 else 2,walkTime=0,unloadTime=0,inspectionTime=0,laborType='General',processDefined=True))
 return dict(schema='ELS_PROCESS_ANALYSIS_SCENARIO',schemaVersion=3,appVersion='2.7.36',model=dict(stations=stations,routes=[{'from':1,'to':2},{'from':2,'to':3}],equipment=[],pxPerFt=11.2),simulation=dict(days=1,shifts=1,unitsPerShift=20,shiftLengthMin=480,breakMin=0,efficiencyPct=100,designWipCapacity=60,cureContinuesOffShift=True),labor=dict(showCoverage=True,showDots=True,people=[dict(id=i+1,name=f'Operator {i+1} — long name',assignments=[dict(stationId=1,pct=50),dict(stationId=2,pct=50)],walkingPaths={}) for i in range(8)]),view=dict(zoom=1))
async def load(page,data=None,name='Indicators.json'):
 await page.locator('#scenarioFile').set_input_files(dict(name=name,mimeType='application/json',buffer=json.dumps(data or fixture()).encode()))
 await expect(page.locator('#scenarioFile')).to_have_value('');await expect(page.locator('#scenarioName')).to_have_text(name)
async def hover(page,region):
 dims=await page.evaluate('({w:canvas.width,h:canvas.height})');box=await page.locator('#layoutCanvas').bounding_box()
 x=box['x']+(region['x']+region['w']/2)*box['width']/dims['w'];y=box['y']+(region['y']+region['h']/2)*box['height']/dims['h']
 await page.mouse.move(x,y)
async def regions(page):return await page.evaluate('LayoutIndicators.snapshot()')
def no_overlap(items):
 for i,a in enumerate(items):
  for b in items[i+1:]:assert a['x']+a['w']+8<=b['x'] or b['x']+b['w']+8<=a['x'] or a['y']+a['h']+8<=b['y'] or b['y']+b['h']+8<=a['y'],(a,b)
async def main():
 RESULTS.mkdir(parents=True,exist_ok=True);checks=[]
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 with tempfile.TemporaryDirectory() as tmp:
  temp=Path(tmp);(temp/'app.html').write_bytes(APP.read_bytes())
  baseline=os.environ.get('BASELINE_HTML')
  if baseline:(temp/'before.html').write_bytes(Path(baseline).read_bytes())
  else:(temp/'before.html').write_bytes(subprocess.check_output(['git','show','b314dd18a1dfe62c0669f7148e4dcfbbceac69d1:Process_Simulator_Repaired.html'],cwd=ROOT))
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=tmp));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_address[1]}'
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   await page.add_init_script('window.showSaveFilePicker=undefined;window.showOpenFilePicker=undefined')
   await page.goto(base+'/app.html');await load(page)
   items=await regions(page);no_overlap(items)
   assert len([i for i in items if i['kind']=='coverage'])==2
   combined=next(i for i in items if i['kind']=='coverage' and i['stationId']==1);assert len(combined['people'])==8
   assert combined['assigned']==4 and combined['demand']==5 and combined['state']=='gap'
   assert not [i for i in items if i['kind']=='operators'];checks.append('Eight colocated operators group into one badge; coverage values remain 4/5 FTE')
   covered=next(i for i in items if i['kind']=='coverage' and i['stationId']==2);assert covered['state']=='covered'
   assert not await page.locator('#layoutIndicatorTooltip').is_visible()
   text=await page.evaluate("()=>{const texts=[],fill=ctx.fillText;ctx.fillText=function(t,...args){texts.push(String(t));return fill.call(this,t,...args)};try{draw()}finally{ctx.fillText=fill}return texts}")
   assert not any('FTE' in t or 'Operator' in t or 'HC ' in t or 'Staffing' in t for t in text),text
   for i in items:
    if i['kind']=='wip':assert i['text'] in text
   await page.screenshot(path=str(RESULTS/'compact-layout.png'),full_page=True);checks.append('Associated labels, names and FTE text are absent from the canvas; WIP quantities remain visible')
   await hover(page,combined);await expect(page.locator('#layoutIndicatorTooltip')).to_be_visible();await expect(page.locator('#layoutIndicatorTooltip')).to_contain_text('4.00 assigned / 5.00 required FTE');await expect(page.locator('#layoutIndicatorTooltip')).to_contain_text('Operator 1')
   assert not await page.locator('#workAreaLens').is_visible();await page.screenshot(path=str(RESULTS/'coverage-hover.png'),full_page=True)
   await page.mouse.move(12,12);await expect(page.locator('#layoutIndicatorTooltip')).not_to_be_visible()
   wip=next(i for i in items if i['kind']=='wip');await hover(page,wip);await expect(page.locator('#layoutIndicatorTooltip')).to_contain_text('Work in progress')
   await page.keyboard.press('Escape');await expect(page.locator('#layoutIndicatorTooltip')).not_to_be_visible();checks.append('Real hover reveals staffing/name/WIP details; leaving or Escape hides them; magnifier does not obscure tooltip')
   # Headcount-only and coverage-only modes keep the saved toggles' semantics.
   await page.locator('#simulationMenu>summary').click();await page.locator('#headcountBtn').click();await page.locator('#showLaborCoverage').uncheck();await page.locator('#headcountCloseBtn').click()
   items=await regions(page);assert len([i for i in items if i['kind']=='operators'])==1;no_overlap(items)
   await hover(page,next(i for i in items if i['kind']=='operators'));await expect(page.locator('#layoutIndicatorTooltip')).to_contain_text('HC 1')
   await page.locator('#simulationMenu>summary').click();await page.locator('#headcountBtn').click();await page.locator('#showHeadcountDots').uncheck();await page.locator('#showLaborCoverage').check();await page.locator('#headcountCloseBtn').click()
   assert all(not i.get('people') for i in await regions(page));assert not await page.locator('#layoutIndicatorTooltip').is_visible();checks.append('Headcount Setup controls independently show grouped operators and coverage badges')
   single=fixture();single['labor']['people']=single['labor']['people'][:1];single['labor']['people'][0]['assignments']=[dict(stationId=1,pct=100)]
   for station in single['model']['stations']:station['initial']=0;station['operators']=1 if station['id']==1 else 0
   await load(page,single,'Single.json')
   labels=await page.evaluate("()=>{const texts=[],fill=ctx.fillText;ctx.fillText=function(t,...args){texts.push(String(t));return fill.call(this,t,...args)};try{LayoutIndicators.draw()}finally{ctx.fillText=fill}return texts}")
   assert labels==[],labels;checks.append('A single-operator badge has an uncluttered icon with no redundant count or overlapping label')
   # More crowded geometry and larger fonts still have separated, bounded annotations.
   dense=fixture();dense['model']['stations']=[];dense['model']['routes']=[];dense['labor']['people']=[]
   for i in range(12):
    s=copy.deepcopy(fixture()['model']['stations'][0]);s.update(id=i+1,name=f'Cell {i+1}',x=120+(i%4)*185,y=110+(i//4)*185,operators=1,initial=i+1);dense['model']['stations'].append(s)
    dense['labor']['people'].append(dict(id=i+1,name=f'Cell operator {i+1}',assignments=[dict(stationId=i+1,pct=100)],walkingPaths={}))
   await load(page,dense,'Dense.json');no_overlap(await regions(page));await page.screenshot(path=str(RESULTS/'dense-layout.png'),full_page=True)
   await page.evaluate('headcountSymbolSize=64;headcountTextSize=30;draw()');no_overlap(await regions(page))
   for r in await regions(page):assert r['x']>=0 and r['y']>=0 and r['x']+r['w']<=await page.evaluate('canvas.width') and r['y']+r['h']<=await page.evaluate('canvas.height')
   checks.append('Twelve-station layout and maximum operator display sizes keep badge rectangles separated and in bounds')
   # Hover geometry follows zoom and scrolling; reimport clears any previous tooltip.
   await load(page);await page.evaluate('applyZoom(.7,false);draw()');r=next(i for i in await regions(page) if i['kind']=='coverage');await hover(page,r);await expect(page.locator('#layoutIndicatorTooltip')).to_be_visible()
   await load(page,name='Reloaded.json');await expect(page.locator('#layoutIndicatorTooltip')).not_to_be_visible();checks.append('Hover hit-testing works after zoom and clears on scenario import')
   # Add walking paths and advance playback: eight moving markers remain grouped, not eight lines/icons.
   walking=fixture()
   for person in walking['labor']['people']:person['walkingPaths']={'1>2':[dict(x=300,y=330)]}
   await load(page,walking,'Walking.json');await page.evaluate('fastRun();setPlaybackTime(.5);draw()');no_overlap(await regions(page))
   moving=[i for i in await regions(page) if i['kind']=='operators'];assert moving and len(moving[0]['people'])==8;checks.append('Moving shared-path operators group without redrawing per-person travel lines')
   # Print options expose the new layer; preview rendering cannot change live visibility flags.
   await page.locator('#fileMenu>summary').click();await page.locator('#printLayoutBtn').click();assert await page.locator('[data-layer=headcount]').is_visible()
   await page.locator('[data-layer=coverage]').check();before=await page.locator('#layoutPrintPreview').get_attribute('src');live=await page.evaluate('({dots:showHeadcountDots,coverage:showLaborCoverage})')
   await page.locator('[data-layer=headcount]').uncheck();after=await page.locator('#layoutPrintPreview').get_attribute('src');assert before!=after;assert await page.evaluate('({dots:showHeadcountDots,coverage:showLaborCoverage})')==live
   await page.locator('[data-layer=headcount]').check();await page.locator('#layoutPrintClose').click();await hover(page,(await regions(page))[0]);await page.emulate_media(media='print');assert not await page.locator('#layoutIndicatorTooltip').is_visible();await page.emulate_media(media='screen')
   checks.append('Operator print layer changes actual preview pixels and restores live flags; hover text never prints')
   # Saved scenario compatibility and numerical baseline are unchanged by rendering.
   await load(page,walking);saved=await page.evaluate('captureScenario()');await load(page,saved,'Roundtrip.json');assert await page.evaluate('captureScenario().labor')==saved['labor']
   baseline_page=await browser.new_page();await baseline_page.goto(base+'/before.html');await load(baseline_page,walking)
   for tab in [baseline_page,page]:await tab.evaluate('fastRun()')
   expression='({done,simTime,peakWip,peakCure,history,stations:stations.map(s=>({id:s.id,ct:s.ct,operators:s.operators})),laborPeople})'
   assert await baseline_page.evaluate(expression)==await page.evaluate(expression);checks.append('JSON round-trip and exact simulation history match the previously released application')
   assert not errors,errors
   report={'passed':len(checks),'failed':0,'browser':browser.version,'checks':checks,'page_errors':errors};(RESULTS/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));await browser.close()
  server.shutdown()
asyncio.run(main())
