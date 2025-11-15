# Open Code Model Configurator

A CLI tool for managing Opencode configuration. Switch, add, delete, set different AI models and providers.

## Features

```sh
ocs --help
usage: ocs [-h] [--config CONFIG] {ls,show,update,change,add,delete} ...

Open Code Model Configurator

positional arguments:
  {ls,show,update,change,add,delete}
                        Available commands
    ls                  List all models grouped by provider
    show                Show current model configuration
    update              Update models by querying provider /v1/models endpoints
    change              Change the model configuration value
    add                 Add provider or model
    delete              Delete provider or model

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to config file (default: ~/.config/opencode/config.json)
```


## Fast Install
Install uv:
https://docs.astral.sh/uv/getting-started/installation/

Install CLI:
```
uv tool install git+https://github.com/eleqtrizit/Opencode-Model-Configurator.git
```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager



### Env Setup

Clone the repository:
```bash
git clone https://github.com/eleqtrizit/Opencode-Model-Configurator.git
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

