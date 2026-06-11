# Contributing to JobScout-Lite

We love contributions! Whether you are reporting a bug, proposing a new scraping portal, or optimizing local model prompt engineering, your help is highly appreciated.

Here is a quick guide on how to get started.

## How Can I Contribute?

### 1. Reporting Bugs
- Search existing issues first before creating a new one.
- Provide a clear, descriptive title.
- Detail the steps to reproduce the issue, your environment setup, and your Ollama model configurations.

### 2. Submitting Pull Requests
1. **Fork** the repository and create your branch from `main`.
2. **Setup your environment** locally and verify your changes.
3. Make sure to **never commit your credentials** (`.env`) or your personal resume/profile markdown files.
4. Keep the code style clean:
   - Use `asyncio` and `httpx` for async/network processes.
   - Comment your code logic clearly.
5. Submit a pull request describing your changes and what problem they solve.

## Code Style Guide
- **Python**: Use Python 3.10+ PEP 8 coding standards. Use type annotations where appropriate.
- **Asynchronous Flow**: Maintain the `asyncio` pattern for API servers and web scrapers. Keep server pings polite with reasonable sleep delay timers.
- **Documentation**: If your PR modifies setup steps, update the `README.md` and `ARCHITECTURE.md` accordingly.

Thank you for contributing! 🌟
