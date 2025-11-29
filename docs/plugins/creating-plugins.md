# Creating Custom Plugins

flowyml's plugin system is designed to be extensible. You can integrate any Python class as a flowyml component using the **Generic Bridge** and a simple YAML configuration.

## Configuration Structure

Plugins are defined in a `plugins` list within your `flowyml.yaml` or a dedicated config file.

```yaml
plugins:
  - name: <unique_plugin_name>
    source: <python_import_path>
    type: <component_type>
    adaptation:
      method_mapping:
        <flowyml_method>: <external_method>
      attribute_mapping:
        <flowyml_attribute>: <external_attribute>
```

### Fields

-   **`name`**: A unique identifier for the plugin (e.g., `my_custom_orchestrator`).
-   **`source`**: The full Python import path to the class (e.g., `airflow.providers.google.cloud.operators.bigquery.BigQueryExecuteQueryOperator`).
-   **`type`**: The flowyml component type. Supported values:
    -   `orchestrator`
    -   `artifact_store`
    -   `container_registry`
-   **`adaptation`**: (Optional) Rules for adapting the external class to flowyml's interface.

## Adaptation Rules

### Method Mapping

Map flowyml's standard methods to the methods of your external class.

**Example:** Mapping flowyml's `run_pipeline` to Airflow's `execute`:

```yaml
adaptation:
  method_mapping:
    run_pipeline: execute
```

### Attribute Mapping

Map flowyml's expected attributes to the attributes of your external class.

**Example:** Mapping `config` to `params`:

```yaml
adaptation:
  attribute_mapping:
    config: params
```

## Example: Airflow Operator

Here is how you can wrap an Airflow BigQuery operator as a flowyml orchestrator:

```yaml
plugins:
  - name: airflow_bigquery
    source: airflow.providers.google.cloud.operators.bigquery.BigQueryExecuteQueryOperator
    type: orchestrator
    adaptation:
      method_mapping:
        run_pipeline: execute
      attribute_mapping:
        config: params
```

Once defined, you can load and use this component in your flowyml code:

```python
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()
registry.load_plugins_from_config("flowyml.yaml")

bq_operator = registry.get_orchestrator("airflow_bigquery")
# Now use it like any flowyml orchestrator!
```
