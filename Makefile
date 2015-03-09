test: test-sqlite test-postgres test-flake8

test-sqlite: install-dependencies
	python setup.py test

test-postgres: install-dependencies
	python setup.py test_on_postgres

test-flake8:
	pip install flake8
	flake8 .

install-dependencies:
	pip install -r dev_requirements.txt
