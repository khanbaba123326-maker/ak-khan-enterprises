
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
if(dp){dp.addEventListener('click',function(){openLB(dp.querySelector('img').src,dp.querySelector('img').alt);});}
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
// hero carousel: rotating stills, ~5s autoplay, crossfade, bottom-left
// prev / current / next slide list; click a list name to jump; pause on
// real mouse hover only — touch never pauses (see below).
var hc=document.getElementById('heroCarousel');
if(hc){
  var hSlides=Array.prototype.slice.call(hc.querySelectorAll('.hero-slide'));
  var hList=hc.querySelectorAll('.hero-list button');
  var hIdx=0,hTimer=null;
  function hGo(i){
    hIdx=(i+hSlides.length)%hSlides.length;
    hSlides.forEach(function(s,j){s.classList.toggle('active',j===hIdx);});
    var prev=(hIdx-1+hSlides.length)%hSlides.length,next=(hIdx+1)%hSlides.length;
    if(hList.length===3){
      hList[0].textContent=hSlides[prev].dataset.name;hList[0].dataset.go=prev;
      hList[1].textContent=hSlides[hIdx].dataset.name;hList[1].dataset.go=hIdx;
      hList[2].textContent=hSlides[next].dataset.name;hList[2].dataset.go=next;
    }
  }
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
  document.addEventListener('visibilitychange',function(){if(document.hidden){hStop();}else{hStart();}});
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
