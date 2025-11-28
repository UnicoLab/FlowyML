# Materializers 📦

Materializers control how artifacts (data, models, metrics) are serialized and stored. UniFlow provides default materializers for common types (Pandas DataFrames, NumPy arrays, JSON), but you can create custom ones for specialized data.

## 📦 Built-in Materializers

UniFlow automatically selects the appropriate materializer based on the type hint or object type.

- **PandasMaterializer**: Parquet or CSV.
- **NumpyMaterializer**: `.npy` files.
- **JsonMaterializer**: JSON files.
- **PickleMaterializer**: Fallback for arbitrary Python objects.

## 🛠 Custom Materializers

To support a custom type, subclass `BaseMaterializer`.

```python
from uniflow.io import BaseMaterializer
from my_library import CustomGraph

class GraphMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (CustomGraph,)

    def handle_input(self, data_type):
        # Read from artifact store
        with open(self.artifact.uri, 'rb') as f:
            return CustomGraph.load(f)

    def handle_return(self, graph):
        # Write to artifact store
        with open(self.artifact.uri, 'wb') as f:
            graph.save(f)

# Register the materializer
from uniflow import materializer_registry
materializer_registry.register(GraphMaterializer)
```

## 🎯 Usage

Once registered, UniFlow will automatically use your materializer when a step returns a `CustomGraph` object.

```python
@step
def build_graph() -> CustomGraph:
    return CustomGraph(...)
```
