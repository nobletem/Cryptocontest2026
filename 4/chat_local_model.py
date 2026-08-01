import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

if len(sys.argv) < 2:
    print("usage: python chat_local_model.py <model_dir>")
    sys.exit(1)

model_dir = sys.argv[1]

tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)

dtype = torch.float16 if torch.cuda.is_available() else torch.float32
device_map = "auto" if torch.cuda.is_available() else None

model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    torch_dtype=dtype,
    device_map=device_map,
    trust_remote_code=True,
)

if not torch.cuda.is_available():
    model = model.to("cpu")

print(f"loaded: {model_dir}")
print("type /exit to quit")

while True:
    user = input("\nYou: ").strip()
    if user.lower() in {"/exit", "exit", "quit"}:
        break

    messages = [{"role": "user", "content": user}]

    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        prompt = f"User: {user}\nAssistant:"

    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    text = tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    print(f"Model: {text.strip()}")