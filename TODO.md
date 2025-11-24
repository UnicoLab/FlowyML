- also make sure that we have similar behaviour to ZenML so that when user starts a pipeline there is a display of an URL when clicked user is taken to the GUI and can follow execution of the pipeline in a realtime. Make sure that our react frontend application is better in terms or UX and more beatuful than the one of prefect. Remember that we are artifacts centric -> so we need some specific displays to maintain the uniqueness of this package !!! Make all this happend and let's finalize everything to have it production ready ! Maybe the backend should be in GoLang so it can be executed in any platform without any installation, be crazy fast and smaller than FasAPI  (does this makes sense)?


- pipeline creation like:
# Create and run pipeline
pipeline = Pipeline("simple_example", context=ctx)
pipeline.add_step(load_and_preprocess)
pipeline.add_step(train_model)

shoudl be simplified or even automatically built from relations etc if not provided, if provided maybe we shoudl think of a simpler way of defining a pipeline with dependencies etc

- we should handle branching contitionals etc to more complx logic