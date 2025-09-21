clean:
	rm -f main.zip authorizer.zip

authorizer:
	cd lambda-authorizer && zip -r ../authorizer.zip .

main:
	pip install --target ./lambda-main -r lambda-main/requirements.txt
	cd lambda-main && zip -r ../main.zip . -x "tests/*"

build: clean authorizer main
