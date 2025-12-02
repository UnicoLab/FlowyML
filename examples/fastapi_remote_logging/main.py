from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from flowyml import Pipeline, step
from flowyml.utils.config import update_config

# Initialize FastAPI app
app = FastAPI(title="FlowyML Remote Logging Example")

# Configure FlowyML to use remote server
# In a real deployment, these would be set via environment variables:
# FLOWYML_EXECUTION_MODE=remote
# FLOWYML_REMOTE_SERVER_URL=http://localhost:8080/api
update_config(
    execution_mode="remote",
    remote_server_url="http://localhost:8080/api",
    enable_logging=True,
)


# Define a simple pipeline
@step(outputs=["data"])
def extract_data(source: str):
    print(f"Extracting data from {source}...")
    return {"source": source, "records": [1, 2, 3]}


@step(outputs=["processed_data"])
def process_data(data: dict):
    print("Processing data...")
    return [x * 2 for x in data["records"]]


@step
def load_data(processed_data: list):
    print(f"Loading {len(processed_data)} records...")
    return "Success"


def create_pipeline():
    pipeline = Pipeline("etl_pipeline")
    pipeline.add_step(extract_data)
    pipeline.add_step(process_data)
    pipeline.add_step(load_data)
    return pipeline


class TriggerRequest(BaseModel):
    source: str = "mongodb"


@app.post("/trigger")
async def trigger_pipeline(request: TriggerRequest, background_tasks: BackgroundTasks):
    """Trigger the pipeline in the background."""

    def run_pipeline(source: str):
        pipeline = create_pipeline()
        result = pipeline.run(inputs={"source": source})
        print(f"Pipeline finished with status: {result.state}")
        print(f"Run ID: {result.run_id}")

    background_tasks.add_task(run_pipeline, request.source)

    return {"status": "submitted", "message": "Pipeline triggered in background"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/schedule")
async def schedule_pipeline(interval_seconds: int = 60):
    """Schedule the pipeline to run periodically."""
    pipeline = create_pipeline()
    # Schedule it
    pipeline.schedule(
        schedule_type="interval",
        value=interval_seconds,
        inputs={"source": "scheduled_job"},
    )
    return {"status": "scheduled", "interval": interval_seconds}


@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup."""
    from flowyml.core.scheduler import PipelineScheduler

    scheduler = PipelineScheduler()
    scheduler.start()
    print("Scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler on app shutdown."""
    from flowyml.core.scheduler import PipelineScheduler

    scheduler = PipelineScheduler()
    scheduler.stop()
    print("Scheduler stopped")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
