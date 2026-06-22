(function () {
  const depth = window.location.pathname.split("/").filter(Boolean).length;
  const root = depth <= 1 ? "." : depth === 2 ? ".." : "../..";

  const nav = document.getElementById("navbar");
  if (!nav) return;

  nav.innerHTML = `
    <a class="nav-logo" href="${root}/index.html">Knowledge<span style="color:#fbbf24">Master</span></a>
    <div class="nav-links">
      <a href="${root}/index.html">Home</a>
      <a href="${root}/presentation/graph.html">Master Graph</a>
      <a href="${root}/exam/quiz.html">Random Exam</a>
    </div>
  `;
})();
