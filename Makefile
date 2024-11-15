# Colors
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m

# Project settings
PROJECT_NAME = kbol
BOOKS_DIR = data/books
PROCESSED_DIR = data/processed

.DEFAULT_GOAL := help

.PHONY: help setup demo process-books stats

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup of development environment
	@echo "$(CYAN)Setting up $(PROJECT_NAME)...$(NC)"
	nix-shell --run "poetry install"
	@echo "$(CYAN)Installing Ollama models...$(NC)"
	ollama pull nomic-embed-text
	ollama pull phi3
	@mkdir -p $(BOOKS_DIR) $(PROCESSED_DIR)
	@echo "$(GREEN)Setup complete!$(NC)"

demo: setup ## Run complete demo pipeline with sample book
	@echo "$(CYAN)Running demo pipeline...$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Linking sample books...$(NC)"
	./scripts/link_books.sh
	@echo ""
	
	@echo "$(YELLOW)2. Processing books with embeddings...$(NC)"
	poetry run python -m kbol process
	@echo ""
	
	@echo "$(YELLOW)3. Showing statistics...$(NC)"
	poetry run python -m kbol stats
	@echo ""
	
	@echo "$(YELLOW)4. Generating documentation...$(NC)"
	poetry run python -m kbol prompt . -o README-phi3.md
	poetry run python -m kbol convert README-phi3.md -t org
	@echo ""
	
	@echo "$(GREEN)Demo pipeline complete! Check:$(NC)"
	@echo "- $(BOOKS_DIR) for linked books"
	@echo "- $(PROCESSED_DIR) for processed chunks"
	@echo "- README-phi3.md and README-phi3.org for generated documentation"

load-books: ## Link relevant books from your collection
	@echo "$(CYAN)Linking books...$(NC)"
	./scripts/link_books.sh
	@ls -l $(BOOKS_DIR)

process-books: ## Process books into chunks with embeddings
	@echo "$(CYAN)Processing books...$(NC)"
	poetry run python -m kbol process

stats: ## Show statistics about processed books
	@echo "$(CYAN)Book Processing Statistics:$(NC)"
	poetry run python -m kbol stats

clean: ## Clean generated files and directories
	@echo "$(CYAN)Cleaning project...$(NC)"
	rm -rf $(PROCESSED_DIR)/*
	rm -f README-phi3.md README-phi3.org
	@echo "$(GREEN)Clean complete!$(NC)"
