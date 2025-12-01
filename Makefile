clean:
	# TODO: figure out how to add dependencies to cleanup
	rm -f main.zip authorizer.zip verifier.zip

authorizer:
	cd lambda-authorizer && zip -r ../authorizer.zip .

main:
	docker run --rm -v $(PWD):/workspace -w /workspace python:3.14-slim sh -c "\
		pip install --target ./lambda-main -r lambda-main/requirements.txt"
	cd lambda-main && zip -r ../main.zip . -x "tests/*"

verifier:
	cd lambda-verifier && zip -r ../verifier.zip .

build: clean authorizer main verifier
