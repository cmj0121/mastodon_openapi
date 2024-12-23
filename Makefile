PYTHON := python3.13
VENV   := .venv
SPEC   := mastodon-openapi.yaml

.PHONY: all clean build test run upgrade help $(SUBDIR)

all: $(SUBDIR) 		# default action
	@[ -f .git/hooks/pre-commit ] || pre-commit install --install-hooks
	@git config commit.template .git-commit-template

clean: $(SUBDIR)	# clean-up environment
	@find . -name '*.sw[po]' -o -name '*.pyc' -delete
	@find . -name __pycache__ -delete

build: $(VENV)		# build the binary/library
	poetry run python src/tools.py -o $(SPEC)

test: $(VENV)		# run the tests
	poetry run pytest

run: 				# run the Swagger UI
	docker run \
		-p 8080:8080 \
		-e SWAGGER_JSON=/app/swagger.json \
		-v $(PWD)/$(SPEC):/app/swagger.json \
		swaggerapi/swagger-ui

upgrade:			# upgrade all the necessary packages
	pre-commit autoupdate

help:				# show this message
	@printf "Usage: make [OPTION]\n"
	@printf "\n"
	@perl -nle 'print $$& if m{^[\w-]+:.*?#.*$$}' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?#"} {printf "    %-18s %s\n", $$1, $$2}'

$(SUBDIR):
	$(MAKE) -C $@ $(MAKECMDGOALS)

$(VENV):
	@$(PYTHON) -m venv $(VENV)
	@poetry install
