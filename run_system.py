import subprocess
import sys
import os
import time

def main():
    print("Starting Image Capture System...")
    
    # Ruta al ejecutable de Python (usando el del entorno virtual si existe)
    python_executable = sys.executable
    
    # Directorio base del proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Comando para el proceso de captura
    capture_script = os.path.join(base_dir, "capture_dataset.py")
    
    # Comando para el proceso de clasificación
    classifier_script = os.path.join(base_dir, "manual-classification", "inter-graph-drive.py")
    
    # Iniciar proceso de captura
    print("Starting capture process...")
    capture_process = subprocess.Popen([python_executable, capture_script])
    
    # Esperar para que se inicialice
    print("Waiting for capture process to initialize...")
    time.sleep(3)
    
    # Iniciar proceso de clasificación
    print("Starting classifier process...")
    classifier_process = subprocess.Popen([python_executable, classifier_script])
    
    try:
        # Mantener el script principal ejecutándose hasta que se cierre manualmente
        print("Both processes started. Press Ctrl+C to stop.")
        capture_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down processes...")
        
        # Intentar terminar los procesos correctamente
        if classifier_process.poll() is None:
            classifier_process.terminate()
        if capture_process.poll() is None:
            capture_process.terminate()
            
        print("System stopped.")

if __name__ == "__main__":
    main()