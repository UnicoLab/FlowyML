# Enhancment of RUN DAG view and it;s components

We shoudl make sure we can nicely and correctly display sveral things in the RUN DAG view in a nice user friendly way on top of current functionality:

Add more display components to the UI DAG display, for example to better show conditional nodes: "pipeline.add_control_flow(
        If(
            condition=check_mae_threshold,
            then_step=deploy_model,
            else_step=None,
        ),
    )"
-> better distinguish artefacts (like using rounded badger or something better) from nodes / steps

-> better display for ressources aggregation

-> show some info about pipelien schedule if it' is scheduled etc ...

-> nice display of Human-in-the-Loop

-> display clearly if step was chached
-> branching and conditional executions

or other functionality shoudl be greatly displayed in the UI dag view


## dependencies, dockers etc for remote execution on gcp or aws

- [x] **Project Isolation**: Implemented project-aware Docker tagging (`registry/project-pipeline:latest`) to prevent collisions in shared registries.
- [ ] **Dependency Management**: Ensure all dependencies (`requirements.txt`, `pyproject.toml`) are correctly detected and bundled into Docker images for remote execution.
- [ ] **Scaling**: Verify centralized metadata server decoupling from project-specific dependencies.
Locally it's easy per project, but what if we centralize flowyml with data from different projects with different deps dockerfiles etc -> we shoudl be able to scalably handle this. ! Maybe we would need to store this part as well, cause if we have centralized handling server we can't install pipelines dependencies it will be executed on gcp or aws and the centralized metadata server to not need it and shoudl be decoupled -> make sure we have the architecture that support sthis. You can also check how zenml solves this problem for comparison and inspiration !!! So locally this is not a problem cause all deps are installed, and flowyml is used in only one project, but once we have a centralized flowyml instance then this shoudl be handled correctly and scalably ! Make sure this is the case !


## Pipeline Tempaltes
Pipeline templates management ... create, edit, detele etc ...



well we should make sure this flowyml instance is well secured and only I'll be able to communicate with it and all the api ports are well secured etc for remote server -> we should maybe user token for it or login and make it work with local cli etc ... ? also for the local development and stack we shoudl not require tokens or anything else to make it simple for user !

We shoudl also implement uder authentification with default admin / flowyml user and password for remote server !!
