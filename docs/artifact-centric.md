To understand the shift from Task-Centric (traditional) to Artifact-Centric (FlowyML) pipelines, we have to look at how the execution engine views the relationship between code and data.

Technically, this isn't just a naming convention; it’s a change in how the Directed Acyclic Graph (DAG) is constructed and how the state is persisted.

1. Declarative Signatures vs. Imperative Sequences
In a task-centric system (like Airflow), you define the order of operations. You essentially write a script that says, "Run preprocess, then run train." The movement of data between them is usually an afterthought—you manualy pass S3 paths or local file locations between functions.

In FlowyML (Artifact-Centric), the system builds the DAG by looking at the Input/Output signatures of your steps.

Technical Implementation: When you define a step, you declare: "I produce an artifact named 'train_data' of type Dataset." The Orchestrator looks at another step that says, "I require an input named 'train_data' of type Dataset."
Result: The "edge" in the graph is formed automatically because of a data dependency, not because you wrote step_a >> step_b. If you change an output name, the graph breaks at build-time (checked by the

TypeValidator
).
2. The Global Artifact Catalog vs. Manual "Handoffs"
The biggest technical hurdle in task-centric pipelines is the "handoff." You often see code like: pd.read_csv(f"s3://my-bucket/{run_id}/data.csv"). This hardcodes the infrastructure and pathing logic inside your business logic.

In an artifact-centric system, FlowyML uses the Catalog (Registry Pattern):

Unique Identity: Every artifact is registered in the

Catalog
 (via

register()
 which I just fixed) with a

content_hash
, source_step, and source_run_id.
Discovery: A downstream step doesn't need to know where the model is stored (S3 vs. Azure vs. Local). It asks the Catalog for the artifact by name/version. The

CatalogBackend
 resolves the storage URI and handles the high-level fetching.
Immutability: Each artifact is a record of truth. If the input data hash hasn't changed, the system knows it can skip the task entirely (Caching/Memoization).
3. Automatic Lineage (The "Parents" Concept)
In task-centric systems, if you find a bad model in production, tracing it back to the exact version of the SQL query and the raw CSV that created it is a manual forensic exercise.

In Artifact-Centric FlowyML:

Lineage Tracking: As seen in the

CatalogEntry
 structure, every artifact stores parent_ids.
Technical Flow: When Step B consumes Artifact A, FlowyML automatically records that Artifact A is the parent of whatever Step B produces.
Observability: You can call

get_lineage(artifact_id)
 to get a full recursive tree of every transformation that touched that specific piece of data, from raw ingestion to the final insight.
4. Infrastructure as Configuration (flowyml.yaml)
In task-centric code, you often specify cpu=4, memory='16Gi' inside your Python @task decorator. This locks your code to specific hardware.

In Artifact-Centric design, we decouple "What happens" from "Where it happens":

The Code: Pure Python logic defined by inputs and outputs.
The YAML: Defines the Stack. It specifies that the "Model" artifact produced by train_step should be stored in an S3ArtifactStore and that the step should run on a KubernetesOrchestrator.
Benefit: You can run the exact same artifact logic on your local machine (using

LocalCatalogBackend
) or in Great-Grandchild-scale production without changing a single line of Python.
Summary Comparison
Metric	Task-Centric	Artifact-Centric (FlowyML)
Logic Focus	"What do I run?" (Verbs)	"What do I produce?" (Nouns)
Data Flow	Manual path passing	Automatic resolution via Catalog
Validation	Errors happen at runtime (file not found)	Errors happen at build-time (type mismatch)
Debugging	Check the logs of Task X	Inspect the state of Artifact Y
Portability	Hardcoded file paths/infra	Stack-based storage abstraction
By focusing on the Artifact, FlowyML treats data as a first-class citizen of the deployment, enabling reproducible machine learning where every result is mathematically linked to its origin.
