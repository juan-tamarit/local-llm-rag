
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

# Configuración de cuantización NF4
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

print(f"Cargando tokenizer: {MODEL_ID}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

print("Cargando modelo en GPU...")

torch.cuda.reset_peak_memory_stats()

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=quantization_config,
    torch_dtype=torch.float16,
    device_map={"": 0},
)

print("Modelo cargado correctamente.")

print(
    f"VRAM ocupada: "
    f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB"
)

messages = [
    {
        "role": "user",
        "content": "Escribe una función Python que compruebe si un número es primo."
    }
]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

print("Generando respuesta...")

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=False,
    )

response = tokenizer.decode(
    outputs[0][inputs["input_ids"].shape[1]:],
    skip_special_tokens=True,
)

print("\n--- RESPUESTA DEL MODELO ---")
print(response)

print("\n--- MEMORIA GPU ---")
print(
    f"Pico de memoria asignada: "
    f"{torch.cuda.max_memory_allocated() / 1024**3:.2f} GB"
)
