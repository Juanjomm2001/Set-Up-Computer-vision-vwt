import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import time
import glob
import tempfile
import threading
import logging
import io
from PIL import Image, ImageTk
import shutil
from functools import lru_cache

# Add the main directory to Python's path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules from the main project
from config.settings import load_config
from utils.helpers import setup_logging
from utils.drive_uploader import get_drive_service

# For Google Drive integration
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

class DriveImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Drive Image Classification")
        self.root.geometry("1200x800")
        
        # Configure logging
        setup_logging()
        
        # Load configuration
        self.config = load_config()
        
        # Google Drive configuration
        self.google_drive_config = self.config.get("google_drive", {})
        self.service_account_file = self.google_drive_config.get("service_account_file", "credentials/katodiskbeskyttelseServiceAccount.json")
        self.drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        
        # Directory for temporarily downloaded images
        self.temp_dir = tempfile.mkdtemp()
        logging.info(f"Created temporary directory for images: {self.temp_dir}")
        
        # Variables for image management
        self.drive_service = None
        self.drive_files = []
        self.current_file_index = 0
        self.current_image_path = None
        self.current_file_id = None
        
        # State
        self.is_loading = False
        self.loading_thread = None
        
        # Initialize Google Drive API
        self.initialize_drive()
        
        # Create interface
        self.create_widgets()
        
        # Load images from Drive in a separate thread
        self.load_drive_images_async()
        
        # Register cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def initialize_drive(self):
        """Initialize connection to Google Drive"""
        try:
            if not os.path.exists(self.service_account_file):
                logging.error(f"Service account file not found: {self.service_account_file}")
                messagebox.showerror("Error", f"Service account file not found: {self.service_account_file}")
                return False
            
            if not self.drive_folder_id:
                logging.error("Google Drive folder ID not defined in .env file")
                messagebox.showerror("Error", "Google Drive folder ID not defined (GOOGLE_DRIVE_FOLDER_ID)")
                return False
            
            self.drive_service = get_drive_service(self.service_account_file) # This function uses the credentials from the JSON file to authenticate with the Google Drive API
            logging.info("Google Drive connection initialized")
            return True
        except Exception as e:
            logging.error(f"Error initializing Google Drive: {e}")
            messagebox.showerror("Error", f"Error connecting to Google Drive: {str(e)}")
            return False
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel (image)
        left_frame = ttk.Frame(main_frame, padding="5", relief="groove", borderwidth=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Title
        ttk.Label(left_frame, text="Current Image", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        # Image panel
        self.image_frame = ttk.Frame(left_frame)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Filename
        self.filename_var = tk.StringVar(value="No image selected")
        ttk.Label(left_frame, textvariable=self.filename_var, font=('Helvetica', 10)).pack(pady=5)
        
        # Navigation buttons
        nav_frame = ttk.Frame(left_frame)
        nav_frame.pack(pady=10)
        
        self.prev_btn = ttk.Button(
            nav_frame, 
            text="◀ Previous", 
            command=self.prev_image
        )
        self.prev_btn.grid(row=0, column=0, padx=10)
        
        # Image counter
        self.counter_var = tk.StringVar(value="0/0")
        ttk.Label(nav_frame, textvariable=self.counter_var, font=('Helvetica', 12)).grid(row=0, column=1, padx=20)
        
        self.next_btn = ttk.Button(
            nav_frame, 
            text="Next ▶", 
            command=self.next_image
        )
        self.next_btn.grid(row=0, column=2, padx=10)
        
        # Classification buttons
        classification_frame = ttk.Frame(left_frame)
        classification_frame.pack(pady=20)
        
        # Define styles
        style = ttk.Style()
        style.configure('Normal.TButton', font=('Helvetica', 14))
        style.configure('Anomaly.TButton', font=('Helvetica', 14))
        
        self.normal_btn = ttk.Button(
            classification_frame, 
            text="NORMAL ✓", 
            style='Normal.TButton',
            command=lambda: self.classify_image("normal")
        )
        self.normal_btn.grid(row=0, column=0, padx=20, ipadx=40, ipady=20)
        
        self.anomaly_btn = ttk.Button(
            classification_frame, 
            text="ANOMALY ✗", 
            style='Anomaly.TButton',
            command=lambda: self.classify_image("anomaly")
        )
        self.anomaly_btn.grid(row=0, column=1, padx=20, ipadx=40, ipady=20)
        
        # Right panel (list and statistics)
        right_frame = ttk.Frame(main_frame, padding="5", relief="groove", borderwidth=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=5)
        right_frame.config(width=300)
        
        ttk.Label(right_frame, text="Drive Images", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        # Refresh button
        ttk.Button(right_frame, text="Refresh List", command=self.load_drive_images_async).pack(pady=10)
        
        # Statistics
        self.stats_frame = ttk.Frame(right_frame, relief="groove", borderwidth=1)
        self.stats_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Label(self.stats_frame, text="Statistics", font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        self.stats_total = tk.StringVar(value="Total: 0")
        self.stats_normal = tk.StringVar(value="Normal: 0")
        self.stats_anomaly = tk.StringVar(value="Anomaly: 0")
        self.stats_pending = tk.StringVar(value="Pending: 0")
        
        ttk.Label(self.stats_frame, textvariable=self.stats_total).pack(anchor='w', padx=10, pady=2)
        ttk.Label(self.stats_frame, textvariable=self.stats_normal).pack(anchor='w', padx=10, pady=2)
        ttk.Label(self.stats_frame, textvariable=self.stats_anomaly).pack(anchor='w', padx=10, pady=2)
        ttk.Label(self.stats_frame, textvariable=self.stats_pending).pack(anchor='w', padx=10, pady=2)
        
        # Image list
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.image_listbox = tk.Listbox(list_frame, height=20, width=40)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.image_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.image_listbox.config(yscrollcommand=scrollbar.set)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_drive_images_async(self):
        """Load images from Drive in a separate thread"""
        if self.is_loading:
            return
            
        self.is_loading = True
        self.status_var.set("Loading images from Google Drive...")
        
        # Cancel any existing thread
        if self.loading_thread and self.loading_thread.is_alive():
            self.loading_thread.join(0.1)
            
        # Start new thread
        self.loading_thread = threading.Thread(target=self.load_drive_images)
        self.loading_thread.daemon = True
        self.loading_thread.start()
    
    def load_drive_images(self):
        """Load the list of images from Google Drive"""
        if not self.drive_service:
            self.is_loading = False
            return
            
        try:
            # Define file types to search for
            query = f"'{self.drive_folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png') and trashed=false"
            
            # Use fields parameter to reduce API response size
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000  # Increased page size for fewer API calls
            ).execute()
            
            items = results.get('files', [])
            
            # Filter already classified images
            # Changed from good/bad to normal/anomaly
            self.drive_files = [f for f in items if not (f['name'].startswith('normal_') or f['name'].startswith('anomaly_'))]
            
            # Count classified images
            normal_files = [f for f in items if f['name'].startswith('normal_')]
            anomaly_files = [f for f in items if f['name'].startswith('anomaly_')]
            
            # Update statistics
            self.stats_total.set(f"Total: {len(items)}")
            self.stats_normal.set(f"Normal: {len(normal_files)}")
            self.stats_anomaly.set(f"Anomaly: {len(anomaly_files)}")
            self.stats_pending.set(f"Pending: {len(self.drive_files)}")
            
            # Update UI from main thread
            self.root.after(0, self.update_ui_after_load)
            
        except Exception as e:
            logging.error(f"Error loading images from Drive: {e}")
            # Update UI from main thread
            self.root.after(0, lambda: self.handle_error(f"Error loading images: {str(e)}"))
        finally:
            self.is_loading = False
    
    def update_ui_after_load(self):
        """Update UI elements after images are loaded (called from main thread)"""
        # Update listbox
        self.image_listbox.delete(0, tk.END)
        for file in self.drive_files:
            self.image_listbox.insert(tk.END, file['name'])
        
        # Update counter
        total = len(self.drive_files)
        if total > 0:
            self.counter_var.set(f"1/{total}")
            # Show first image
            self.current_file_index = 0
            self.download_and_show_image(0)
        else:
            self.counter_var.set("0/0")
            self.image_label.config(image='')
            self.filename_var.set("No pending images")
            self.status_var.set("No images pending classification")
    
    def handle_error(self, error_message):
        """Handle errors and update UI (called from main thread)"""
        self.status_var.set(f"Error: {error_message}")
        messagebox.showerror("Error", error_message)
    
    @lru_cache(maxsize=5)  # Cache recent images
    def get_image_from_drive(self, file_id, filename):
        """Download an image from Drive and cache it"""
        # Download file
        request = self.drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # Reset position and return content
        file_content.seek(0)
        return file_content
    
    def download_and_show_image(self, index):
        """Download and display the image at the specified index"""
        if index < 0 or index >= len(self.drive_files):
            return
        
        self.status_var.set("Downloading image...")
        self.root.update_idletasks()  # More efficient than full update()
        
        try:
            file = self.drive_files[index]
            file_id = file['id']
            filename = file['name']
            
            # Update current index
            self.current_file_index = index
            self.current_file_id = file_id
            
            # Use a separate thread for downloading to keep UI responsive
            threading.Thread(
                target=self._download_and_show_image_thread,
                args=(file_id, filename),
                daemon=True
            ).start()
            
        except Exception as e:
            logging.error(f"Error downloading/displaying image: {e}")
            self.status_var.set(f"Error: {str(e)}")
    
    def _download_and_show_image_thread(self, file_id, filename):
        """Background thread for downloading and showing images"""
        try:
            # Get file content
            file_content = self.get_image_from_drive(file_id, filename)
            
            # Save temporarily
            temp_path = os.path.join(self.temp_dir, filename)
            with open(temp_path, 'wb') as f:
                f.write(file_content.read())
            
            self.current_image_path = temp_path
            
            # Update UI in main thread
            self.root.after(0, lambda: self._update_image_in_ui(temp_path, filename))
            
        except Exception as e:
            logging.error(f"Error in download thread: {e}")
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
    
    def _update_image_in_ui(self, image_path, filename):
        """Update the UI with the downloaded image (called in main thread)"""
        try:
            # Open and resize image
            img = Image.open(image_path)
            img = self.resize_image(img)
            photo = ImageTk.PhotoImage(img)
            
            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep reference
            
            # Update information
            self.filename_var.set(filename)
            self.counter_var.set(f"{self.current_file_index+1}/{len(self.drive_files)}")
            
            # Select in list
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_file_index)
            self.image_listbox.see(self.current_file_index)
            
            self.status_var.set(f"Image loaded: {filename}")
        except Exception as e:
            logging.error(f"Error updating image in UI: {e}")
            self.status_var.set(f"Error: {str(e)}")
    
    def resize_image(self, img):
        """Resize the image maintaining aspect ratio"""
        # Get viewing area dimensions
        max_width = self.image_frame.winfo_width() - 20
        max_height = self.image_frame.winfo_height() - 20
        
        # If widget not fully created yet
        if max_width < 100:
            max_width = 800
        if max_height < 100:
            max_height = 600
        
        # Original dimensions
        width, height = img.size
        
        # Calculate new dimension maintaining aspect ratio
        if width > height:
            new_width = min(width, max_width)
            new_height = int(height * (new_width / width))
        else:
            new_height = min(height, max_height)
            new_width = int(width * (new_height / height))
        
        # Use LANCZOS for better quality
        return img.resize((new_width, new_height), Image.LANCZOS)
    
    def classify_image(self, classification):
        """Classify the current image as normal or anomaly"""
        if not self.current_file_id or not self.current_image_path:
            self.status_var.set("No image to classify")
            return
        
        try:
            self.status_var.set(f"Classifying image as {classification}...")
            self.root.update_idletasks()
            
            # Get current file information
            file = self.drive_files[self.current_file_index]
            original_name = file['name']
            new_name = f"{classification}_{original_name}"
            
            # Update the filename in Drive
            self.drive_service.files().update(
                fileId=self.current_file_id,
                body={'name': new_name},
                supportsAllDrives=True
            ).execute()
            
            self.status_var.set(f"Image classified as {classification}: {new_name}")
            logging.info(f"Image {original_name} classified as {classification}")
            
            # Clear the cache for this file
            if hasattr(self, 'get_image_from_drive'):
                self.get_image_from_drive.cache_clear()
            
            # Reload the image list
            self.load_drive_images_async()
            
        except Exception as e:
            logging.error(f"Error classifying image: {e}")
            self.status_var.set(f"Error classifying: {str(e)}")
            messagebox.showerror("Error", f"Error classifying image: {str(e)}")
    
    def next_image(self):
        """Show the next image"""
        if not self.drive_files:
            return
        
        next_index = self.current_file_index + 1
        if next_index >= len(self.drive_files):
            next_index = 0  # Loop back to beginning
        
        self.download_and_show_image(next_index)
    
    def prev_image(self):
        """Show the previous image"""
        if not self.drive_files:
            return
        
        prev_index = self.current_file_index - 1
        if prev_index < 0:
            prev_index = len(self.drive_files) - 1  # Go to end
        
        self.download_and_show_image(prev_index)
    
    def on_image_select(self, event):
        """Handle image selection in the list"""
        selection = self.image_listbox.curselection()
        if selection:
            index = selection[0]
            self.download_and_show_image(index)
    
    def on_closing(self):
        """Clean up resources when closing the application"""
        try:
            # Delete temporary directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logging.info(f"Deleted temporary directory: {self.temp_dir}")
        except Exception as e:
            logging.error(f"Error cleaning up resources: {e}")
        finally:
            self.root.destroy()

if __name__ == "__main__":
    # Configure logging
    setup_logging()
    
    # Create main window
    root = tk.Tk()
    app = DriveImageClassifier(root)
    
    # Start interface loop
    root.mainloop()