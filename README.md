# Film Creation Tool

## Project Overview
The Film Creation Tool is a desktop application designed to streamline the film production process by integrating with the Frame.io API for efficient project management. It combines a powerful FastAPI backend with an intuitive Electron frontend, enhanced by React and Chakra UI. This tool offers features such as project creation, media upload, sequence management, and leverages GPT-4 for intelligent project naming and organization suggestions.

## Features
- Project creation and management
- Media upload and organization
- Sequence and shot management
- Real-time collaboration through Frame.io integration
- GPT-4 powered project naming and organization suggestions
- Cross-platform desktop application (Windows, macOS, Linux)

## Installation Instructions

### Backend (FastAPI)
1. Ensure you have Python 3.10 or later installed.
2. Navigate to the backend directory:
   ```
   cd /home/ubuntu/film_creation_tool/
   ```
3. Install Poetry (if not already installed):
   ```
   pip install poetry
   ```
4. Install dependencies:
   ```
   poetry install
   ```

### Frontend (Electron + React)
1. Ensure you have Node.js (LTS version) installed.
2. Navigate to the frontend directory:
   ```
   cd /home/ubuntu/film_creation_tool/film-creation-tool-frontend/
   ```
3. Install dependencies:
   ```
   npm install
   ```

## Usage Instructions

### Setting up Environment Variables
Before running the application, make sure to set the following environment variables:
- `FrameAPI`: Your Frame.io API token
- `GPT4_API_KEY`: Your OpenAI GPT-4 API key

### Running the Backend
1. Navigate to the backend directory.
2. Activate the Poetry environment:
   ```
   poetry shell
   ```
3. Start the FastAPI server:
   ```
   uvicorn film_creation_tool.app:app --host 0.0.0.0 --port 8000
   ```

### Running the Frontend
1. Navigate to the frontend directory.
2. Start the Electron application:
   ```
   npm start
   ```

## Contributing
We welcome contributions to the Film Creation Tool! Please read our contributing guidelines before submitting pull requests.

## Support
For support, please open an issue on our GitHub repository or contact our support team at support@filmcreationtool.com.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
