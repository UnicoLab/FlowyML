# Sub-Pipeline Composition

Nest entire pipelines as steps in other pipelines for modular, reusable workflow design.

## Basic Usage

```python
from flowyml import Pipeline, step

# Define reusable preprocessing pipeline
preprocess = Pipeline("preprocessing")
preprocess.add_step(clean_data).add_step(normalize)

# Compose into parent pipeline
parent = Pipeline("training")
parent.add_sub_pipeline(
    preprocess,
    inputs=["raw_data"],
    outputs=["clean_data"],
)
parent.add_step(train_model)
parent.run()
```

## Input/Output Mapping

Map parent outputs to child inputs (and vice versa):

```python
parent.add_sub_pipeline(
    preprocess,
    inputs=["raw_data"],
    outputs=["clean_data"],
    input_mapping={"raw_data": "input_df"},     # parent → child
    output_mapping={"normalized": "clean_data"}, # child → parent
)
```

## Programmatic API

Use `SubPipelineStep` directly for full control:

```python
from flowyml.core.subpipeline import SubPipelineStep

sub_step = SubPipelineStep(
    sub_pipeline=preprocess,
    name="data_prep",
    inputs=["raw"],
    outputs=["clean"],
)
parent.add_step(sub_step)
```

## Benefits

- **Modular composition**: build complex pipelines from smaller, tested units
- **Reusability**: share preprocessing pipelines across projects
- **Encapsulation**: child pipeline details hidden from parent
- **Independent testing**: test child pipelines in isolation
