const questionEl=document.getElementById('question');
const askButton=document.getElementById('ask');
const resultEl=document.getElementById('result');

async function ask(){
  const question=questionEl.value.trim();
  if(question.length<2){questionEl.focus();return;}
  askButton.disabled=true;
  askButton.textContent='검색 중...';
  resultEl.innerHTML='<div class="empty"><span>···</span><p>관련 영화 리뷰를 검색하고 답변을 생성하고 있습니다.</p></div>';
  try{
    const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'요청에 실패했습니다.');
    const sources=(data.sources||[]).map(s=>`<article class="source">
      <strong>${escapeHtml(s.movie_title||'영화')} · ${escapeHtml(s.title||'리뷰')}</strong>
      <p>${escapeHtml(s.text||'')}</p>
      <small>리뷰 ID: ${escapeHtml(s.review_id||'')}</small>
      <a href="${escapeAttr(s.url||'https://github.com/madison-yoon/MOMO')}" target="_blank" rel="noopener">데이터 출처 ↗</a>
    </article>`).join('');
    resultEl.innerHTML=`<div class="answer-card"><h3>ANSWER / 답변</h3><div class="answer">${escapeHtml(data.answer||'답변이 없습니다.')}</div><h3 style="margin-top:30px">SOURCES / 검색된 리뷰</h3>${sources||'<p>검색된 리뷰가 없습니다.</p>'}</div>`;
  }catch(error){resultEl.innerHTML=`<div class="empty"><p>${escapeHtml(error.message)}</p></div>`;}
  finally{askButton.disabled=false;askButton.innerHTML='리뷰 검색 <span>→</span>';}
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function escapeAttr(value){return escapeHtml(value);}
askButton.addEventListener('click',ask);
questionEl.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}});
document.querySelectorAll('[data-q]').forEach(button=>button.addEventListener('click',()=>{questionEl.value=button.dataset.q;ask();}));
