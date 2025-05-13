# DataMatrix Reader and Processor

This application provides a graphical user interface (GUI) for loading images, processing regions of interest (ROI) containing DataMatrix codes, and attempting to decode them. It offers a variety of image processing tools to enhance the readability of codes, especially those that are damaged or poorly printed.

## Features

*   **Image Loading:**
    *   Load images from local files (`.png`, `.jpg`, `.bmp`, etc.).
    *   Load images directly from the clipboard.
    *   Loads a default `image.png` from the application directory on startup if present.
*   **Region of Interest (ROI) Selection:**
    *   Click and drag on the image to select the DataMatrix code area.
*   **Image Processing Controls:**
    *   **Live Preview:** See the effect of processing parameters on the selected ROI in real-time.
    *   **Denoising:** Apply Non-Local Means Denoising to reduce noise.
    *   **Sharpening:** Enhance edges and details.
    *   **Contrast Enhancement:** CLAHE (Contrast Limited Adaptive Histogram Equalization) is applied automatically.
    *   **Thresholding:**
        *   **Global Thresholding:** Apply a single threshold value.
        *   **Adaptive Thresholding:** Choose between Gaussian or Mean methods, with adjustable block size and C value. This is particularly useful for images with uneven lighting or print quality.
        *   **Inverse Colors:** Invert the image (black to white and vice-versa) before decoding.
    *   **Morphological Operations:**
        *   Erode
        *   Close
        *   Open
        *   Adjust kernel sizes and iteration counts.
    *   **Image Upscaling:** Enlarge the loaded image using Lanczos interpolation for potentially better detail before processing.
*   **Manual Image Repair:**
    *   Enable "Repair Mode" to manually paint black or white pixels onto the loaded image.
    *   Adjustable brush size.
    *   Useful for fixing severely damaged or "burned" cells in a DataMatrix.
*   **Decoding:**
    *   Attempt to decode the processed ROI using `pylibdmtx`.
    *   Adjustable timeout for manual decoding attempts.
*   **Presets:**
    *   **Save Current Settings:** Save the current combination of processing parameters as a named preset.
    *   **Iterate Presets:** Automatically try all saved presets on the selected ROI to find one that successfully decodes the DataMatrix.
    *   Adjustable timeout for each preset during iteration.
*   **Application Settings:**
    *   Save and load the last used processing parameters and UI state.
*   **Results Display:**
    *   View decoded data in a table, showing the source of the decode (e.g., "Manual Decode", "Preset 'X'").
    *   Copy decoded data to the clipboard with a button.
*   **User Interface:**
    *   Fullscreen layout with image display on the left and controls/results on the right.
    *   Controls organized into collapsible sections.

## Requirements

*   Python 3.x
*   OpenCV (`opencv-python`)
*   Pillow (`Pillow`)
*   pylibdmtx (`pylibdmtx`)
*   pyperclip (`pyperclip`)

## Setup and Installation

1.  **Clone the Repository (if applicable) or ensure you have all project files.**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```
2.  **Install Dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
    Install the required packages. You can create a `requirements.txt` file (see below) and run:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatively, install them individually:
    ```bash
    pip install opencv-python Pillow pylibdmtx pyperclip
    ```

    **`requirements.txt` file content:**
    ```text
    opencv-python
    Pillow
    pylibdmtx
    pyperclip
    ```

## How to Use

1.  **Run the Application:**
    ```bash
    python read.py
    ```
2.  **Load an Image:**
    *   Click "Load Image" to select a file.
    *   Or, copy an image to your clipboard and click "Load from Clipboard".
3.  **Select DataMatrix Region:**
    *   Click and drag a rectangle around the DataMatrix code on the image displayed in the left panel.
4.  **Adjust Processing Parameters:**
    *   Use the controls in the right panel (organized into two columns) to apply various image processing techniques.
    *   The "Preview" window in the first column of controls shows the effect of your settings on the selected region.
    *   Toggle "Use Adaptive Threshold" for advanced thresholding options.
5.  **Manual Repair (if needed):**
    *   If parts of the DataMatrix are visibly damaged:
        *   Check "Enable Repair Mode" in the "Manual Image Repair" section.
        *   Select "Paint Color" (Black/White) and "Brush Size".
        *   Click on the main image canvas to paint over defects.
        *   Uncheck "Enable Repair Mode" to resume ROI selection.
6.  **Decode:**
    *   Click "Try Decode" in the "Decode Actions" section to attempt decoding with the current settings.
    *   If decoding fails, try adjusting parameters or use "Iterate Presets" to test all saved presets.
7.  **View and Copy Results:**
    *   Decoded data will appear in the "Found Codes" table.
    *   Select a result and click "Copy Selected Result" to copy the data.
8.  **Manage Settings and Presets:**
    *   Use "Save Settings" and "Load Settings" to persist your general application configuration.
    *   Use "Save Current as Preset" to store effective processing combinations.

## Configuration Files

The application uses `.ini` files to store settings and presets in the same directory as `read.py`:

*   **`datamatrix_settings.ini`**: Stores the last used UI control values (thresholds, morphology settings, timeouts, adaptive thresholding parameters, etc.). This file is automatically loaded on startup and saved when you click "Save Settings".
*   **`datamatrix_presets.ini`**: Stores user-defined presets. Each preset includes all relevant processing parameters. This file is generated with defaults if not found.
*   **`image.png` (Optional)**: If an image named `image.png` exists in the application directory, it will be loaded automatically on startup.

## Troubleshooting

*   **`AttributeError: 'DataMatrixReader' object has no attribute 'results_text'` (or similar for `results_table`):** This might occur if you've manually edited the code and an older reference to a UI element persists. Ensure all UI interactions point to the correct, current UI elements.
*   **`pyperclip.PyperclipException` (Copy to Clipboard Fails):** On some systems (especially Linux), `pyperclip` requires a copy/paste mechanism like `xclip` or `xsel` to be installed.
    ```bash
    # For Debian/Ubuntu
    sudo apt-get install xclip
    # or
    sudo apt-get install xsel
    ```
*   **Poor Decoding Performance:** Experiment extensively with all available image processing parameters. The "Iterate Presets" feature is very helpful for this. Adaptive thresholding and manual repair can be particularly effective for challenging codes.

---

This README provides a good overview for users and developers interacting with your project.