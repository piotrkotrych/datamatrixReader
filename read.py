from PIL import Image, ImageTk, ImageGrab
from pylibdmtx.pylibdmtx import decode as dmtx_decode
import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog 
import configparser
import pyperclip # For clipboard functionality

class DataMatrixReader:
    def __init__(self, root):
        self.root = root
        self.root.title("DataMatrix Reader")
        
        self.root.state('zoomed')
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selection = None
        self.cv_image = None
        self.photo = None
        self.scale_factor = 1.0
        
        # Adaptive Thresholding Variables
        self.use_adaptive_thresh = tk.BooleanVar(value=False)
        self.adaptive_method_var = tk.StringVar(value="GAUSSIAN") # "GAUSSIAN" or "MEAN"
        self.adaptive_block_size_raw = tk.IntVar(value=5) # Represents (value*2)+1, so default is 11
        self.adaptive_c_value = tk.IntVar(value=2)

        # Repair Mode Variables
        self.repair_mode_var = tk.BooleanVar(value=False)
        self.paint_color_var = tk.StringVar(value="BLACK") # "BLACK" or "WHITE"
        self.brush_size_var = tk.IntVar(value=3) # Brush size in pixels on original image
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)
        
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side="right", fill="y", padx=10, pady=10)
        
        self.canvas_frame = ttk.Frame(self.left_frame)
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<Configure>", self.resize_image_on_canvas_configure)
        
        self.create_controls()
        
        self.load_settings()
        
        self.toggle_adaptive_thresh_controls() # Set initial state of controls
        self.toggle_repair_mode_controls() # Initialize repair mode UI state
        
        self.load_initial_image() 
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def _setup_new_cv_image(self, cv_image_data):
        self.cv_image = cv_image_data
        self.selection = None 
        self.rect_id = None 
        self.display_image_on_canvas()
        self.update_preview()
        # Optionally, disable repair mode when a new image is loaded
        if self.repair_mode_var.get():
            self.repair_mode_var.set(False)
            self.toggle_repair_mode_controls()

    def load_initial_image(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_image_path = os.path.join(current_dir, 'image.png')
        if os.path.exists(default_image_path):
            temp_cv_image = cv2.imread(default_image_path)
            if temp_cv_image is not None:
                self._setup_new_cv_image(temp_cv_image)
            else:
                messagebox.showerror("Error", f"Failed to load default image: {default_image_path}")
                self.canvas.delete("all")
        else:
            messagebox.showinfo("Information", "Please load an image using the 'Load Image' or 'Load from Clipboard' button.")
            self.canvas.delete("all")

    def select_image_file(self):
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), 
                       ("All files", "*.*"))
        )
        if file_path:
            temp_cv_image = cv2.imread(file_path)
            if temp_cv_image is not None:
                self._setup_new_cv_image(temp_cv_image)
            else:
                messagebox.showerror("Error", f"Failed to load image: {file_path}")

    # load_image method is now effectively _setup_new_cv_image combined with file reading
    # For clarity, direct calls will use _setup_new_cv_image after getting cv_image_data

    def display_image_on_canvas(self):
        if self.cv_image is None:
            self.canvas.delete("all")
            if hasattr(self, 'photo'): 
                del self.photo
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1: 
            self.root.after(50, self.display_image_on_canvas) 
            return

        img_height, img_width = self.cv_image.shape[:2]
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        self.scale_factor = min(scale_w, scale_h)
        
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        
        if new_width <= 0 or new_height <= 0: 
            return

        self.cv_image_display = cv2.resize(self.cv_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        rgb_image = cv2.cvtColor(self.cv_image_display, cv2.COLOR_BGR2RGB)
        self.pil_image = Image.fromarray(rgb_image)
        
        self.photo = ImageTk.PhotoImage(self.pil_image) 
        
        self.canvas.delete("all") 
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        if self.rect_id: 
            self.rect_id = None
        # self.selection = None # Keep selection if image is just re-rendered due to resize

    def resize_image_on_canvas_configure(self, event):
        if self.cv_image is not None:
            self.display_image_on_canvas()
            
    def create_controls(self):
        self.thresh_val = tk.IntVar(value=127)
        self.inverse = tk.BooleanVar(value=False)
        self.erode_size = tk.IntVar(value=2)
        self.close_size = tk.IntVar(value=4)
        self.open_size = tk.IntVar(value=3)
        self.erode_iter = tk.IntVar(value=1)
        self.sharpness_factor = tk.IntVar(value=0) 
        self.denoise_strength = tk.IntVar(value=0)
        self.manual_decode_timeout = tk.IntVar(value=2000) 
        self.preset_iteration_timeout = tk.IntVar(value=1000)
        self.upscale_factor_var = tk.DoubleVar(value=1.0) # For upscaling

        # --- Top Buttons ---
        top_button_frame = ttk.Frame(self.right_frame)
        top_button_frame.pack(fill="x", pady=(0,5))

        load_image_button = ttk.Button(top_button_frame, text="Load Image", command=self.select_image_file)
        load_image_button.pack(side="left", fill="x", expand=True, padx=(0,2)) 

        load_clipboard_button = ttk.Button(top_button_frame, text="Load from Clipboard", command=self.load_from_clipboard)
        load_clipboard_button.pack(side="left", fill="x", expand=True, padx=(2,0))
        
        # --- Main Settings Area (2 columns) ---
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.pack(fill="x", pady=5)

        settings_col1 = ttk.Frame(main_settings_frame)
        settings_col1.pack(side="left", fill="x", expand=True, padx=(0, 5))

        settings_col2 = ttk.Frame(main_settings_frame)
        settings_col2.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # --- Column 1 Controls ---
        preview_frame = ttk.LabelFrame(settings_col1, text="Preview")
        preview_frame.pack(fill="x", padx=5, pady=5)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(padx=5, pady=5)

        morph_frame = ttk.LabelFrame(settings_col1, text="Morphology Settings")
        morph_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(morph_frame, text="Erode kernel size:").pack(fill="x", padx=5)
        ttk.Scale(morph_frame, from_=1, to=5, variable=self.erode_size,
                 orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)
        ttk.Label(morph_frame, text="Erode iterations:").pack(fill="x", padx=5)
        ttk.Scale(morph_frame, from_=1, to=3, variable=self.erode_iter,
                 orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)
        ttk.Label(morph_frame, text="Close kernel size:").pack(fill="x", padx=5)
        ttk.Scale(morph_frame, from_=2, to=6, variable=self.close_size,
                 orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)
        ttk.Label(morph_frame, text="Open kernel size:").pack(fill="x", padx=5)
        ttk.Scale(morph_frame, from_=2, to=5, variable=self.open_size,
                 orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)

        # --- Manual Repair Controls (Column 1) ---
        repair_outer_frame = ttk.LabelFrame(settings_col1, text="Manual Image Repair")
        repair_outer_frame.pack(fill="x", padx=5, pady=5)

        self.repair_mode_cb = ttk.Checkbutton(repair_outer_frame, text="Enable Repair Mode",
                                              variable=self.repair_mode_var, command=self.toggle_repair_mode_controls)
        self.repair_mode_cb.pack(anchor="w", padx=5)

        self.repair_params_frame = ttk.Frame(repair_outer_frame)
        # Packed by toggle_repair_mode_controls

        ttk.Label(self.repair_params_frame, text="Paint Color:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        repair_paint_black_rb = ttk.Radiobutton(self.repair_params_frame, text="Black", variable=self.paint_color_var, value="BLACK")
        repair_paint_black_rb.grid(row=0, column=1, sticky="w", padx=2)
        repair_paint_white_rb = ttk.Radiobutton(self.repair_params_frame, text="White", variable=self.paint_color_var, value="WHITE")
        repair_paint_white_rb.grid(row=0, column=2, sticky="w", padx=2)

        ttk.Label(self.repair_params_frame, text="Brush Size (px):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.repair_brush_scale = ttk.Scale(self.repair_params_frame, from_=1, to=20, variable=self.brush_size_var)
        self.repair_brush_scale.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        self.repair_params_frame.columnconfigure(1, weight=1)


        # --- Column 2 Controls ---
        sharpness_frame = ttk.LabelFrame(settings_col2, text="Sharpness")
        sharpness_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(sharpness_frame, text="Sharpness Level (0-100):").pack(fill="x", padx=5)
        ttk.Scale(sharpness_frame, from_=0, to=100, variable=self.sharpness_factor,
                  orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)
        
        denoise_frame = ttk.LabelFrame(settings_col2, text="Denoising")
        denoise_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(denoise_frame, text="Denoise Strength (0-30):").pack(fill="x", padx=5)
        ttk.Scale(denoise_frame, from_=0, to=30, variable=self.denoise_strength,
                  orient="horizontal", command=self.update_preview).pack(fill="x", padx=5)

        upscale_frame = ttk.LabelFrame(settings_col2, text="Image Upscaling")
        upscale_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(upscale_frame, text="Upscale Factor (1.0-4.0):").pack(fill="x", padx=5)
        ttk.Scale(upscale_frame, from_=1.0, to=4.0, variable=self.upscale_factor_var,
                  orient="horizontal").pack(fill="x", padx=5) # No command, applied by button
        ttk.Button(upscale_frame, text="Apply Upscale to Image", command=self.apply_image_upscale).pack(fill="x", padx=5, pady=(5,0))

        # --- Global Threshold (can be disabled by adaptive) ---
        self.global_thresh_frame = ttk.LabelFrame(settings_col2, text="Global Threshold")
        self.global_thresh_frame.pack(fill="x", padx=5, pady=5)
        self.thresh_scale = ttk.Scale(self.global_thresh_frame, from_=0, to=255, variable=self.thresh_val, 
                 orient="horizontal", command=self.update_preview)
        self.thresh_scale.pack(fill="x", padx=5)
        self.inverse_cb = ttk.Checkbutton(self.global_thresh_frame, text="Inverse Colors (Global/Adaptive)", 
                        variable=self.inverse, command=self.update_preview) # Inverse applies to both
        self.inverse_cb.pack(fill="x", padx=5)


        # --- Adaptive Thresholding ---
        adaptive_thresh_outer_frame = ttk.LabelFrame(settings_col2, text="Adaptive Thresholding")
        adaptive_thresh_outer_frame.pack(fill="x", padx=5, pady=5)

        self.use_adaptive_cb = ttk.Checkbutton(adaptive_thresh_outer_frame, text="Use Adaptive Threshold",
                                         variable=self.use_adaptive_thresh, command=self.toggle_adaptive_thresh_controls)
        self.use_adaptive_cb.pack(anchor="w", padx=5)

        self.adaptive_params_frame = ttk.Frame(adaptive_thresh_outer_frame)
        # self.adaptive_params_frame.pack(fill="x", padx=5, pady=5) # Packed by toggle_adaptive_thresh_controls

        ttk.Label(self.adaptive_params_frame, text="Method:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        adaptive_method_gaussian_rb = ttk.Radiobutton(self.adaptive_params_frame, text="Gaussian", variable=self.adaptive_method_var, value="GAUSSIAN", command=self.update_preview)
        adaptive_method_gaussian_rb.grid(row=0, column=1, sticky="w", padx=2)
        adaptive_method_mean_rb = ttk.Radiobutton(self.adaptive_params_frame, text="Mean", variable=self.adaptive_method_var, value="MEAN", command=self.update_preview)
        adaptive_method_mean_rb.grid(row=0, column=2, sticky="w", padx=2)
        
        ttk.Label(self.adaptive_params_frame, text="Block Size (3-31 odd):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.adaptive_block_scale = ttk.Scale(self.adaptive_params_frame, from_=1, to=15, variable=self.adaptive_block_size_raw, command=self.update_preview) # Raw value 1-15 -> Block 3-31
        self.adaptive_block_scale.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)

        ttk.Label(self.adaptive_params_frame, text="C Value:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.adaptive_c_scale = ttk.Scale(self.adaptive_params_frame, from_=-10, to=10, variable=self.adaptive_c_value, command=self.update_preview)
        self.adaptive_c_scale.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5)
        self.adaptive_params_frame.columnconfigure(1, weight=1)


        timeout_frame = ttk.LabelFrame(settings_col2, text="Timeout Settings (ms)")
        timeout_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(timeout_frame, text="Manual Decode Timeout:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(timeout_frame, textvariable=self.manual_decode_timeout, width=7).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(timeout_frame, text="Preset Iteration Timeout:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(timeout_frame, textvariable=self.preset_iteration_timeout, width=7).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        timeout_frame.columnconfigure(1, weight=1)

        decode_actions_frame = ttk.LabelFrame(settings_col2, text="Decode Actions")
        decode_actions_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(decode_actions_frame, text="Try Decode", 
                  command=self.try_decode).pack(fill="x", padx=5, pady=2)
        ttk.Button(decode_actions_frame, text="Iterate Presets",
                   command=self.iterate_presets).pack(fill="x", padx=5, pady=2)
        ttk.Button(decode_actions_frame, text="Save Current as Preset",
                   command=self.save_current_as_preset).pack(fill="x", padx=5, pady=2)

        # --- Results Table ---
        results_area_frame = ttk.LabelFrame(self.right_frame, text="Found Codes")
        results_area_frame.pack(fill="both", expand=True, padx=5, pady=5)

        cols = ("Source", "Data")
        self.results_table = ttk.Treeview(results_area_frame, columns=cols, show='headings', height=5)
        for col in cols:
            self.results_table.heading(col, text=col)
            self.results_table.column(col, width=150 if col=="Source" else 250, stretch=tk.YES)
        self.results_table.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        copy_result_button = ttk.Button(results_area_frame, text="Copy Selected Result", command=self.copy_selected_result)
        copy_result_button.pack(side="bottom", fill="x", padx=5, pady=(0,5))


        # --- Bottom Buttons (Save/Load Settings) ---
        bottom_buttons_frame = ttk.Frame(self.right_frame)
        bottom_buttons_frame.pack(fill="x", pady=(5,0))
        ttk.Button(bottom_buttons_frame, text="Save Settings", 
                  command=self.save_settings).pack(side="left", fill="x", expand=True, padx=(0,2))
        ttk.Button(bottom_buttons_frame, text="Load Settings", 
                  command=self.load_settings).pack(side="right", fill="x", expand=True, padx=(2,0))

    def toggle_repair_mode_controls(self):
        if self.repair_mode_var.get():
            self.repair_params_frame.pack(fill="x", padx=5, pady=5) # Show repair params
            # Optionally, provide visual feedback or disable selection drawing more explicitly
            if self.rect_id:
                self.canvas.delete(self.rect_id) # Clear any existing selection rectangle
                self.rect_id = None
            # self.selection = None # Clear logical selection
            self.canvas.config(cursor="crosshair") # Change cursor for repair
        else:
            self.repair_params_frame.pack_forget() # Hide repair params
            self.canvas.config(cursor="") # Reset cursor
        # No need to call update_preview here unless toggling mode itself should trigger it

    def toggle_adaptive_thresh_controls(self):
        if self.use_adaptive_thresh.get():
            self.adaptive_params_frame.pack(fill="x", padx=5, pady=5) # Show adaptive params
            # Disable global threshold scale
            self.thresh_scale.configure(state=tk.DISABLED)
            self.global_thresh_frame.config(text="Global Threshold (Disabled)")
        else:
            self.adaptive_params_frame.pack_forget() # Hide adaptive params
            # Enable global threshold scale
            self.thresh_scale.configure(state=tk.NORMAL)
            self.global_thresh_frame.config(text="Global Threshold")
        self.update_preview()

    def apply_image_upscale(self):
        if self.cv_image is None:
            messagebox.showwarning("Upscale Error", "Please load an image first.")
            return
        
        factor = self.upscale_factor_var.get()
        if factor <= 1.0:
            messagebox.showinfo("Upscale Info", "Upscale factor must be greater than 1.0.")
            return

        orig_h, orig_w = self.cv_image.shape[:2]
        new_w = int(orig_w * factor)
        new_h = int(orig_h * factor)

        try:
            # Using INTER_LANCZOS4 for better quality upscaling
            upscaled_image = cv2.resize(self.cv_image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            self._setup_new_cv_image(upscaled_image) # This will handle display update
            messagebox.showinfo("Upscale Complete", f"Image upscaled by a factor of {factor:.2f}.")
        except Exception as e:
            messagebox.showerror("Upscale Error", f"Could not upscale image: {e}")


    def copy_selected_result(self):
        selected_item = self.results_table.focus() # Get selected item
        if not selected_item:
            messagebox.showinfo("Copy Result", "No result selected from the table.")
            return
        
        item_details = self.results_table.item(selected_item)
        data_to_copy = item_details.get("values")[1] # Assuming "Data" is the second column

        try:
            pyperclip.copy(data_to_copy)
            messagebox.showinfo("Copy Result", "Selected result copied to clipboard!")
        except pyperclip.PyperclipException as e:
            messagebox.showerror("Copy Error", f"Could not copy to clipboard: {e}\nMake sure you have a copy/paste mechanism installed (e.g., xclip or xsel on Linux).")


    def on_press(self, event):
        if self.repair_mode_var.get():
            self.paint_on_canvas(event) # Call paint function if in repair mode
            return # Skip selection logic

        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
    def on_drag(self, event):
        if self.repair_mode_var.get():
            # For simplicity, drag painting is not implemented here. 
            # Could be added by calling self.paint_on_canvas(event) continuously.
            return # Skip selection logic

        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y, outline='red', width=2)
        
    def on_release(self, event):
        if self.repair_mode_var.get():
            return # Skip selection logic

        if self.cv_image is None or self.start_x is None: # Ensure image is loaded and press occurred
            return

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        # Convert coordinates back to original image scale
        x1_orig = int(x1 / self.scale_factor)
        y1_orig = int(y1 / self.scale_factor)
        x2_orig = int(x2 / self.scale_factor)
        y2_orig = int(y2 / self.scale_factor)
        self.selection = (x1_orig, y1_orig, x2_orig, y2_orig)
        
        self.update_preview() # Update preview after selection is made
        
    def paint_on_canvas(self, event):
        if self.cv_image is None or not self.repair_mode_var.get():
            return

        # Convert canvas click coordinates to original image coordinates
        x_canvas = event.x
        y_canvas = event.y
        
        x_orig = int(x_canvas / self.scale_factor)
        y_orig = int(y_canvas / self.scale_factor)

        brush_size = self.brush_size_var.get()
        brush_half = brush_size // 2

        # Determine paint color (BGR for OpenCV)
        paint_color_bgr = (0, 0, 0) if self.paint_color_var.get() == "BLACK" else (255, 255, 255)

        # Define the top-left and bottom-right corners of the brush stroke
        pt1 = (max(0, x_orig - brush_half), max(0, y_orig - brush_half))
        pt2 = (min(self.cv_image.shape[1] - 1, x_orig + brush_half), 
               min(self.cv_image.shape[0] - 1, y_orig + brush_half))

        # Ensure points are valid before drawing
        if pt1[0] < pt2[0] and pt1[1] < pt2[1]:
            cv2.rectangle(self.cv_image, pt1, pt2, paint_color_bgr, -1) # -1 for filled

            self.display_image_on_canvas() # Refresh the main canvas display
            self.update_preview()          # Refresh the processed preview

    def process_image(self):
        if not self.selection or self.cv_image is None: # Check if cv_image exists
            return None
            
        x1, y1, x2, y2 = self.selection
        # Ensure selection coordinates are valid before cropping
        if x1 >= x2 or y1 >= y2:
            # Invalid selection, e.g., zero width or height
            if hasattr(self, 'results_table'): # Check if table exists
                self.results_table.insert("", tk.END, values=("Process Warning", "Invalid selection area (zero width or height)."))
            return None 
            
        cropped = self.cv_image[y1:y2, x1:x2]
        
        # Add a check for the cropped image dimensions
        if cropped.shape[0] == 0 or cropped.shape[1] == 0:
            # If cropped image is empty, return None
            if hasattr(self, 'results_table'): # Check if table exists
                self.results_table.insert("", tk.END, values=("Process Warning", "Cropped area is empty."))
            return None
            
        # Rotate if needed - REMOVED
        
        # Convert to grayscale
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

        # Apply Denoising if strength > 0
        denoise_val = self.denoise_strength.get()
        if denoise_val > 0:
            # Parameters for fastNlMeansDenoising:
            # h : Parameter regulating filter strength. Higher h value removes more noise but also blurs details.
            # templateWindowSize : Should be odd. (Recommended 7)
            # searchWindowSize : Should be odd. (Recommended 21)
            gray = cv2.fastNlMeansDenoising(gray, h=float(denoise_val), templateWindowSize=7, searchWindowSize=21)

        # Apply sharpening if factor > 0
        sharpness_level = self.sharpness_factor.get() # Integer 0-100
        if sharpness_level > 0:
            alpha = sharpness_level / 100.0 # Convert to 0.0-1.0
            # Common sharpening kernel
            kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]], dtype=np.float32)
            # Apply the sharpening kernel
            sharpened_gray = cv2.filter2D(gray, -1, kernel)
            # Blend the original gray image with the sharpened one
            gray = cv2.addWeighted(gray, 1.0 - alpha, sharpened_gray, alpha, 0)
            # Ensure the result is still uint8 (though addWeighted should handle it if inputs are uint8)
            gray = np.clip(gray, 0, 255).astype(np.uint8)
        
        # Improve contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Apply binary threshold (Global or Adaptive)
        if self.use_adaptive_thresh.get():
            method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C if self.adaptive_method_var.get() == "GAUSSIAN" else cv2.ADAPTIVE_THRESH_MEAN_C
            block_size_val = self.adaptive_block_size_raw.get() * 2 + 1 # Ensure odd: 1->3, 2->5, ...
            if block_size_val < 3: block_size_val = 3 # Minimum block size
            c_val = self.adaptive_c_value.get()
            
            processed = cv2.adaptiveThreshold(gray, 255, method, 
                                              cv2.THRESH_BINARY, block_size_val, c_val)
        else:
            _, processed = cv2.threshold(gray, self.thresh_val.get(), 255, 
                cv2.THRESH_BINARY)
        
        # Invert if needed (applies to both global and adaptive result)
        if self.inverse.get():
            processed = cv2.bitwise_not(processed)
        
        # Morphological operations with current settings
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, 
            (self.erode_size.get(), self.erode_size.get()))
        processed = cv2.erode(processed, kernel_small, 
            iterations=self.erode_iter.get())
        
        kernel_square = cv2.getStructuringElement(cv2.MORPH_RECT, 
            (self.close_size.get(), self.close_size.get()))
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel_square)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
            (self.open_size.get(), self.open_size.get()))
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
        
        return processed

    def update_preview(self, *args):
        if self.cv_image is None: # Don't try to process if no image
            if hasattr(self, 'preview_label') and self.preview_label.winfo_exists():
                 # Clear previous preview if it exists
                empty_preview = ImageTk.PhotoImage(Image.new('L', (1, 1))) # Minimal placeholder
                self.preview_label.configure(image=empty_preview)
                self.preview_label.image = empty_preview
            return

        processed = self.process_image()
        if processed is not None:
            preview = Image.fromarray(processed)
            preview.thumbnail((200, 200), Image.Resampling.LANCZOS) # Use Image.Resampling.LANCZOS
            preview_tk = ImageTk.PhotoImage(preview) # Renamed to avoid conflict
            self.preview_label.configure(image=preview_tk)
            self.preview_label.image = preview_tk # Keep reference

    def _try_decode_current_settings(self, timeout_ms=None):
        if self.cv_image is None or not self.selection:
            return None
            
        processed = self.process_image()
        if processed is None:
            return None 
            
        current_timeout = timeout_ms if timeout_ms is not None else self.manual_decode_timeout.get()
        if current_timeout <= 0: 
            current_timeout = 1000 

        try:
            decoded_data = dmtx_decode(Image.fromarray(processed), timeout=current_timeout)
            if decoded_data:
                return decoded_data[0].data.decode('utf-8')
        except Exception as e: 
            # Log to results table/area instead of just console or a popup
            self.results_table.insert("", tk.END, values=("Decode Error", f"Timeout {current_timeout}ms: {e}"))
            self.root.update_idletasks()
        return None

    def try_decode(self):
        if self.cv_image is None:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        if not self.selection:
            messagebox.showwarning("Warning", "Please select an area first")
            return
            
        for i in self.results_table.get_children(): # Clear previous results
            self.results_table.delete(i)
        
        manual_timeout = self.manual_decode_timeout.get()
        decoded_text = self._try_decode_current_settings(timeout_ms=manual_timeout) 
        
        if decoded_text:
            self.results_table.insert("", tk.END, values=("Manual Decode", decoded_text))
        else:
            self.results_table.insert("", tk.END, values=("Manual Decode", f"No code (timeout {manual_timeout}ms)"))

    def generate_default_presets_file(self, filepath='datamatrix_presets.ini'):
        # Rotation removed from presets
        presets_content = """
[Preset1]
name = Default Global
thresh_val = 127
inverse = False
erode_size = 2
erode_iter = 1
close_size = 4
open_size = 3
sharpness_factor = 0
denoise_strength = 0
use_adaptive_thresh = False
adaptive_method = GAUSSIAN
adaptive_block_size_raw = 5
adaptive_c_value = 2

[Preset2]
name = Default Adaptive Gaussian
thresh_val = 127
inverse = False
erode_size = 2
erode_iter = 1
close_size = 4
open_size = 3
sharpness_factor = 0
denoise_strength = 5
use_adaptive_thresh = True
adaptive_method = GAUSSIAN
adaptive_block_size_raw = 5 
adaptive_c_value = 2

[Preset3]
name = Adaptive Mean LowContrast
thresh_val = 127
inverse = False
erode_size = 1
erode_iter = 1
close_size = 2
open_size = 2
sharpness_factor = 10
denoise_strength = 3
use_adaptive_thresh = True
adaptive_method = MEAN
adaptive_block_size_raw = 7 
adaptive_c_value = 3
""" # ... (add more presets, including adaptive settings)
        try:
            with open(filepath, 'w') as f:
                f.write(presets_content.strip())
            if hasattr(self, 'results_table'): # Check if table exists
                 self.results_table.insert("", tk.END, values=("Info", f"Generated default presets: {filepath}"))
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate presets file: {e}")

    def iterate_presets(self):
        if self.cv_image is None:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        if not self.selection:
            messagebox.showwarning("Warning", "Please select an area on the image first.")
            return

        config = configparser.ConfigParser()
        presets_file_path = 'datamatrix_presets.ini' 

        if not os.path.exists(presets_file_path):
            # self.results_text.insert(tk.END, f"Presets file not found: {presets_file_path}. Generating default.\n")
            self.generate_default_presets_file(presets_file_path)
            if not os.path.exists(presets_file_path): 
                 messagebox.showerror("Error", f"Failed to create or find presets file: {presets_file_path}")
                 return

        config.read(presets_file_path)
        
        for i in self.results_table.get_children(): # Clear previous results
            self.results_table.delete(i)
        
        presets_were_read = False
        current_preset_timeout = self.preset_iteration_timeout.get()
        if current_preset_timeout <= 0:
            current_preset_timeout = 1000 
        found_codes_count = 0

        for section in config.sections():
            if section.startswith("Preset"):
                presets_were_read = True
                preset_name = config.get(section, 'name', fallback=section)
                # self.results_text.insert(tk.END, f"Trying Preset: {preset_name} (max {current_preset_timeout}ms)...\n")
                self.root.update_idletasks() 

                try:
                    self.thresh_val.set(config.getint(section, 'thresh_val'))
                    self.inverse.set(config.getboolean(section, 'inverse'))
                    self.erode_size.set(config.getint(section, 'erode_size'))
                    self.erode_iter.set(config.getint(section, 'erode_iter'))
                    self.close_size.set(config.getint(section, 'close_size'))
                    self.open_size.set(config.getint(section, 'open_size'))
                    self.sharpness_factor.set(config.getint(section, 'sharpness_factor', fallback=0))
                    self.denoise_strength.set(config.getint(section, 'denoise_strength', fallback=0)) 
                    # Adaptive thresholding settings
                    self.use_adaptive_thresh.set(config.getboolean(section, 'use_adaptive_thresh', fallback=False))
                    self.adaptive_method_var.set(config.get(section, 'adaptive_method', fallback="GAUSSIAN"))
                    self.adaptive_block_size_raw.set(config.getint(section, 'adaptive_block_size_raw', fallback=5))
                    self.adaptive_c_value.set(config.getint(section, 'adaptive_c_value', fallback=2))
                except Exception as e:
                    self.results_table.insert("", tk.END, values=(f"Preset {preset_name}", f"Error loading: {e}"))
                    self.root.update_idletasks()
                    continue 

                self.update_preview() 
                self.root.update_idletasks() 
                self.toggle_adaptive_thresh_controls() # Update UI based on loaded preset

                decoded_text = self._try_decode_current_settings(timeout_ms=current_preset_timeout) 
                
                if decoded_text:
                    found_codes_count += 1
                    self.results_table.insert("", tk.END, values=(f"Preset '{preset_name}'", decoded_text))
                else:
                    self.results_table.insert("", tk.END, values=(f"Preset '{preset_name}'", "Failed"))
                self.root.update_idletasks()

        if not presets_were_read:
            self.results_table.insert("", tk.END, values=("Info", "No presets found in file."))
            messagebox.showinfo("Info", "No presets found in the settings file.")
            return

        summary_message = f"Iteration complete. Found code(s) with {found_codes_count} preset(s)."
        if found_codes_count == 0:
            summary_message = "Iteration complete. No code found with any preset."
        
        self.results_table.insert("", tk.END, values=("Summary", summary_message))
        messagebox.showinfo("Iteration Complete", summary_message + " Check results table for details.")
        
    def save_settings(self):
        config = configparser.ConfigParser()
        config['Morphology'] = {
            'erode_size': str(self.erode_size.get()),
            'erode_iter': str(self.erode_iter.get()),
            'close_size': str(self.close_size.get()),
            'open_size': str(self.open_size.get())
        }
        config['Threshold'] = {
            'thresh_val': str(self.thresh_val.get()),
            'inverse': str(self.inverse.get())
        }
        config['Sharpening'] = { 
            'sharpness_factor': str(self.sharpness_factor.get())
        }
        config['Denoising'] = { 
            'denoise_strength': str(self.denoise_strength.get())
        }
        config['Timeouts'] = { 
            'manual_decode_timeout': str(self.manual_decode_timeout.get()),
            'preset_iteration_timeout': str(self.preset_iteration_timeout.get())
        }
        config['AdaptiveThreshold'] = {
            'use_adaptive_thresh': str(self.use_adaptive_thresh.get()),
            'adaptive_method': self.adaptive_method_var.get(),
            'adaptive_block_size_raw': str(self.adaptive_block_size_raw.get()),
            'adaptive_c_value': str(self.adaptive_c_value.get())
        }
        
        with open('datamatrix_settings.ini', 'w') as configfile:
            config.write(configfile)
            
    def load_settings(self):
        config = configparser.ConfigParser()
        try:
            config.read('datamatrix_settings.ini')
            
            if 'Morphology' in config:
                self.erode_size.set(config.getint('Morphology', 'erode_size', fallback=2))
                self.erode_iter.set(config.getint('Morphology', 'erode_iter', fallback=1))
                self.close_size.set(config.getint('Morphology', 'close_size', fallback=4))
                self.open_size.set(config.getint('Morphology', 'open_size', fallback=3))
                
            if 'Threshold' in config:
                self.thresh_val.set(config.getint('Threshold', 'thresh_val', fallback=127))
                self.inverse.set(config.getboolean('Threshold', 'inverse', fallback=False))
                
            if 'Sharpening' in config: 
                self.sharpness_factor.set(config.getint('Sharpening', 'sharpness_factor', fallback=0))
            
            if 'Denoising' in config: 
                self.denoise_strength.set(config.getint('Denoising', 'denoise_strength', fallback=0))
            
            if 'Timeouts' in config: 
                self.manual_decode_timeout.set(config.getint('Timeouts', 'manual_decode_timeout', fallback=2000))
                self.preset_iteration_timeout.set(config.getint('Timeouts', 'preset_iteration_timeout', fallback=1000))

            if 'AdaptiveThreshold' in config:
                self.use_adaptive_thresh.set(config.getboolean('AdaptiveThreshold', 'use_adaptive_thresh', fallback=False))
                self.adaptive_method_var.set(config.get('AdaptiveThreshold', 'adaptive_method', fallback="GAUSSIAN"))
                self.adaptive_block_size_raw.set(config.getint('AdaptiveThreshold', 'adaptive_block_size_raw', fallback=5))
                self.adaptive_c_value.set(config.getint('AdaptiveThreshold', 'adaptive_c_value', fallback=2))
            
            # self.toggle_adaptive_thresh_controls() # Called after create_controls in __init__
                
        except Exception as e:
            messagebox.showwarning("Settings", f"Could not load settings: {str(e)}")

    def load_from_clipboard(self):
        try:
            pil_image = ImageGrab.grabclipboard()
            if pil_image is None:
                messagebox.showinfo("Clipboard", "No image found on clipboard, or clipboard content is not an image.")
                return

            if pil_image.mode == 'RGBA':
                pil_image_rgb = pil_image.convert('RGB')
            elif pil_image.mode != 'RGB':
                pil_image_rgb = pil_image.convert('RGB')
            else:
                pil_image_rgb = pil_image
            
            cv_image_data = cv2.cvtColor(np.array(pil_image_rgb), cv2.COLOR_RGB2BGR)
            
            if cv_image_data is None:
                messagebox.showerror("Error", "Failed to convert clipboard image to OpenCV format.")
                return
                
            self._setup_new_cv_image(cv_image_data)
            if hasattr(self, 'results_table'): # Check if table exists
                self.results_table.insert("", tk.END, values=("Info", "Image loaded from clipboard."))

        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not load image from clipboard: {str(e)}")
            if hasattr(self, 'results_table'): # Check if table exists
                self.results_table.insert("", tk.END, values=("Clipboard Error", str(e)))

    def save_current_as_preset(self):
        preset_name_input = simpledialog.askstring("Save Preset", "Enter Preset Name:", parent=self.root)
        if not preset_name_input:
            return 

        presets_file_path = 'datamatrix_presets.ini'
        config = configparser.ConfigParser()

        if not os.path.exists(presets_file_path):
            self.generate_default_presets_file(presets_file_path)
            if not os.path.exists(presets_file_path): 
                 messagebox.showerror("Error", f"Failed to create or find presets file: {presets_file_path} for saving.")
                 return
        
        config.read(presets_file_path)

        next_preset_num = 1
        existing_preset_nums = []
        for section in config.sections():
            if section.startswith("Preset"):
                try:
                    num = int(section[len("Preset"):])
                    existing_preset_nums.append(num)
                except ValueError:
                    continue 
        if existing_preset_nums:
            next_preset_num = max(existing_preset_nums) + 1
        
        section_title = f"Preset{next_preset_num}"
        config.add_section(section_title)
        config.set(section_title, 'name', preset_name_input)
        config.set(section_title, 'thresh_val', str(self.thresh_val.get()))
        config.set(section_title, 'inverse', str(self.inverse.get()))
        config.set(section_title, 'erode_size', str(self.erode_size.get()))
        config.set(section_title, 'erode_iter', str(self.erode_iter.get()))
        config.set(section_title, 'close_size', str(self.close_size.get()))
        config.set(section_title, 'open_size', str(self.open_size.get()))
        config.set(section_title, 'sharpness_factor', str(self.sharpness_factor.get()))
        config.set(section_title, 'denoise_strength', str(self.denoise_strength.get()))
        # Adaptive thresholding settings
        config.set(section_title, 'use_adaptive_thresh', str(self.use_adaptive_thresh.get()))
        config.set(section_title, 'adaptive_method', self.adaptive_method_var.get())
        config.set(section_title, 'adaptive_block_size_raw', str(self.adaptive_block_size_raw.get()))
        config.set(section_title, 'adaptive_c_value', str(self.adaptive_c_value.get()))

        try:
            with open(presets_file_path, 'w') as configfile:
                config.write(configfile)
            if hasattr(self, 'results_table'): # Check if table exists
                self.results_table.insert("", tk.END, values=("Info", f"Preset '{preset_name_input}' saved as {section_title}."))
            messagebox.showinfo("Preset Saved", f"Settings saved as Preset '{preset_name_input}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save preset: {e}")

if __name__ == '__main__':
    root = tk.Tk()
    app = DataMatrixReader(root)
    root.mainloop()