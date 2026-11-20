
// header: transparent over the hero, solid white on scroll; solid from the
// start on pages without a hero.
var header=document.getElementById('siteHeader');
function headerState(){
  if(!header)return;
  if(!document.querySelector('.hero')){header.classList.add('solid');document.body.classList.add('no-hero');return;}
  header.classList.toggle('solid',window.scrollY>10);
}
window.addEventListener('scroll',headerState,{passive:true});
headerState();
// mobile menu
var btn=document.getElementById('menuBtn'),nav=document.getElementById('mainNav');
if(btn&&nav){btn.addEventListener('click',function(){var o=nav.classList.toggle('open');btn.setAttribute('aria-expanded',o?'true':'false');});}
// scroll reveal
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);}});},{threshold:.12});
document.querySelectorAll('.reveal').forEach(function(el){io.observe(el);});
// video facade: sharp maxresdefault thumbnail; click loads the real player.
document.querySelectorAll('.video-thumb').forEach(function(t){
  t.addEventListener('click',function(){
    var vid=t.dataset.vid,title=t.dataset.title||'Video';
    var f=document.createElement('iframe');
    f.src='https://www.youtube-nocookie.com/embed/'+vid+'?autoplay=1';
    f.title=title;f.allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';f.allowFullscreen=true;
    t.replaceWith(f);
  });
});
// lightbox (product photo)
var lb=document.getElementById('lightbox');
function openLB(src,alt){if(!lb)return;lb.querySelector('img').src=src;lb.querySelector('img').alt=alt||'';lb.classList.add('open');document.body.style.overflow='hidden';}
function closeLB(){if(!lb)return;lb.classList.remove('open');lb.classList.remove('zoomed');document.body.style.overflow='';}
if(lb){lb.addEventListener('click',function(e){if(e.target.tagName==='IMG'){lb.classList.toggle('zoomed');}else{closeLB();}});document.addEventListener('keydown',function(e){if(e.key==='Escape')closeLB();});}
var dp=document.getElementById('detailPhoto');
if(dp&&!document.getElementById('galleryMain')){dp.addEventListener('click',function(){openLB(dp.querySelector('img').src,dp.querySelector('img').alt);});}
// product gallery: switch the main image + active thumb/dot; the
// lightbox opens the CURRENTLY shown image. Thumbs carry data-full for
// extras (their base64 data URIs) — the primary image's data URI is
// never copied into an attribute (it is read once from the main img's src).
var gm=document.getElementById('galleryMain');
if(gm){
  var gThumbs=Array.prototype.slice.call(document.querySelectorAll('.g-thumb'));
  var gDots=Array.prototype.slice.call(document.querySelectorAll('.g-dot'));
  var gSrcs=gThumbs.map(function(t,i){return i===0?gm.src:(t.getAttribute('data-full')||gm.src);});
  var gIdx=0;
  function gShow(i){
    gIdx=(i+gSrcs.length)%gSrcs.length;
    gm.src=gSrcs[gIdx];
    var cap=gThumbs[gIdx].getAttribute('data-cap');
    if(cap){gm.style.cssText=cap;}
    gm.alt=gThumbs[gIdx].getAttribute('data-alt')||gm.alt;
    gThumbs.forEach(function(t,j){t.classList.toggle('active',j===gIdx);});
    gDots.forEach(function(d,j){d.classList.toggle('active',j===gIdx);});
  }
  gThumbs.forEach(function(t,i){t.addEventListener('click',function(e){e.stopPropagation();gShow(i);});});
  gDots.forEach(function(d,i){d.addEventListener('click',function(e){e.stopPropagation();gShow(i);});});
  document.querySelectorAll('.g-arrow').forEach(function(a){a.addEventListener('click',function(e){e.stopPropagation();gShow(gIdx+parseInt(a.getAttribute('data-dir'),10));});});
  gm.addEventListener('click',function(){openLB(gm.src,gm.alt);});
}
// category filter + sort
var grid=document.getElementById('catGrid');
if(grid){
  var brandSel=document.getElementById('brandFilter'),sortSel=document.getElementById('sortSel'),countEl=document.getElementById('resultCount');
  function applyFilter(){
    var cards=Array.prototype.slice.call(grid.querySelectorAll('.card'));
    var b=brandSel?brandSel.value:'';
    var visible=cards.filter(function(c){var ok=!b||c.dataset.brand===b;c.style.display=ok?'':'none';return ok;});
    var s=sortSel?sortSel.value:'featured';
    // 'featured' keeps the generator's order (drones are flagship-first
    // like DJI); any other value re-sorts the visible cards.
    if(s!=='featured')visible.sort(function(a,c){
      if(s==='name-asc')return a.dataset.name.localeCompare(c.dataset.name);
      if(s==='name-desc')return c.dataset.name.localeCompare(a.dataset.name);
      if(s==='price-asc'){var pa=parseFloat(a.dataset.price)||Infinity,pb=parseFloat(c.dataset.price)||Infinity;return pa-pb;}
      if(s==='price-desc'){var pa=parseFloat(a.dataset.price)||0,pb=parseFloat(c.dataset.price)||0;return pb-pa;}
      return 0;
    });
    visible.forEach(function(c){grid.appendChild(c);});
    if(countEl)countEl.textContent=visible.length+' product'+(visible.length===1?'':'s');
  }
  if(brandSel)brandSel.addEventListener('change',applyFilter);
  if(sortSel)sortSel.addEventListener('change',applyFilter);
  applyFilter();
}
// hero carousel: DJI's official YouTube films, ~5s autoplay, crossfade,
// bottom-left prev / current / next slide list; click a list name to
// jump; pause on real mouse hover only — touch never pauses (see below).
var hc=document.getElementById('heroCarousel');
if(hc){
  var hSlides=Array.prototype.slice.call(hc.querySelectorAll('.hero-slide'));
  var hList=hc.querySelectorAll('.hero-list button');
  var hIdx=0,hTimer=null;
  // Round 12 -- SELF-HOSTED HERO FILMS: the 4 DJI films are re-encoded
  // to 720p (~2-2.5MB each, no audio) and embedded as base64 in
  // assets/hero-film-*.js (same origin as the site). No external CDN, no
  // YouTube dependency. Round 10's 6-12MB CDN mp4s never started on a
  // slow connection (Slow 3G repro: readyState 0, currentTime 0 after
  // 18s, proxy up) and Round 11's YouTube films never started on the
  // boss's machine at all (YT-blocked repro: no API, no players, poster
  // still on every slide) -- both showed a still poster. Small same-origin
  // files + preload="auto" + autoplay + play() on canplay mean the film
  // actually moves. The DJI poster stays the cover until a video really
  // plays (hero-film-on fires on the video 'playing' event, never on a
  // timer). Reduced-motion users get the poster still.
  var hReduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hVideos={};   // slide index -> <video> element
  var hBlobUrls={}; // film key -> blob: URL (built once per film)
  window.__akHeroVideos=hVideos; // debug handle: harness reads state via this
  function hB64ToBlob(b64){
    var bin=atob(b64),len=bin.length,arr=new Uint8Array(len);
    for(var i=0;i<len;i++){arr[i]=bin.charCodeAt(i);}
    return new Blob([arr],{type:'video/mp4'});
  }
  function hFilmUrl(key){
    if(hBlobUrls[key])return hBlobUrls[key];
    var F=window.__HERO_FILMS||{};
    if(!F[key])return null;
    try{hBlobUrls[key]=URL.createObjectURL(hB64ToBlob(F[key]));}catch(_){return null;}
    return hBlobUrls[key];
  }
  function hPlayVideo(j){
    var v=hVideos[j];if(!v)return;
    if(v.readyState>=2){var p=v.play();if(p&&p.catch){p.catch(function(){});}}
  }
  function hWireVideo(j){
    if(hVideos[j]||hReduced)return;
    var s=hSlides[j],key=s.dataset.film,url=hFilmUrl(key);
    if(!url)return;
    var v=document.createElement('video');
    v.className='hero-video';
    v.muted=true;v.loop=true;v.playsInline=true;v.preload='auto';v.autoplay=true;
    v.setAttribute('aria-hidden','true');
    v.addEventListener('playing',function(){s.classList.add('hero-film-on');});
    v.addEventListener('canplay',function(){if(j===hIdx){hPlayVideo(j);}});
    // Insert BEFORE the overlay/text so the video sits under them
    // (z-index 0, same as the poster) and never covers the copy.
    var ov=s.querySelector('.hero-overlay');
    if(ov){s.insertBefore(v,ov);}else{s.appendChild(v);}
    v.src=url;
    hVideos[j]=v;
    if(j===hIdx){hPlayVideo(j);}
  }
  // A film script calls this the moment its base64 lands (film scripts
  // are deferred, so they run after this file). Also wired on every
  // slide change, so a late-arriving film is used as soon as it can be.
  window.__heroFilmArrived=function(key){
    hSlides.forEach(function(s,j){if(s.dataset.film===key){hWireVideo(j);}});
  };
  function hFilm(){
    hSlides.forEach(function(s,j){
      var keep=(j===hIdx)||(j===(hIdx+1)%hSlides.length);
      if(keep&&!hReduced){
        hWireVideo(j);
        var v=hVideos[j];
        if(v){if(j===hIdx){hPlayVideo(j);}else{v.pause();}}
      }else{
        var v2=hVideos[j];
        if(v2){v2.pause();}
        s.classList.remove('hero-film-on');
      }
    });
  }
  function hGo(i){
    hIdx=(i+hSlides.length)%hSlides.length;
    hSlides.forEach(function(s,j){s.classList.toggle('active',j===hIdx);});
    var prev=(hIdx-1+hSlides.length)%hSlides.length,next=(hIdx+1)%hSlides.length;
    if(hList.length===3){
      hList[0].textContent=hSlides[prev].dataset.name;hList[0].dataset.go=prev;
      hList[1].textContent=hSlides[hIdx].dataset.name;hList[1].dataset.go=hIdx;
      hList[2].textContent=hSlides[next].dataset.name;hList[2].dataset.go=next;
    }
    hFilm();
  }
  // Load the film scripts SEQUENTIALLY, active slide first: on a slow
  // connection, parallel downloads share the pipe and NO film finishes
  // for minutes (probe: Slow 3G, 60s, zero films landed); sequential
  // loading gets the active slide's film first so the hero starts
  // moving as soon as possible, then the rest follow in slide order.
  (function(){
    var order=[],seen={};
    [hIdx,(hIdx+1)%hSlides.length].forEach(function(j){var k=hSlides[j].dataset.film;if(k&&!seen[k]){seen[k]=1;order.push(k);}});
    ['air3s','mavic3pro','mini3pro','mini4pro'].forEach(function(k){if(!seen[k]){seen[k]=1;order.push(k);}});
    (function next(){
      if(!order.length)return;
      var key=order.shift();
      var sc=document.createElement('script');
      sc.src='assets/hero-film-'+key+'.js';
      sc.onload=function(){next();};
      sc.onerror=function(){next();};
      document.head.appendChild(sc);
    })();
  })();
  function hStart(){hStop();hTimer=setInterval(function(){hGo(hIdx+1);},5000);}
  function hStop(){if(hTimer){clearInterval(hTimer);hTimer=null;}}
  hList.forEach(function(b){b.addEventListener('click',function(){hGo(parseInt(b.dataset.go,10));hStart();});});
  hc.querySelectorAll('.hero-arrow').forEach(function(a){a.addEventListener('click',function(){hGo(hIdx+parseInt(a.dataset.dir,10));hStart();});});
  // Pause ONLY on a real mouse hover. On touch screens a tap fires an
  // emulated mouseenter with no matching mouseleave, which used to stop
  // the autoplay forever after the first tap on the hero.
  function hHover(e){if(e.pointerType==='mouse'){hStop();}}
  function hUnhover(e){if(e.pointerType==='mouse'){hStart();}}
  hc.addEventListener('pointerenter',hHover);
  hc.addEventListener('pointerleave',hUnhover);
  // Safety net: any touch end or scroll restarts autoplay, so a stray
  // pause can never freeze the hero on a phone.
  hc.addEventListener('touchend',hStart,{passive:true});
  window.addEventListener('scroll',function(){if(!hTimer){hStart();}},{passive:true});
  document.addEventListener('visibilitychange',function(){if(document.hidden){hStop();}else{hStart();hFilm();}});
  hGo(0);hStart();
}
// films carousel: centre card ~1230px, side cards peeking, ‹ › arrows,
// dot indicators below (DJI "Shot on").
var fc=document.getElementById('filmsCarousel');
if(fc){
  var fTrack=fc.querySelector('.films-track');
  var fCards=Array.prototype.slice.call(fTrack.querySelectorAll('.video-card'));
  var fIdx=0;
  var fDotsWrap=document.createElement('div');
  fDotsWrap.className='films-dots';
  fCards.forEach(function(c,i){var d=document.createElement('button');d.type='button';d.setAttribute('aria-label','Go to film '+(i+1));d.addEventListener('click',function(){fGo(i);});fDotsWrap.appendChild(d);});
  fc.appendChild(fDotsWrap);
  var fDots=Array.prototype.slice.call(fDotsWrap.querySelectorAll('button'));
  function fLayout(){
    var cardW=fCards[0].getBoundingClientRect().width+16;
    var wrapW=fc.getBoundingClientRect().width;
    var off=(wrapW-fCards[0].getBoundingClientRect().width)/2-fIdx*cardW;
    fTrack.style.transform='translateX('+off+'px)';
  }
  function fGo(i){fIdx=(i+fCards.length)%fCards.length;fLayout();fDots.forEach(function(d,j){d.classList.toggle('active',j===fIdx);});}
  fc.querySelector('.films-arrow.prev').addEventListener('click',function(){fGo(fIdx-1);});
  fc.querySelector('.films-arrow.next').addEventListener('click',function(){fGo(fIdx+1);});
  window.addEventListener('resize',fLayout);
  fLayout();
}
// back-to-top button
var toTop=document.getElementById('toTop');
if(toTop){
  window.addEventListener('scroll',function(){toTop.classList.toggle('show',window.scrollY>600);},{passive:true});
  toTop.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
}
// compare: add from product pages
document.querySelectorAll('[data-compare]').forEach(function(b){
  b.addEventListener('click',function(){
    var slug=b.dataset.compare, list=[];
    try{list=JSON.parse(localStorage.getItem('akCompare')||'[]');}catch(e){list=[];}
    if(list.indexOf(slug)===-1){if(list.length>=3){alert('Compare holds up to 3 products. Remove one on the Compare page first.');return;}list.push(slug);localStorage.setItem('akCompare',JSON.stringify(list));}
    b.textContent='Added to compare';
  });
});
