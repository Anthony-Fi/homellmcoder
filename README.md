# HomeLLMCoder

A high-performance, offline-first desktop application with AI capabilities, built with modern technologies.

## Features

- 🚀 **Offline-First** - Full functionality without internet connection
- 🛠 **Integrated Development Environment** - Code editor, terminal, and file explorer
- 🤖 **AI-Powered** - Built-in LLM capabilities
- 📊 **Data Visualization** - Interactive charts and graphs
- 🔒 **Secure** - Local data storage with encryption
- 🌍 **Multi-platform** - Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git
- pip (Python package manager)

### Installation

#### Windows
1. Open PowerShell as Administrator
2. Clone the repository:
   ```powershell
   git clone https://github.com/Anthony-Fi/homellmcoder
   cd homellmcoder
   ```
3. Run the setup script:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
   .\setup.ps1
   ```

#### macOS/Linux
1. Open Terminal
2. Clone the repository:
   ```bash
   git clone https://github.com/Anthony-Fi/homellmcoder
   cd homellmcoder
   ```
3. Make the setup script executable and run it:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

## 🚀 Building for v0.02

### Prerequisites
- Python 3.9+
- Ollama (for local LLM)

### Installation

1. **Download the latest release**
   - Download `HomeLLMCoder-v0.02-windows.zip` from the [Releases](https://github.com/Anthony-Fi/homellmcoder/releases) page
   - Extract the zip file to your desired location
   - Run `HomeLLMCoder-v0.02.exe`

### Building from Source

1. **Clone the repository**
   ```bash
   git clone https://github.com/Anthony-Fi/homellmcoder
   cd homellmcoder
   git checkout v0.02  # Checkout the v0.02 tag
   ```

2. **Set up a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python src/main.py
   ```

## 🛠 Building a Distribution

To create a standalone executable:

1. Install build dependencies:
   ```bash
   pip install pyinstaller pywin32
   ```

2. Run the build script:
   ```bash
   python build.py
   ```

3. The distributable zip file will be created in the project root.

## 🛠 Development

### Virtual Environment

#### Activating the Environment
- **Windows**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

#### Deactivating the Environment
```bash
deactivate
```

### Running the Application

1. Ensure the virtual environment is activated
2. Start the development server:
   ```bash
   python src/index.py
   ```
3. Open your browser to `http://localhost:3000`

### Installing Dependencies

- **Python Dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
  
- **Development Dependencies**:
  ```bash
  pip install -r requirements-dev.txt
  ```

- **Node.js Dependencies**:
  ```bash
  npm install
  ```

## 🧪 Testing

Run the test suite:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/<test_file>.py -v
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💬 Support

For support or questions, please open an issue in the [GitHub repository](https://github.com/Anthony-Fi/homellmcoder/issues).

## Project Structure

```
homellmcoder/
├── .github/            # GitHub workflows and CI/CD
├── src/                # Source code
│   ├── assets/        # Static files (images, styles)
│   ├── components/    # Reusable UI components
│   ├── pages/         # Application pages
│   ├── services/      # API and service integrations
│   └── utils/         # Utility functions
├── tests/             # Test files
├── .gitignore         # Git ignore file
├── package.json       # Node.js dependencies
├── requirements.txt   # Python dependencies
├── setup.ps1          # Windows setup script
└── setup.sh           # Unix/Linux setup script
