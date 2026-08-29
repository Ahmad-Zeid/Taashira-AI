"""HTTP surface. Serves the browser; never calls a model.

That split is enforced by IAM, not convention: the `taashira-api` service account has
no `aiplatform.user` role, so even a full compromise of this service cannot spend on
inference or reach Vertex AI.
"""
