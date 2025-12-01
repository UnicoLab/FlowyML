# CHANGELOG

<!-- version list -->

## v1.3.0 (2025-12-01)

### Bug Fixes

- Add Pipeline Dependencies guide and enhance resource and docker configuration handling in the
  pipeline
  ([`f87fe6c`](https://github.com/UnicoLab/FlowyML/commit/f87fe6cc5899a3b43523502f2a29d57c78de7fe8))

- Enhance LocalArtifactStore to save fallback data with improved metadata structure and update
  cloudpickle materializer registration logic.
  ([`ad3e04f`](https://github.com/UnicoLab/FlowyML/commit/ad3e04f87cf0b11a66d61a8b6b6d77a976d630ee))

- Replace `Never` type hint with `NoReturn` in `alerts.py`.
  ([`944deed`](https://github.com/UnicoLab/FlowyML/commit/944deed0b683cc1c8a0ede710b4bfede7db4d67d))

### Chores

- Save last release version for recovery [skip ci]
  ([`e79b4ea`](https://github.com/UnicoLab/FlowyML/commit/e79b4eabb22ddf51c1db11e84ac617d179422df9))

### Features

- Add artifact download functionality across UI components, enhancing user experience for asset
  management
  ([`e98c8d6`](https://github.com/UnicoLab/FlowyML/commit/e98c8d6d497e19cda4f75a65f8dc8b0678f54a5c))

- Add data seeding and verification scripts, and enhance UI API to list experiments and pipelines
  across all projects.
  ([`e8bde5a`](https://github.com/UnicoLab/FlowyML/commit/e8bde5ae0bba693281089c056882dcec6224bbda))

- Add project detail pages with new UI components and update frontend build assets.
  ([`9b086b9`](https://github.com/UnicoLab/FlowyML/commit/9b086b9732a4ddbdda0ea27870c6fdae265f235f))

- Add remote services configuration to backend and update header component to display remote
  services links in UI
  ([`e1b2bea`](https://github.com/UnicoLab/FlowyML/commit/e1b2beae90d94761a62173d984592a11eb379435))

- Add step start/end hooks to orchestrator and create a TODO list for future development.
  ([`611d85f`](https://github.com/UnicoLab/FlowyML/commit/611d85fb41c5472db192cc30dda426b56b6316f1))

- Add support for AWS and Azure stacks, including artifact stores and container registries,
  enhancing cloud deployment capabilities
  ([`92d3abd`](https://github.com/UnicoLab/FlowyML/commit/92d3abd43e187ea9aef88b6e02c4bfc4f15d50de))

- Enhance token management UI by adding permission chips with icons and styles for better visual
  representation of permissions.
  ([`c4af947`](https://github.com/UnicoLab/FlowyML/commit/c4af947ba1af2f753261112f94b87db2a45f2221))

- Implement a toast notification system and integrate it into the pipeline details panel for status
  updates.
  ([`0999576`](https://github.com/UnicoLab/FlowyML/commit/0999576f846913c801317d5f4341df63ac619033))

- Implement asset statistics dashboard, hierarchical view, and search functionality with supporting
  backend API endpoints.
  ([`46c4dd5`](https://github.com/UnicoLab/FlowyML/commit/46c4dd5bca060f565124d37b27b502aae5983383))

- Implement core orchestrator system for pipeline execution, integrating local and remote
  orchestrators with pipeline and cloud stacks, and remove rebranding script and materializer tests.
  ([`0c9c50e`](https://github.com/UnicoLab/FlowyML/commit/0c9c50e08ff7a7da58a2cb4cae9cf641c2d97f83))

- Implement model metrics logging and retrieval API, enhancing project performance tracking
  capabilities
  ([`890b01e`](https://github.com/UnicoLab/FlowyML/commit/890b01e9a6155207549be7d9bba63d23c374790d))

- Integrate project context across backend data models and enhance frontend asset and pipeline views
  with project filtering and UI refinements.
  ([`40baed6`](https://github.com/UnicoLab/FlowyML/commit/40baed6c386dc1727d02159d5d918411d89ee8f9))

- Introduce asset lineage graph component, update asset pages and backend, and add TODO list.
  ([`14acaec`](https://github.com/UnicoLab/FlowyML/commit/14acaecab7262c0c50fec28eef100a2512c7418c))

- Introduce cloudpickle materializer and overhaul plugin system documentation.
  ([`a93bff9`](https://github.com/UnicoLab/FlowyML/commit/a93bff92a2baded52d121c6b092019f47a0e4335))

- Introduce dedicated detail panels and a navigation tree for experiments, runs, and pipelines.
  ([`4b347d8`](https://github.com/UnicoLab/FlowyML/commit/4b347d8c6d4cfd11fee0811ac93c4ba7940add91))

- Introduce detailed project views with new components and update build assets.
  ([`62f1327`](https://github.com/UnicoLab/FlowyML/commit/62f13270aee7476372bfaaf69b4825d8048d7776))

- Introduce observability page with new orchestrator and cache metrics endpoints.
  ([`7bfa6c4`](https://github.com/UnicoLab/FlowyML/commit/7bfa6c4e4a52a29373607784f3bf6ef887482b13))

- Introduce ZenML integration UI, Keras training history documentation, and a project TODO list.
  ([`ed93b4e`](https://github.com/UnicoLab/FlowyML/commit/ed93b4ebc0b3b176fd2b34092748170e6be38824))

- Refactor Pipeline class to improve stack handling and add support for active stack switching
  ([`7dcbe48`](https://github.com/UnicoLab/FlowyML/commit/7dcbe48e293f72d163b87f63d265684ab2297b8c))

- Refactor sidebar navigation to group links into categories for improved organization and
  usability.
  ([`f0dfa82`](https://github.com/UnicoLab/FlowyML/commit/f0dfa82b3b49cd1523449c07db5563d72ef2561f))

- Update frontend assets with new JavaScript and CSS files, replacing outdated versions to enhance
  UI performance and styling.
  ([`ace9018`](https://github.com/UnicoLab/FlowyML/commit/ace90184015264630ffbf6ffe29205ed5c87bfcd))

- Update frontend assets, modify the assets page component, and add a TODO list for future UI/UX
  improvements.
  ([`aec2049`](https://github.com/UnicoLab/FlowyML/commit/aec204965baf2a6564a66de01c9ec6227e558189))

- Update frontend build artifacts, modify project UI components, and add a TODO file.
  ([`9f16e11`](https://github.com/UnicoLab/FlowyML/commit/9f16e115024007c14dec034a492295ba8dce2b46))

- Update frontend build assets, add a new backend client router, and revise the license copyright.
  ([`1ab9fe1`](https://github.com/UnicoLab/FlowyML/commit/1ab9fe1abcb8dc3124e4dc01a4972db2f3ad658b))


## v1.2.0 (2025-11-29)

### Bug Fixes

- Add project TODO list and update build configuration to include frontend assets and correct
  package name in manifest.
  ([`da53f05`](https://github.com/UnicoLab/FlowyML/commit/da53f05523fa1e02cdc7eb0caf3acbcba82dd16b))

### Documentation

- Update and expand FlowyML documentation with new feature highlights, detailed explanations, and a
  project TODO list.
  ([`1249a84`](https://github.com/UnicoLab/FlowyML/commit/1249a8485755dbeb6d765d8bf7c30014aeb8982c))

### Features

- Add TODO list and improve `Never` type import compatibility for older Python versions.
  ([`c18593d`](https://github.com/UnicoLab/FlowyML/commit/c18593dc80ae04efdc255c03ee988f2b5889a4ff))


## v1.1.0 (2025-11-29)

### Documentation

- Replace changelog with a new project TODO list.
  ([`ce2a2e6`](https://github.com/UnicoLab/FlowyML/commit/ce2a2e6e7fa50e992b68c98af1feb1393ffac8af))


## v1.0.0 (2025-11-29)

- Initial Release
