
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
// Round 20 -- CGI reveal: cards + category tiles fade/slide in on scroll,
// same .reveal language as the tiles. Class added by JS only, so without
// JS the cards stay visible.
document.querySelectorAll('.card,.cat-tile').forEach(function(el){el.classList.add('reveal');io.observe(el);});
// video facade: sharp maxresdefault thumbnail; click loads the real player.
document.querySelectorAll('.video-thumb').forEach(function(t){
  if(!t.dataset.vid)return; // Round 14: self-hosted Shot on cards are plain links, not YouTube facades.
  t.addEventListener('click',function(){
    var vid=t.dataset.vid,title=t.dataset.title||'Video';
    var f=document.createElement('iframe');
    f.src='https://www.youtube-nocookie.com/embed/'+vid+'?autoplay=1';
    f.title=title;f.allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';f.allowFullscreen=true;
    t.replaceWith(f);
  });
});

// Round 14 -- Shot on: self-hosted looping videos reusing the hero films.
// The homepage Shot on cards carry a <video class="shot-video" data-film>;
// when a film's base64 lands, its blob URL (built once by the hero loader)
// is shared here, so the cards play real video with ZERO new bytes.
function akWireShotVideos(){
  if(!window.__akFilmUrl)return;
  document.querySelectorAll('video.shot-video[data-film]').forEach(function(v){
    if(v.src)return;
    var url=window.__akFilmUrl(v.dataset.film);
    if(url){v.src=url;v.addEventListener('playing',function(){v.classList.add('playing');});var p=v.play();if(p&&p.catch){p.catch(function(){});}}
  });
}
window.__akWireShot=akWireShotVideos;
// Round 21 -- NATIVE-RES CHUNK LOADER (top-level, so the hero loader AND
// the detail-hero loader both use it): each film is split into <=2.8MB
// part files (assets/<kind>/<key>-p<N>.js, push limit) holding
// window.__AK_FILM_PARTS['<key>-hero'|'...-detail'][i] base64 pieces.
// Parts load sequentially and are assembled into one base64 string;
// `done` gets it, `fail` runs if any part is missing/broken.
function akLoadFilm(key,kind,parts,base,done,fail){
  var idx=0;
  (function next(){
    if(idx>=parts){
      var P=(window.__AK_FILM_PARTS||{})[key+'-'+kind]||{},b='';
      for(var i=0;i<parts;i++){b+=P[i]||'';}
      if(b){done(b);}else{fail();}
      return;
    }
    var s=document.createElement('script');
    s.src=base+key+'-p'+(idx+1)+'.js';
    idx++;
    s.onload=next;
    s.onerror=function(){fail();};
    document.head.appendChild(s);
  })();
}
// Round 21 -- NATIVE-RES DETAIL HEROES: each product page's
// <video class="detail-hero-video" data-film="..."> gets its native-res film from
// the chunk files; the poster shows until the film plays. The assets base
// is derived from this script's own src, so it works from any page depth.
(function(){
  var vids=document.querySelectorAll('video.detail-hero-video[data-film]');
  if(!vids.length)return;
  var parts={air3s:2,mavic3pro:5,mini3pro:2,mini4pro:5}; // Round 21 native-res detail parts (manifest)
  var base='assets/';
  var ss=document.getElementsByTagName('script');
  for(var i=0;i<ss.length;i++){var s=ss[i].getAttribute('src')||'';if(s.indexOf('site.js')>=0){base=s.slice(0,s.lastIndexOf('/')+1);break;}}
  vids.forEach(function(v){
    var key=v.getAttribute('data-film');
    akLoadFilm(key,'detail',parts[key]||1,base+'detail-film/',function(b64){
      try{
        var bin=atob(b64),arr=new Uint8Array(bin.length);
        for(var j=0;j<bin.length;j++){arr[j]=bin.charCodeAt(j);}
        v.src=URL.createObjectURL(new Blob([arr],{type:'video/mp4'}));
        v.addEventListener('playing',function(){v.classList.add('playing');});
        var p=v.play();if(p&&p.catch){p.catch(function(){});}
      }catch(_){}
    },function(){});
  });
})();
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
  var hIdx=0,hTimer=null,hLastGo=Date.now(),hPending=-1;
  // Round 12 -- SELF-HOSTED HERO FILMS (Round 21: native resolution,
  // 2560x1440 -- Mini 3 Pro 1920x1080 -- no audio) as base64 chunks in
  // assets/hero-film/<key>-p<N>.js (same origin as the site). No external CDN, no
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
  // Round 21 -- NATIVE RES serves every screen: one film per product at
  // its native resolution (2560x1440; Mini 3 Pro 1920x1080). Round 20's
  // 3840 "4K" files were upscales of these same masters, so native is the
  // same picture ~35% lighter and starts sooner on slow connections.
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
  window.__akFilmUrl=hFilmUrl; // Round 14: Shot on cards share the hero films' blob URLs.
  function hPlayVideo(j){
    var v=hVideos[j];if(!v)return;
    if(v.readyState>=2){var p=v.play();if(p&&p.catch){p.catch(function(){});}}
  }
  // Round 13 -- CAROUSEL WAITS FOR FILMS: on a slow connection the 5s
  // timer used to advance to a slide whose film had not arrived yet, so
  // the hero sat on a poster still. A slide is "ready" only when its
  // video exists, has data (readyState>=2) and is actually playing.
  // The timer advances ONLY to a ready slide; otherwise it stays on the
  // current (playing, looping) slide, so the hero ALWAYS shows motion,
  // never a poster. Reduced-motion users get posters by design, so every
  // slide counts as ready for them. If a film script fails to load, its
  // slide also counts as ready (poster fallback) so one dead film can
  // never freeze the carousel.
  var hFilmFailed={};
  function hReady(j){
    if(hReduced)return true;
    var v=hVideos[j];
    if(v)return v.readyState>=2&&!v.paused;
    return !!hFilmFailed[hSlides[j].dataset.film];
  }
  // Called whenever a video starts playing or a film lands: if a manual
  // jump is waiting on that slide, go there; else, if the next slide is
  // ready and the current slide has already shown for a full 5s, advance
  // now instead of waiting for the next timer tick.
  function hMaybeAdvance(){
    if(hPending>=0){
      if(hReady(hPending)){var p=hPending;hPending=-1;hGo(p);hStart();}
      return;
    }
    var nxt=(hIdx+1)%hSlides.length;
    if(hReady(nxt)&&Date.now()-hLastGo>=5000){hGo(nxt);}
  }
  function hWireVideo(j){
    if(hVideos[j]||hReduced)return;
    var s=hSlides[j],key=s.dataset.film,url=hFilmUrl(key);
    if(!url)return;
    var v=document.createElement('video');
    v.className='hero-video';
    v.muted=true;v.loop=true;v.playsInline=true;v.preload='auto';v.autoplay=true;
    v.setAttribute('aria-hidden','true');
    v.addEventListener('playing',function(){s.classList.add('hero-film-on');hMaybeAdvance();});
    v.addEventListener('canplay',function(){if(j===hIdx||j===(hIdx+1)%hSlides.length){hPlayVideo(j);}});
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
    hFilm();
    hMaybeAdvance();
  };
  function hFilm(){
    hSlides.forEach(function(s,j){
      var keep=(j===hIdx)||(j===(hIdx+1)%hSlides.length);
      if(keep&&!hReduced){
        hWireVideo(j);
        var v=hVideos[j];
        // Round 13: PRE-ROLL -- play the next slide's video too (it is
        // hidden, non-active slides are opacity:0, so this is invisible)
        // so it is already playing when the carousel advances to it.
        if(v){hPlayVideo(j);}
      }else{
        var v2=hVideos[j];
        if(v2){v2.pause();}
        s.classList.remove('hero-film-on');
      }
    });
    if(window.__akWireShot){window.__akWireShot();} // Round 14: wire Shot on videos whenever hero films are (re)wired.
  }
  function hGo(i){
    hIdx=(i+hSlides.length)%hSlides.length;
    hLastGo=Date.now();
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
  // Round 13: the queue is a live list -- a manual jump to a film that
  // has not loaded yet (hQueueFilmFirst) moves that film to the FRONT,
  // so a tap never waits behind films the user did not ask for. A film
  // that fails to load is marked failed (hFilmFailed) so its slide
  // falls back to its poster instead of freezing the carousel.
  var hFilmQueue=[],hFilmLoading=null,hFilmLoaded={};
  function hQueueFilm(key){
    if(!key||hFilmLoaded[key]||hFilmLoading===key||hFilmQueue.indexOf(key)>=0)return;
    hFilmQueue.push(key);
  }
  function hQueueFilmFirst(key){
    if(!key||hFilmLoaded[key]||hFilmLoading===key)return;
    var ix=hFilmQueue.indexOf(key);
    if(ix>=0)hFilmQueue.splice(ix,1);
    hFilmQueue.unshift(key);
  }
  // Round 21 -- native-res: the queue advances ONLY when a film has arrived (or
  // failed) -- never on a loader's onload, because a chunk loader's onload
  // fires before its parts land. __heroFilmArrived wires the video;
  // __heroFilmFailed marks the slide as poster-fallback so one dead film
  // can never freeze the carousel.
  var hFilmParts={air3s:1,mavic3pro:3,mini3pro:1,mini4pro:3}; // Round 21 native-res hero parts (manifest)
  window.__heroFilmFailed=function(key){hFilmFailed[key]=1;hMaybeAdvance();};
  function hLoadNextFilm(){
    if(hFilmLoading)return;
    var key=hFilmQueue.shift();
    if(!key)return;
    hFilmLoading=key;
    akLoadFilm(key,'hero',hFilmParts[key]||1,'assets/hero-film/',function(b64){
      window.__HERO_FILMS=window.__HERO_FILMS||{};
      window.__HERO_FILMS[key]=b64;
      hFilmLoaded[key]=1;hFilmLoading=null;
      if(window.__heroFilmArrived)window.__heroFilmArrived(key);
      if(hFilmsDone()){hLoadBelowfoldImages();}
      hLoadNextFilm();
    },function(){
      hFilmFailed[key]=1;hFilmLoading=null;
      if(window.__heroFilmFailed)window.__heroFilmFailed(key);
      if(hFilmsDone()){hLoadBelowfoldImages();}
      hLoadNextFilm();
    });
  }
  (function(){
    var order=[];
    [hIdx,(hIdx+1)%hSlides.length].forEach(function(j){var k=hSlides[j].dataset.film;if(k)order.push(k);});
    ['air3s','mavic3pro','mini3pro','mini4pro'].forEach(function(k){if(order.indexOf(k)<0)order.push(k);});
    order.forEach(function(k){hQueueFilm(k);});
    hLoadNextFilm();
  })();
  // Round 13 -- BELOW-FOLD IMAGES: the 10 product/feature/field-tile photos
  // used to be inline base64 in index.html (1.55MB), so the browser had to
  // download them before it could reach site.js and start the hero films
  // (first motion ~58s on Slow 3G even with the films shrunk). They now
  // live in assets/belowfold-images.js and load only AFTER the hero films
  // are all in -- or when the user scrolls toward them -- so the hero gets
  // the slow pipe first. The tiles show a dark placeholder until then.
  var hBfLoaded=false;
  function hLoadBelowfoldImages(){
    if(hBfLoaded)return;hBfLoaded=true;
    var sc=document.createElement('script');
    sc.src='assets/belowfold-images.js';
    document.head.appendChild(sc);
  }
  function hFilmsDone(){
    var keys=['air3s','mavic3pro','mini3pro','mini4pro'];
    for(var i=0;i<keys.length;i++){if(!hFilmLoaded[keys[i]]&&!hFilmFailed[keys[i]])return false;}
    return true;
  }
  window.addEventListener('scroll',function(){hLoadBelowfoldImages();},{once:true,passive:true});
  // Round 13: the 5s timer advances ONLY to a film-ready slide; if the
  // next film has not arrived yet it stays on the current (playing)
  // slide and tries again on the next tick -- the hero never shows a
  // poster after the first motion.
  function hTryAdvance(){
    var nxt=(hIdx+1)%hSlides.length;
    if(hReady(nxt)){hGo(nxt);}
    else{hFilm();}
  }
  function hStart(){hStop();hTimer=setInterval(function(){hTryAdvance();},5000);}
  function hStop(){if(hTimer){clearInterval(hTimer);hTimer=null;}}
  // Manual navigation: switch at once if the target film is ready;
  // otherwise wait for it -- jump its film to the front of the load
  // queue and switch the moment it plays.
  function hRequestGo(i){
    var t=(i+hSlides.length)%hSlides.length;
    if(hReady(t)){hPending=-1;hGo(t);hStart();}
    else{hPending=t;hQueueFilmFirst(hSlides[t].dataset.film);hLoadNextFilm();hFilm();}
  }
  hList.forEach(function(b){b.addEventListener('click',function(){hRequestGo(parseInt(b.dataset.go,10));});});
  hc.querySelectorAll('.hero-arrow').forEach(function(a){a.addEventListener('click',function(){hRequestGo(hIdx+parseInt(a.dataset.dir,10));});});
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
  // Round 20 -- hero parallax (CGI feel): the playing film drifts down
  // slower than the page scroll. Only the film (it has no CSS animation);
  // the poster keeps its kb-zoom and sits behind, so no gap ever shows.
  // Reduced-motion: off.
  if(!hReduced){
    var hParTicking=false;
    function hParallax(){
      hParTicking=false;
      var y=window.scrollY||0;
      var off=y>330?40:Math.round(y*0.12);
      var vs=hc.querySelectorAll('video.hero-video');
      for(var i=0;i<vs.length;i++){vs[i].style.transform='translateY('+off+'px)';}
    }
    window.addEventListener('scroll',function(){if(!hParTicking){hParTicking=true;requestAnimationFrame(hParallax);}},{passive:true});
  }
}
// films carousel: FULL-BLEED films (DJI "Shot on"), ‹ › arrows at
// mid-height on the video edges, dash indicators below.
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
  // Round 20 -- films FULL-BLEED (DJI): each film fills the whole
  // carousel width, no peeking side cards; the track slides by exactly
  // one card width.
  function fLayout(){
    var cardW=fCards[0].getBoundingClientRect().width;
    fTrack.style.transform='translateX('+(-fIdx*cardW)+'px)';
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

// Round 23 -- YouTube hero fallback: the 8 detail pages with a YouTube
// iframe hero (agras, air-3, avata-2, matrice-30t, mini-2, mini-3,
// mini-5-pro, neo) show a dead grey error surface when youtube.com is
// unreachable -- YouTube is blocked on the boss's own network, so the
// hero looks dead to him. Probe the video's thumbnail (same i.ytimg.com
// host the film facades already use); on error/timeout hide the iframe
// and let the bg photo show with Ken Burns, so the hero stays alive.
// On a network where YouTube loads, nothing changes.
(function(){
  var frames=document.querySelectorAll('iframe.detail-hero-yt');
  if(!frames.length)return;
  frames.forEach(function(f){
    var m=(f.src||'').match(/\/embed\/([A-Za-z0-9_-]{6,})/);
    if(!m)return;
    var hero=f.closest('.detail-hero');
    if(!hero)return;
    var done=false,img=new Image(),t=setTimeout(fail,4000);
    function fail(){if(done)return;done=true;hero.classList.add('yt-dead');hero.classList.add('kenburns');}
    img.onload=function(){if(done)return;done=true;clearTimeout(t);};
    img.onerror=fail;
    img.src='https://i.ytimg.com/vi/'+m[1]+'/hqdefault.jpg';
  });
})();

// Round 29 -- DJI-Store buy layout (product pages only): gallery thumbs,
// video tab, variant cards, quantity stepper, WhatsApp order link.
(function(){
  var buy=document.querySelector('.buy'); if(!buy) return;
  var mainImg=buy.querySelector('.buy-main-img');
  var film=buy.querySelector('.buy-film');
  var thumbs=Array.prototype.slice.call(buy.querySelectorAll('.buy-thumb'));
  function setActive(btn){thumbs.forEach(function(t){t.classList.toggle('is-active',t===btn);});}
  function showPhoto(btn){
    if(film){film.hidden=true;if(film.tagName==='VIDEO'){film.pause();}}
    if(mainImg){mainImg.hidden=false;mainImg.src=btn.getAttribute('data-src');}
    setActive(btn);
  }
  function showVideo(btn){
    if(!film)return;
    if(mainImg){mainImg.hidden=true;}
    film.hidden=false;
    if(film.tagName==='VIDEO'){var p=film.play();if(p&&p.catch){p.catch(function(){});}}
    setActive(btn);
  }
  thumbs.forEach(function(t){
    t.addEventListener('click',function(){
      if(t.getAttribute('data-kind')==='video'){showVideo(t);}else{showPhoto(t);}
    });
  });
  var orderLink=document.getElementById('waOrder');
  var qtyEl=document.getElementById('buyQty');
  var productName=buy.getAttribute('data-name')||'';
  var productPrice=buy.getAttribute('data-price')||'';
  function orderText(){
    var qty=qtyEl?parseInt(qtyEl.textContent,10)||1:1;
    var v=buy.querySelector('.buy-variant.is-active');
    var variant=v?v.getAttribute('data-variant'):'';
    var msg='Assalam-o-Alaikum! I would like to order '+productName;
    if(variant){msg+=' — '+variant;}
    msg+='. Quantity: '+qty+'.';
    if(productPrice){msg+=' Price: '+productPrice+'.';}
    msg+=' Please confirm the price, availability and delivery.';
    return msg;
  }
  function refreshOrder(){
    if(orderLink){orderLink.href='https://wa.me/923067000682?text='+encodeURIComponent(orderText());}
  }
  var variants=Array.prototype.slice.call(buy.querySelectorAll('.buy-variant'));
  variants.forEach(function(v){
    v.addEventListener('click',function(){
      variants.forEach(function(x){x.classList.toggle('is-active',x===v);});
      refreshOrder();
    });
  });
  var minus=document.getElementById('qtyMinus'),plus=document.getElementById('qtyPlus');
  function setQty(n){n=Math.max(1,Math.min(99,n));if(qtyEl){qtyEl.textContent=String(n);}refreshOrder();}
  if(minus){minus.addEventListener('click',function(){setQty((parseInt(qtyEl.textContent,10)||1)-1);});}
  if(plus){plus.addEventListener('click',function(){setQty((parseInt(qtyEl.textContent,10)||1)+1);});}
  refreshOrder();
})();
