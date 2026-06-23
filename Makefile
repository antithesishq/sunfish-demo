REPOSITORY=us-central1-docker.pkg.dev/molten-verve-216720/honey-pwhale-repository/

.PHONY: sunfish config up down push

sunfish:
	podman build -f antithesis/config/Dockerfile.sut -t ${REPOSITORY}sunfish:latest .

config:
	podman build -f antithesis/config/Dockerfile.config -t ${REPOSITORY}sunfish-config:latest .

down:
	docker-compose -f antithesis/config/docker-compose.yaml down

up: down
	docker-compose -f antithesis/config/docker-compose.yaml up

.ONESHELL:
push:
	cd ~/src/customer/customer-honey-whale
	customer credentials_shell -c " \
	podman push $(REPOSITORY)sunfish-config:latest && \
	podman push $(REPOSITORY)sunfish:latest"