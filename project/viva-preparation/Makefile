LATEXMK ?= latexmk

.PHONY: all clean

all: hbm_defects.pdf problem_framing.pdf

hbm_defects.pdf: hbm_defects.tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error hbm_defects.tex

problem_framing.pdf: problem_framing.tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error problem_framing.tex

clean:
	$(LATEXMK) -C hbm_defects.tex
	$(LATEXMK) -C problem_framing.tex
