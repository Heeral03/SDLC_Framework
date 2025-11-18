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
        
        print(f"✓ Model loaded on device: {self.model.device}")

    def generate(self, prompt, max_tokens=2~00):
        """
        Generate text with optimized settings for speed
        """
        # Truncate input to prevent excessive processing
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=1024  # Limit input context
        ).to(self.model.device)
        
        output = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.3,  # Lower for more focused output
            do_sample=True,
            top_p=0.9,
            pad_token_id=self.tokenizer.eos_token_id,
            num_beams=1  # Greedy decoding for speed
        )
        
        return self.tokenizer.decode(output[0], skip_special_tokens=True)