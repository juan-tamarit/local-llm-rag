import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

def print_vram_usage(step_name=""):
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024 ** 3)
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        print(f"[{step_name}] VRAM Asignada: {allocated:.2f} GB | VRAM Reservada: {reserved:.2f} GB")
    else:
        print(f"[{step_name}] Ejecutando en CPU")

def run_limit_tests():
    print("=== INICIALIZANDO PRUEBAS DE LÍMITES (FASE 0) ===")
    print_vram_usage("Inicio")

    # 1. Configuración moderna de cuantización NF4 de 4 bits mediante bitsandbytes
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4"
    )

    print(f"\nCargando modelo {MODEL_ID} con BitsAndBytesConfig...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        device_map="cuda",
        quantization_config=quantization_config
    )
    print_vram_usage("Post-Carga Modelo")

    # 2. Prueba de contexto creciente
    base_prompt = "Escribe una función en Python optimizada que calcule números primos utilizando la criba de Eratóstenes."
    context_multipliers = [1, 5, 10, 20]
    dummy_code_block = "\n# Comentario técnico de relleno para ocupar contexto: " + ("código " * 100) + "\n"

    print("\n--- INICIANDO PRUEBAS DE CONTEXTO ---")
    for mult in context_multipliers:
        padding_text = dummy_code_block * (mult * 20)
        full_prompt = f"{padding_text}\n\nPregunta: {base_prompt}"
        
        inputs = tokenizer(full_prompt, return_tensors="pt").to("cuda")
        input_tokens = inputs.input_ids.shape[1]
        
        print(f"\nProbando con un contexto de entrada de ~{input_tokens} tokens (Multiplicador: {mult})...")
        
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                do_sample=True
            )
        end_time = time.time()
        
        print(f"-> Generación completada en {end_time - start_time:.2f} segundos.")
        print_vram_usage(f"Contexto {input_tokens} tokens")
        
        torch.cuda.empty_cache()

    # 3. Prueba de longitud máxima de generación
    print("\n--- INICIANDO PRUEBA DE GENERACIÓN LARGA ---")
    generation_lengths = [256, 512, 1024]
    
    for max_tokens in generation_lengths:
        print(f"\nSolicitando una generación máxima de {max_tokens} tokens...")
        inputs = tokenizer(base_prompt, return_tensors="pt").to("cuda")
        
        try:
            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    do_sample=True
                )
            end_time = time.time()
            
            print(f"-> Generados {outputs.shape[1] - inputs.input_ids.shape[1]} tokens en {end_time - start_time:.2f} s.")
            print_vram_usage(f"Generación máx {max_tokens}")
        except torch.cuda.OutOfMemoryError:
            print(f"¡AVISO! OOM (Out of Memory) alcanzado al intentar generar {max_tokens} tokens.")
            break
        
        torch.cuda.empty_cache()

    print("\n=== PRUEBAS DE FASE 0 FINALIZADAS ===")

if __name__ == "__main__":
    run_limit_tests()