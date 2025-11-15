from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class SLMModel:
    def __init__(self, model_name="Qwen/Qwen2.5-0.5B-Instruct"):
        print("Loading model... This may take 20–40 sec.")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )

    def generate(self, prompt):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        output = self.model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.2
        )
        return self.tokenizer.decode(output[0], skip_special_tokens=True)
