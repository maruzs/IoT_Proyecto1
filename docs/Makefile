# Makefile para compilar la documentación LaTeX de Unidad 2
# Requiere: pdflatex, plantuml (opcional)

TEX = pdflatex
TEXFLAGS = -interaction=nonstopmode -halt-on-error
MAIN = informe_u2
PUMLS = $(wildcard img/*.puml)
PUML_OUT = $(PUMLS:.puml=.png)

.PHONY: all clean puml

all: $(MAIN).pdf

# Compilar LaTeX (2 pasadas para referencias cruzadas)
$(MAIN).pdf: $(MAIN).tex
	$(TEX) $(TEXFLAGS) $(MAIN).tex
	$(TEX) $(TEXFLAGS) $(MAIN).tex
	@echo "\n=== Documento listo: $(MAIN).pdf ==="

# Generar PNG desde PlantUML (requiere plantuml.jar)
puml: $(PUML_OUT)

img/%.png: img/%.puml
	plantuml -tpng $<

# Limpiar archivos auxiliares
clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk
	rm -f $(MAIN).pdf
	rm -f img/*.png

# Limpiar todo (incluyendo PDFs)
distclean: clean
	rm -f $(MAIN).pdf
