import tkinter as tk
from tkinter import ttk
import time
import os
import threading
import logging
from PIL import Image, ImageTk
from camera.local_camera import capture_image_local
from camera.reolink_camera import capture_image_reolink
from config.settings import load_config

class ImageClassificationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Clasificación de Imágenes")
        self.root.geometry("1000x700")
        
        # Cargar configuración
        self.config = load_config()
        self.dataset_dir = self.config.get("dataset_dir", "dataset_images")
        self.cam_type = self.config.get("camera", {}).get("type", "local").lower()
        self.camera_index = self.config.get("camera_index", 0)
        
        # Crear directorios de clasificación
        self.today = time.strftime("%Y%m%d")
        self.base_dir = os.path.join(self.dataset_dir, self.today)
        self.good_dir = os.path.join(self.base_dir, "good")
        self.bad_dir = os.path.join(self.base_dir, "bad")
        os.makedirs(self.good_dir, exist_ok=True)
        os.makedirs(self.bad_dir, exist_ok=True)
        
        # Variables
        self.current_image_path = None
        self.is_capturing = False
        self.capture_thread = None
        
        # Crear la interfaz
        self.create_widgets()
        
        # Iniciar con una captura
        self.capture_image()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel de imagen
        self.image_label = ttk.Label(main_frame)
        self.image_label.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Frame de botones de clasificación
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        # Estilo para botones grandes
        style = ttk.Style()
        style.configure('Large.TButton', font=('Helvetica', 14))
        
        # Botones de clasificación
        self.good_btn = ttk.Button(
            btn_frame, 
            text="BUENA ✓", 
            style='Large.TButton',
            command=lambda: self.classify_and_capture("good")
        )
        self.good_btn.grid(row=0, column=0, padx=20, ipadx=30, ipady=20)
        
        self.bad_btn = ttk.Button(
            btn_frame, 
            text="MALA ✗", 
            style='Large.TButton',
            command=lambda: self.classify_and_capture("bad")
        )
        self.bad_btn.grid(row=0, column=1, padx=20, ipadx=30, ipady=20)
        
        # Frame de estatus
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Listo para clasificar")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack()
        
        # Contador de imágenes
        self.counter_frame = ttk.Frame(main_frame)
        self.counter_frame.pack(fill=tk.X, pady=5)
        
        self.good_count_var = tk.StringVar(value="Buenas: 0")
        self.bad_count_var = tk.StringVar(value="Malas: 0")
        
        ttk.Label(self.counter_frame, textvariable=self.good_count_var).pack(side=tk.LEFT, padx=20)
        ttk.Label(self.counter_frame, textvariable=self.bad_count_var).pack(side=tk.RIGHT, padx=20)
        
        # Actualizar contadores
        self.update_counters()
    
    def capture_image(self):
        """Captura una imagen de la cámara configurada"""
        self.status_var.set("Capturando imagen...")
        self.root.update()
        
        try:
            if self.cam_type == "reolink":
                temp_config = dict(self.config)
                temp_config["image_dir"] = self.base_dir
                image_path = capture_image_reolink(temp_config, filename_prefix="temp_image")
            else:
                image_path = capture_image_local(self.base_dir, "temp_image", self.camera_index)
            
            if image_path:
                self.current_image_path = image_path
                self.display_image(image_path)
                self.status_var.set("Imagen capturada. Esperando clasificación...")
            else:
                self.status_var.set("¡Error al capturar imagen!")
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            logging.error(f"Error capturing image: {e}")
    
    def display_image(self, image_path):
        """Muestra la imagen en la interfaz"""
        try:
            # Cargar y redimensionar imagen para la interfaz
            img = Image.open(image_path)
            # Mantener relación de aspecto y ajustar al tamaño de la ventana
            width, height = img.size
            max_width = self.root.winfo_width() - 50
            max_height = self.root.winfo_height() - 200
            
            # Calcular nuevas dimensiones manteniendo la relación de aspecto
            ratio = min(max_width/width, max_height/height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            self.image_label.config(image=photo)
            self.image_label.image = photo  # Mantener referencia
        except Exception as e:
            self.status_var.set(f"Error al mostrar imagen: {str(e)}")
            logging.error(f"Error displaying image: {e}")
    
    def classify_and_capture(self, classification):
        """Clasifica la imagen actual y captura una nueva"""
        if not self.current_image_path or self.is_capturing:
            return
        
        self.is_capturing = True
        
        try:
            # Determinar directorio de destino
            dest_dir = self.good_dir if classification == "good" else self.bad_dir
            
            # Crear nombre de archivo con timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{classification}_{timestamp}.jpg"
            dest_path = os.path.join(dest_dir, filename)
            
            # Mover o copiar archivo
            if os.path.exists(self.current_image_path):
                # Opción 1: Mover archivo
                os.rename(self.current_image_path, dest_path)
                # Opción 2: Copiar archivo (descomenta si prefieres copiar)
                # import shutil
                # shutil.copy2(self.current_image_path, dest_path)
                # os.remove(self.current_image_path)  # eliminar original
                
                self.status_var.set(f"Imagen clasificada como {classification}")
                # Actualizar contadores
                self.update_counters()
            else:
                self.status_var.set("Error: La imagen ya no existe")
        except Exception as e:
            self.status_var.set(f"Error al clasificar: {str(e)}")
            logging.error(f"Error classifying image: {e}")
        
        # Iniciar un nuevo hilo para capturar la siguiente imagen
        self.capture_thread = threading.Thread(target=self.threaded_capture)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def threaded_capture(self):
        """Captura una imagen en un hilo separado"""
        time.sleep(0.5)  # Breve pausa antes de la siguiente captura
        self.capture_image()
        self.is_capturing = False
    
    def update_counters(self):
        """Actualiza los contadores de imágenes buenas y malas"""
        try:
            good_count = len([f for f in os.listdir(self.good_dir) if f.endswith('.jpg')])
            bad_count = len([f for f in os.listdir(self.bad_dir) if f.endswith('.jpg')])
            
            self.good_count_var.set(f"Buenas: {good_count}")
            self.bad_count_var.set(f"Malas: {bad_count}")
        except Exception as e:
            logging.error(f"Error updating counters: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageClassificationApp(root)
    root.mainloop()