LATEXMK ?= latexmk
LATEXFLAGS = -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build

.PHONY: all slides notes clean
all: slides notes

slides: helion_slides.pdf
notes: helion_presenter.pdf

helion_slides.pdf: helion_slides.tex speaker_notes.tex
	mkdir -p build
	$(LATEXMK) $(LATEXFLAGS) helion_slides.tex
	cp build/helion_slides.pdf $@

helion_presenter.pdf: helion_presenter.tex helion_slides.tex speaker_notes.tex
	mkdir -p build
	$(LATEXMK) $(LATEXFLAGS) helion_presenter.tex
	cp build/helion_presenter.pdf $@

clean:
	$(LATEXMK) -C -outdir=build helion_slides.tex helion_presenter.tex
