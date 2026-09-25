.PHONY: build serve clean new

build:
	@python3 build.py

serve: build
	@echo "http://localhost:8000"
	@cd dist && python3 -m http.server 8000

clean:
	@rm -rf dist

# make new SLUG=my-project
new:
	@test -n "$(SLUG)" || (echo "usage: make new SLUG=my-project" && exit 1)
	@n=$$(ls content/projects | wc -l); d=content/projects/$$(printf '%02d' $$(( (n+1)*10 )))-$(SLUG); \
	mkdir -p $$d; \
	printf -- '---\nname: %s\nshort: %s\norg:\nrole:\nperiod:\nstatus: active\nweight: 2\ntags: []\nlinks:\n---\n\nOne sentence summary.\n\n- First detail.\n' \
		"$(SLUG)" "$$(echo $(SLUG) | cut -c1-7 | tr a-z A-Z)" > $$d/index.md; \
	echo "created $$d/index.md"
