const questionEl=document.getElementById('question');
const askButton=document.getElementById('ask');
const resultEl=document.getElementById('result');
const recommendationEl=document.getElementById('recommendation-list');

async function ask(){
  const question=questionEl.value.trim();
  if(question.length<2){questionEl.focus();return;}
  askButton.disabled=true;
  askButton.textContent='검색 중...';
  resultEl.innerHTML='<div class="empty"><span>···</span><p>관련 영화와 리뷰 근거를 검색하고 있습니다.</p></div>';
  try{
    const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'요청에 실패했습니다.');
    const sources=(data.sources||[]).map(s=>'<article class="source"><strong>'+escapeHtml(s.movie_title||'영화')+' · '+escapeHtml(s.title||'리뷰')+'</strong><small>'+escapeHtml([s.genre,s.director,s.release_date].filter(Boolean).join(' · '))+' · 리뷰 ID: '+escapeHtml(s.review_id||'')+'</small><p>'+escapeHtml(s.text||'')+'</p><a href="'+escapeAttr(s.url||'https://github.com/madison-yoon/MOMO')+'" target="_blank" rel="noopener">MOMO 데이터 출처 ↗</a></article>').join('');
    resultEl.innerHTML='<div class="answer-card"><h3>AI ANSWER / 답변</h3><div class="answer">'+escapeHtml(data.answer||'답변이 없습니다.')+'</div><h3 style="margin-top:30px">REVIEW SOURCES / 검색 근거</h3>'+(sources||'<p>검색된 리뷰가 없습니다.</p>')+'</div>';
  }catch(error){resultEl.innerHTML='<div class="empty"><p>'+escapeHtml(error.message)+'</p></div>';}
  finally{askButton.disabled=false;askButton.innerHTML='AI 검색 <span>→</span>';}
}
async function loadRecommendations(genre){
  recommendationEl.innerHTML='<p class="recommendation-message">MOMO 추천 목록을 불러오는 중입니다.</p>';
  try{
    const url=genre?'/api/recommendations?genre='+encodeURIComponent(genre):'/api/recommendations';
    const response=await fetch(url);
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'추천 목록을 불러오지 못했습니다.');
    const movies=data.movies||[];
    if(!movies.length){recommendationEl.innerHTML='<p class="recommendation-message">현재 추천 후보가 없습니다. MOMO 백엔드의 박스오피스 추천 데이터를 확인하세요.</p>';return;}
    recommendationEl.innerHTML=movies.map(movie=>{
      const poster=movie.posterUrl&&/^https?:\/\//i.test(movie.posterUrl)?'<img src="'+escapeAttr(movie.posterUrl)+'" alt="" loading="lazy">':'<div class="poster-placeholder">M</div>';
      const rank=movie.bestBoxOfficeRank?'최고 순위 '+escapeHtml(movie.bestBoxOfficeRank):'MOMO 추천 후보';
      return '<article class="recommendation-card">'+poster+'<div><strong>'+escapeHtml(movie.title||'제목 미상')+'</strong><p>'+escapeHtml([movie.genre,movie.releaseDate].filter(Boolean).join(' · '))+'</p><small>'+rank+'</small></div></article>';
    }).join('');
  }catch(error){recommendationEl.innerHTML='<p class="recommendation-message">'+escapeHtml(error.message)+'</p>';}
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function escapeAttr(value){return escapeHtml(value);}
askButton.addEventListener('click',ask);
questionEl.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}});
document.querySelectorAll('[data-q]').forEach(button=>button.addEventListener('click',()=>{questionEl.value=button.dataset.q;ask();}));
document.querySelectorAll('[data-genre]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-genre]').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  loadRecommendations(button.dataset.genre);
}));
loadRecommendations('');
