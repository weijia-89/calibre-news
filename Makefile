# Convenience Makefile for calibre-news

all:
	python3 -m calibre_news.build

tech:
	python3 -m calibre_news.build --subject tech

consumer:
	python3 -m calibre_news.build --subject consumer

security:
	python3 -m calibre_news.build --subject security

local:
	python3 -m calibre_news.build --subject local

news:
	python3 -m calibre_news.build --subject news

prune:
	python3 -m calibre_news.build --prune-only

dry-run:
	python3 -m calibre_news.build --dry-run

.PHONY: all tech consumer security local news prune dry-run