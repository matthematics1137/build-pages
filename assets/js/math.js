// KaTeX auto-render initialization scoped to .md-content
(function(){
  function init(){
    if (!window.renderMathInElement) return;
    document.querySelectorAll('.md-content').forEach(el => {
      window.renderMathInElement(el, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false},
          {left: '\\(', right: '\\)', display: false},
          {left: '\\[', right: '\\]', display: true}
        ],
        throwOnError: false,
        macros: {
          "\\R": "\\mathbb{R}",
          "\\RR": "\\mathbb{R}",
          "\\N": "\\mathbb{N}",
          "\\NN": "\\mathbb{N}",
          "\\Z": "\\mathbb{Z}",
          "\\ZZ": "\\mathbb{Z}",
          "\\Q": "\\mathbb{Q}",
          "\\QQ": "\\mathbb{Q}",
          "\\E": "\\mathbb{E}",
          "\\Var": "\\mathrm{Var}",
          "\\Cov": "\\mathrm{Cov}",
          "\\Prob": "\\mathbb{P}",
          "\\argmax": "\\mathop{\\mathrm{arg\\,max}}",
          "\\argmin": "\\mathop{\\mathrm{arg\\,min}}",
          "\\func": "\\operatorname{func}"
        }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
