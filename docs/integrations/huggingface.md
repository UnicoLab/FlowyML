# Hugging Face Integration 🤗

Build state-of-the-art NLP and Vision pipelines with Transformers and flowyml.

> [!NOTE]
> **What you'll learn**: How to manage Transformers models and datasets
>
> **Key insight**: Treat Hugging Face models as first-class citizens in your pipeline.

## Why Hugging Face + flowyml?

- **Model Management**: Version control large Transformer models efficiently.
- **Dataset Lineage**: Track exactly which version of a dataset was used for fine-tuning.
- **Easy Deployment**: Move from fine-tuning to inference seamlessly.

## 🤗 Transformers

Fine-tune models with full lineage tracking.

```python
from flowyml import step
from transformers import Trainer, TrainingArguments

@step
def fine_tune(model, dataset):
    args = TrainingArguments(output_dir="./results", num_train_epochs=3)

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset["train"]
    )

    trainer.train()
    return trainer.model
```

## 📚 Datasets

Load and version datasets.

```python
from datasets import load_dataset
from flowyml import step

@step
def get_data():
    # This dataset artifact will be versioned
    return load_dataset("imdb")
```
