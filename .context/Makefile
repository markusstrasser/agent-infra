# Context views for cross-model review
# Usage: make [target]  — generates .xml views from working tree
# Targets rebuild only when source files change (Make dependency tracking)

SHELL := /bin/bash
PROJECT_ROOT := $(shell cd .. && pwd)
REPOMIX := repomix --quiet --style xml --no-security-check --no-git-sort-by-changes

# Source file sets
MD_FILES := $(shell find $(PROJECT_ROOT) -maxdepth 2 -name '*.md' -not -path '*/.context/*' -not -path '*/.claude/*' -not -path '*/node_modules/*' 2>/dev/null)
SCRIPT_FILES := $(shell find $(PROJECT_ROOT)/scripts -name '*.py' -o -name '*.sh' 2>/dev/null)
ALL_FILES := $(MD_FILES) $(SCRIPT_FILES)

.PHONY: all clean filetree diffs

all: full.xml constitution.xml docs.xml infra.xml filetree.xml

# Full project context — everything relevant
full.xml: $(ALL_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "CLAUDE.md,GOALS.md,**/*.md,scripts/**" \
		--ignore ".context/**,.claude/**,.model-review/**/*.md,node_modules/**,downloads/**" \
		-o .context/$@

# Constitution + goals — stable prefix for prompt caching
constitution.xml: $(PROJECT_ROOT)/CLAUDE.md $(PROJECT_ROOT)/GOALS.md
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "CLAUDE.md,GOALS.md" \
		--no-directory-structure \
		-o .context/$@

# All documentation — research memos, architecture docs
docs.xml: $(MD_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "**/*.md" \
		--ignore ".context/**,.claude/**,.model-review/**" \
		-o .context/$@

# Infrastructure — scripts, hooks
infra.xml: $(SCRIPT_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "scripts/**" \
		-o .context/$@

# Directory structure only — cheap overview
filetree.xml:
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--no-files --no-file-summary \
		--ignore ".context/**,.claude/**,node_modules/**,downloads/**" \
		-o .context/$@

# Git diffs — current uncommitted changes
diffs.xml:
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--no-files --no-file-summary --no-directory-structure \
		--include-diffs \
		-o .context/$@

clean:
	rm -f *.xml
