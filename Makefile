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

test-sync:			# download the test HTML
	wget https://docs.joinmastodon.org/methods/accounts/              -O src/tests/html/api_accounts.html
	wget https://docs.joinmastodon.org/methods/admin/                 -O src/tests/html/api_admin.html
	wget https://docs.joinmastodon.org/methods/apps/                  -O src/tests/html/api_apps.html
	wget https://docs.joinmastodon.org/methods/bookmarks/             -O src/tests/html/api_bookmarks.html
	wget https://docs.joinmastodon.org/methods/filters/               -O src/tests/html/api_filters.html
	wget https://docs.joinmastodon.org/methods/grouped_notifications/ -O src/tests/html/api_grouped_notifications.html
	wget https://docs.joinmastodon.org/methods/instance/              -O src/tests/html/api_instance.html
	wget https://docs.joinmastodon.org/methods/admin/ip_blocks/       -O src/tests/html/api_ip_blocks.html
	wget https://docs.joinmastodon.org/entities/Account/              -O src/tests/html/component_account.html
	wget https://docs.joinmastodon.org/entities/Admin_Account/		  -O src/tests/html/component_admin_account.html

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
