# JSON AI Translator

A powerful, multithreaded desktop application designed to automate IT and software localization. Built with Python and Tkinter, this tool uses the Google Gemini API to translate JSON localization files into over 100 languages while strictly preserving JSON formatting, keys, and technical context.

## Download (No Python Required)

You can download the standalone `.exe` file directly from the [Releases](https://github.com/Bruh-SomeBody/JSON-AI-Translator/releases/latest) page. Just download and run it.

## Features

* **Smart JSON Handling:** Translates only the values, keeping your JSON keys and structure completely intact.
* **Multithreaded Processing:** Configure up to 15 concurrent threads for blazing-fast batch translations.
* **100+ Languages:** Supports a massive database of languages categorized by region (Europe, Asia, Africa, etc.), with handy presets for the most popular ones.
* **Modern UI:** A clean, responsive interface with Dark/Light mode support (powered by `sv_ttk` and `pywinstyles`).
* **Custom Prompts:** Built-in prompt editor to tweak the translation context (e.g., instructing the model to ignore specific IT jargon like "UWP" or "bloatware").
* **Resilient & Auto-Saving:** Automatically handles API rate limits (429), server errors, and malformed JSON responses by intelligently retrying. Skips already translated files to save API quota.

## Prerequisites (For running from source)

* **Python 3.8+**
* A valid **Google Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

## Installation (Source)

1. **Clone the repository:**
    ```bash
    git clone [https://github.com/Bruh-SomeBody/JSON-AI-Translator.git](https://github.com/Bruh-SomeBody/JSON-AI-Translator.git)
    cd JSON-AI-Translator
    ```

2. **(Optional but recommended) Create a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3. **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Run the application:
    ```bash
    python main.py
    ```
2. Paste your **Gemini API Key** and click **Refresh List** to load available models. Select a model (e.g., `gemini-3.1-flash`).
3. Select your **Source JSON** file.
4. Select the **Output Folder** where the translated JSON files will be saved.
5. Choose your target languages (use the presets or select manually).
6. Adjust the thread count and click **▶ START TRANSLATION**.

## Configuration

The app automatically generates a `settings.json` file in the root directory after your first run. This file saves your API key locally, your last used paths, your custom prompt, and UI theme preferences so you don't have to re-enter them next time.