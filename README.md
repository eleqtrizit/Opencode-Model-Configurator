# Open Code Model Configurator

A CLI tool for managing Opencode configuration. Switch, add, delete, set different AI models and providers for various router types (default, background, think, longContext, webSearch) with a simple command-line interface.

## Features

- List all available models grouped by provider
- View current router configuration
- Change router settings for different use cases
- Set long context threshold for longContext router
- Delete/unset router configurations (except default)
- Add and manage providers and models
- Auto-detect provider when model name is unique


## Fast Install
Install uv:
https://docs.astral.sh/uv/getting-started/installation/

Install CLI:
```
uv tool install git+https://github.com/eleqtrizit/opencode_model_configurator
```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager



### Env Setup

Clone the repository:
```bash
git clone https://github.com/eleqtrizit/opencode_model_configurator
cd opencode_model_configurator
```

Re/Install the package in development mode:
```bash
make install
```

### Running the CLI

Run in development mode without installation:
```bash
make dev
```

### Development Commands

- `make test` - Run tests
- `make lint` - Run linters (flake8, mypy)
- `make format` - Format code with autopep8
- `make clean` - Clean build artifacts

### Usage

#### Basic Commands

**List all available models:**
```bash
ocs ls
```

**Show current router configuration:**
```bash
ocs show
```

#### Router Management

**Change a router setting:**
```bash
# For default router (required - cannot be deleted)
ocs change default anthropic,claude-3-5-sonnet-20241022

# For background tasks
ocs change background anthropic,claude-3-5-haiku-20241022

# For thinking/reasoning tasks
ocs change think openai,o1

# For long context operations
ocs change longContext anthropic,claude-3-5-sonnet-20241022

# For web search tasks
ocs change webSearch openai,gpt-4o
```

**Set long context threshold:**

```bash
# Requires longContext router to be configured first
ocs set-threshold 100000
```

**Delete/unset a router configuration:**

```bash
# Available for: background, think, longContext, webSearch
# Note: default router cannot be deleted
ocs delete router background
```

#### Provider and Model Management

**Add a provider:**

```bash
ocs add provider --name myprovider --base-url https://api.example.com --api-key YOUR_KEY
```

**Add a model to a provider:**

```bash
ocs add model myprovider my-model-name
```

**Delete a provider (with confirmation):**

```bash
ocs delete provider myprovider
```

**Delete a model (with confirmation):**

```bash
ocs delete model my-model-name
```

