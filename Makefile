# Variables
PYTHON = venv/bin/python
PIP = venv/bin/pip
MANAGE = $(PYTHON) manage.py

.PHONY: help install migrate run shell clean neo4j-start neo4j-stop

help:
	@echo "Các lệnh khả dụng:"
	@echo "  make install     - Cài đặt thư viện từ requirements.txt"
	@echo "  make migrate     - Makemigrations và Migrate database"
	@echo "  make run         - Chạy Django server"
	@echo "  make neo4j-start - Khởi động Neo4j service (cần sudo)"
	@echo "  make neo4j-stop  - Dừng Neo4j service"
	@echo "  make shell       - Vào Django shell"
	@echo "  make clean       - Xóa các file rác python (__pycache__)"

install:
	$(PIP) install -r requirements.txt

migrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

run:
	$(MANAGE) runserver

shell:
	$(MANAGE) shell

neo4j-start:
	sudo service neo4j start

neo4j-stop:
	sudo service neo4j stop

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete