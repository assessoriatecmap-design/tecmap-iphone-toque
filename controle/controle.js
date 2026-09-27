// O mesmo jeito dos apps sem onclick: UM ouvinte no document (delegação). O iPhone só manda o clique até aqui se o
// elemento tocado parecer clicável.
window.__cliques = [];
document.addEventListener('click', function (e) {
  var el = e.target && e.target.closest ? e.target.closest('[id]') : null;
  window.__cliques.push(el ? el.id : '?');
});
