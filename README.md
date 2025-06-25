# Offline Desktop Application

A high-performance, offline-first desktop application built with modern technologies.

## Features

- 🚀 **Offline-First** - Full functionality without internet connection
- 🛠 **Integrated Development Environment** - Code editor, terminal, and file explorer
- 🤖 **AI-Powered** - Built-in LLM capabilities
- 📊 **Data Visualization** - Interactive charts and graphs
- 🔒 **Secure** - Local data storage with encryption
- 🌍 **Multi-platform** - Works on Windows, macOS, and Linux

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/Anthony-Fi/homellmcoder
cd offline-desktop-app

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install

# Build the frontend
npm run build

# Run the application
cd ..
python main.py
```

## Project Structure

```
project/
├── .github/          # GitHub workflows and templates
├── docs/             # Documentation
├── src/              # Source code
│   ├── core/        # Core application logic
│   ├── ui/          # User interface components
│   └── utils/       # Utility functions
├── tests/           # Test suites
└── frontend/        # Frontend source code
```

## Development

### Setup Development Environment
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with hot-reload for development
python -m src.main --dev
```

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository.
