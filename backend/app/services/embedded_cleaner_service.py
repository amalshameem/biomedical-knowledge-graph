import logging
import torch
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from app.services.pdf_service import clean_and_defragment_text

logger = logging.getLogger(__name__)

class EmbeddedCleanerService:
    _model = None
    _tokenizer = None
    _device = None

    @classmethod
    def get_instance(cls):
        """
        Lazy-loads the embedded micro-LLM (Qwen2.5-0.5B-Instruct) into memory.
        Uses Apple Silicon (MPS), CUDA, or CPU automatically.
        """
        if cls._model is None or cls._tokenizer is None:
            model_id = "Qwen/Qwen2.5-0.5B-Instruct"
            logger.info(f"Loading embedded micro-LLM cleaner: {model_id}...")

            device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.float16 if device in ("mps", "cuda") else torch.float32

            try:
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token

                model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    dtype=dtype,
                    device_map=device
                )
                cls._model = model
                cls._tokenizer = tokenizer
                cls._device = device
                logger.info(f"Embedded micro-LLM cleaner ready on {device} ({dtype}).")
            except Exception as e:
                logger.error(f"Failed to load embedded micro-LLM: {e}")
                return None, None, "cpu"

        return cls._model, cls._tokenizer, cls._device

    @classmethod
    def is_available(cls) -> bool:
        try:
            m, t, _ = cls.get_instance()
            return m is not None and t is not None
        except Exception:
            return False

    @classmethod
    def clean_text_embedded(cls, text: str, max_tokens: int = 512) -> str:
        """
        Cleans and restores biomedical text using a hybrid pipeline:
        1. Fast deterministic Python de-fragmentation (ftfy, ligature repair, word boundary separation).
        2. Embedded micro-LLM (Qwen2.5-0.5B-Instruct) contextual pass for remaining OCR artifacts.
        """
        if not text or not text.strip():
            return ""

        # Tier 1: Fast deterministic Python de-noising
        pre_cleaned = clean_and_defragment_text(text)
        if not pre_cleaned:
            return ""

        # If micro-LLM is not loaded, return the high-fidelity Tier 1 output
        try:
            model, tokenizer, device = cls.get_instance()
            if model is None or tokenizer is None:
                return pre_cleaned

            system_prompt = (
                "You are an expert biomedical text restoration engine. "
                "Fix all remaining PDF OCR ligature splits and word boundary errors in the text. "
                "Strictly preserve all scientific names, gene symbols (e.g. LCN2, IL-6, COX-2), chromosome loci, metrics (e.g. 25-kDa), and numbers. "
                "Output ONLY the cleaned verbatim text without commentary."
            )
            user_prompt = f"Text to clean:\n{pre_cleaned}\n\nCleaned text:"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer([input_text], return_tensors="pt", padding=True).to(device)

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=inputs.input_ids,
                    attention_mask=inputs.attention_mask,
                    max_new_tokens=min(len(inputs.input_ids[0]) + 100, max_tokens),
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id
                )

            generated_ids = outputs[0][len(inputs.input_ids[0]):]
            cleaned_output = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

            if cleaned_output and len(cleaned_output) > 10:
                # Run a quick pass through Tier 1 to ensure any output punctuation is clean
                return clean_and_defragment_text(cleaned_output)
            return pre_cleaned
        except Exception as e:
            logger.warning(f"Embedded micro-LLM inference error: {e}. Falling back to Tier 1 clean text.")
            return pre_cleaned
