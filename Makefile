REPOSITORY=us-central1-docker.pkg.dev/molten-verve-216720/honey-pwhale/

.PHONY: sunfish up down

sunfish:
	podman build -f antithesis/config/Dockerfile.sut -t ${REPOSITORY}sunfish:latest .

config:
	podman build -f antithesis/config/Dockerfile.config -t ${REPOSITORY}sunfish:latest .

down:
	docker-compose -f antithesis/config/docker-compose.yaml down

up: down
	docker-compose -f antithesis/config/docker-compose.yaml up