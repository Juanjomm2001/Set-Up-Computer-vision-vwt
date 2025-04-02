# Computer Vision + Veolia LLM Analysis


This repository provides a **flexible, production-ready** Python application for continuously capturing images (from a local camera or a Reolink IP camera) and analyzing them using Veolia's Secure GPT API.  The core functionality is built around a configurable loop that captures images, sends them for analysis, and manages old images.  While the primary example focuses on detecting water on the floor, you can easily adapt the system to perform **any image-based analysis** by modifying the `prompt` in the `config.yaml` file.

## Table of Contents

*   [Features](#features)
*   [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Installation](#installation)
*   [Project Structure](#project-structure)
*   [Usage](#usage)


## Features

*   **Multiple Camera Support:**  Seamlessly capture images from either:
    *   A local webcam (ideal for development and testing).
    *   A Reolink IP camera (for deployment in real-world environments).
*   **Powerful LLM-based Analysis:** Leverages Veolia's Secure GPT API to perform sophisticated image analysis.
*   **Highly Configurable:**  Easily customize the application's behavior through the `config.yaml` file:
    *   Switch between camera types.
    *   Adjust the image capture interval.
    *   Modify the analysis prompt sent to the Veolia API.
*   **Robust Logging and Cleanup:**
    *   Detailed logging for debugging and monitoring.
    *   Automatic cleanup of old images to prevent storage issues.
*   **Production-Ready Design:**
    *   Modular code organized into separate folders for clarity and maintainability.



## Getting Started

### Prerequisites

1.  **Python 3.9+:**  Ensure you have Python 3.9 or a later version installed.  You can check your Python version by running `python --version` or `python3 --version` in your terminal.
2.  **Veolia Secure GPT Account:**  You'll need a valid Veolia Secure GPT account and the associated credentials:
    *   Client ID
    *   Client Secret
    *   User Email
    *   API Base URL
3.  **Reolink Camera (Optional):** If you plan to use a Reolink IP camera, ensure it's connected to your network and you know its IP address, username, and password.
4. **Pip:** you should already have pip if python is installed.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>  # Replace <repository_url> with the actual URL
    cd computer_vision_GenAI
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**  In the root directory of the project (`computer_vision_GenAI`), create a file named `.env`.  **Do not commit this file to version control.**  Add your Veolia Secure GPT credentials to this file:

    ```
    # .env file (DO NOT COMMIT)

    VEOLIA_CLIENT_ID=YOUR_VEOLIA_CLIENT_ID
    VEOLIA_CLIENT_SECRET=YOUR_VEOLIA_CLIENT_SECRET
    USER_EMAIL=YOUR_EMAIL@company.com
    VEOLIA_API_BASE_URL=https://api.veolia.com/llm/veoliasecuregpt/v1/answer  # Or your specific endpoint

    ```



