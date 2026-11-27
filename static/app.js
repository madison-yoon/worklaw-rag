const $ = (selector) => document.querySelector(selector);
const status = $("#status");
const ingest = $("#ingest");
const ask = $("#ask");
const result = $("#result");

async function refresh() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "상태 확인 실패");
    const indexLabel = data.vector_index_ready ? "인덱스 준비 완료" : "인덱스 준비 중";
    status.textContent = `MongoDB Atlas · 청크 ${data.indexed_chunks.toLocaleString()}개 · ${indexLabel}`;
  } catch (error) {
    status.textContent = error.message;
  }
}

ingest.onclick = async () => {
  ingest.disabled = true;
  ingest.textContent = "수집 및 임베딩 중…";
  status.textContent = "공식 문서를 수집해 MongoDB Atlas에 저장하고 있습니다.";
  try {
    const response = await fetch("/api/ingest", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "문서 수집 실패");
    status.textContent = `페이지 ${data.pages_fetched}개 · 청크 ${data.chunks_indexed}개 · Vector Index ${data.vector_index?.queryable ? "준비 완료" : "생성 중"}`;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    ingest.disabled = false;
    ingest.textContent = "공식 문서 수집 및 색인";
    await refresh();
  }
};

ask.onclick = async () => {
  const question = $("#question").value.trim();
  if (question.length < 2) {
    alert("질문을 2자 이상 입력하세요.");
    return;
  }
  ask.disabled = true;
  ask.textContent = "검색 중…";
  result.className = "result show";
  result.textContent = "MongoDB Atlas에서 관련 문서를 검색하고 답변을 생성합니다.";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "질의 처리 실패");

    result.replaceChildren();
    const heading = document.createElement("h2");
    heading.textContent = "답변";
    const answer = document.createElement("div");
    answer.className = "answer";
    answer.textContent = data.answer;
    result.append(heading, answer);

    const section = document.createElement("div");
    section.className = "sources";
    const sourceHeading = document.createElement("h2");
    sourceHeading.textContent = "검색 근거";
    section.append(sourceHeading);
    data.sources.forEach((source, index) => {
      const row = document.createElement("div");
      row.className = "source";
      const link = document.createElement("a");
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `[${index + 1}] ${source.title}`;
      const score = document.createElement("span");
      score.textContent = `유사도 ${source.score}`;
      row.append(link, score);
      section.append(row);
    });
    result.append(section);
  } catch (error) {
    result.textContent = error.message;
  } finally {
    ask.disabled = false;
    ask.textContent = "질문하기 ↗";
  }
};

refresh();
