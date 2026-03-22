# 🤗 Hugging Face Integration

!!! info "What you'll learn"
    How to manage Transformers models and datasets with FlowyML — treat Hugging Face models as first-class citizens in your ML pipeline.

Build state-of-the-art NLP, Vision, and Multimodal pipelines with the Transformers ecosystem and FlowyML.

---

## Why Hugging Face + FlowyML?

| Feature | Benefit |
|---|---|
| **Model Management** | Version control large Transformer models |
| **Dataset Lineage** | Track which dataset version was used for fine-tuning |
| **Hub Integration** | Push/pull models from the Hugging Face Hub |
| **Easy Deployment** | Move from fine-tuning to inference seamlessly |

---

## 🤗 Fine-Tuning Transformers

Fine-tune models with full lineage tracking:

```python
from flowyml import step
from transformers import AutoModelForSequenceClassification, Trainer, TrainingArguments

@step(outputs=["model"])
def fine_tune(dataset):
    model = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased",
        num_labels=2,
    )

    args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
    )

    trainer.train()
    return trainer.model
```

---

## 📚 Loading Datasets

Load and version Hugging Face datasets:

```python
from datasets import load_dataset
from flowyml import step

@step(outputs=["dataset"])
def get_data():
    """Dataset artifact is versioned and tracked by FlowyML."""
    return load_dataset("imdb")

@step(outputs=["tokenized"])
def tokenize(dataset):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    def tokenize_fn(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True)

    return dataset.map(tokenize_fn, batched=True)
```

---

## 🚀 Pushing to the Hub

Push fine-tuned models to the Hugging Face Hub:

```python
@step
def push_to_hub(model, tokenizer):
    model.push_to_hub("my-org/sentiment-classifier-v2")
    tokenizer.push_to_hub("my-org/sentiment-classifier-v2")
```

---

## 🔮 Inference Pipeline

```python
from transformers import pipeline as hf_pipeline
from flowyml import step

@step(outputs=["predictions"])
def predict(texts: list[str]):
    classifier = hf_pipeline("sentiment-analysis", model="my-org/sentiment-classifier-v2")
    return classifier(texts)
```

---

## Best Practices

!!! tip "Use AutoModel classes"
    Always use `AutoModelFor*` and `AutoTokenizer` instead of specific model classes — they automatically handle architecture selection.

!!! tip "Gradient checkpointing for large models"
    For models > 1B parameters, enable gradient checkpointing to reduce GPU memory: `model.gradient_checkpointing_enable()`.

!!! warning "Large model storage"
    Transformer models can be several GB. Use FlowyML's artifact catalog to avoid downloading the same model repeatedly.
