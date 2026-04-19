import os
import sys

def check_processor():
    from transformers import AutoProcessor, AutoTokenizer
    # Don't download big model, just check the tokenizer/processor
    model_id = "google/gemma-2b-it" # Or any locally cached
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        print("Tokenizer has apply_chat_template:", hasattr(tokenizer, "apply_chat_template"))
        # We don't have internet maybe? If not, we can't test. It's ok.
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_processor()
