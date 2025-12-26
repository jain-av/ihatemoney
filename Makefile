VIRTUALENV = uv venv
VENV := $(shell realpath $${VIRTUAL_ENV-.venv})
BIN := uv tool run
PIP := uv pip
PYTHON = $(BIN)/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)
ZOPFLIPNG := zopflipng
MAGICK_MOGRIFY := mogrify

.PHONY: virtualenv
virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

.PHONY: serve
serve: build-translations
	@echo 'Running ihatemoney on http://localhost:5000'
	FLASK_DEBUG=1 FLASK_APP=ihatemoney.wsgi uv run flask run --host=0.0.0.0

.PHONY: test
test:
	uv run --extra dev --extra database pytest .

.PHONY: lint
lint:
	uv tool run ruff check .
	uv tool run vermin --no-tips --violations -t=3.8- .

.PHONY: format
format: 
	uv tool run ruff format .

.PHONY: release
release:
		uv run --extra dev fullreleas

.PHONY: compress-showcase
compress-showcase:
	@which $(MAGICK_MOGRIFY) >/dev/null || (echo "ImageMagick 'mogrify' ($(MAGICK_MOGRIFY)) is missing" && exit 1)
	$(MAGICK_MOGRIFY) -format webp -resize '75%>' -quality 50 -define webp:method=6:auto-filter=true -path ihatemoney/static/showcase/ 'assets/showcase/*.jpg'

.PHONY: compress-assets
compress-assets: compress-showcase
	@which $(ZOPFLIPNG) >/dev/null || (echo "ZopfliPNG ($(ZOPFLIPNG)) is missing" && exit 1)
	mkdir $(TEMPDIR)/zopfli
	$(eval CPUCOUNT := $(shell python -c "import psutil; print(psutil.cpu_count(logical=False))"))
	cd ihatemoney/static/images/; find -name '*.png' -printf '%f\0' | xargs --null --max-args=1 --max-procs=$(CPUCOUNT) $(ZOPFLIPNG) --iterations=500 --filters=01234mepb --lossy_8bit --lossy_transparent --prefix=$(TEMPDIR)/zopfli/
	mv $(TEMPDIR)/zopfli/* ihatemoney/static/images/

.PHONY: build-translations
build-translations:
	uv run --extra dev pybabel compile -d ihatemoney/translations

.PHONY: extract-translations
extract-translations:
	uv run --extra dev pybabel extract --add-comments "I18N:" --strip-comments --omit-header --no-location --mapping-file ihatemoney/babel.cfg -o ihatemoney/messages.pot ihatemoney
	uv run --extra dev pybabel update -i ihatemoney/messages.pot -d ihatemoney/translations/

.PHONY: create-database-revision
create-database-revision:
	@read -p "Please enter a message describing this revision: " rev_message; \
	uv run python -m ihatemoney.manage db migrate -d ihatemoney/migrations -m "$${rev_message}"

.PHONY: create-empty-database-revision
create-empty-database-revision:
	@read -p "Please enter a message describing this revision: " rev_message; \
	uv run python -m ihatemoney.manage db revision -d ihatemoney/migrations -m "$${rev_message}"

.PHONY: clean
clean:
	rm -rf .venv

build-docs:
	uv run --extra doc sphinx-build -a -n -b html -d docs/_build/doctrees docs docs/_build/html

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
