# MyLatexPaper

Files:

- `main.tex`: conference paper source
- `references.bib`: bibliography
- `IEEEtran.cls`: copied from the conference template
- `figures/`: architecture images and PGFPlots chart snippets

Recommended build sequence on a machine with TeX installed:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Or with `latexmk`:

```bash
latexmk -pdf main.tex
```

Note:

- This workspace does not currently have `pdflatex` or `bibtex` installed, so the project was prepared structurally but not compiled locally.
